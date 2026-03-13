"""
API routes for querying IACS datasets via DuckDB.
"""
from flask import Blueprint, jsonify, request, current_app

api = Blueprint('api', __name__)

# Threshold: if more features in viewport than this, switch to overview mode
OVERVIEW_THRESHOLD = 5000


def get_engine():
    return current_app.config['QUERY_ENGINE']


@api.route('/datasets', methods=['GET'])
def list_datasets():
    engine = get_engine()
    if request.args.get('reload'):
        engine.reload_datasets()
    return jsonify(engine.list_datasets())


@api.route('/datasets/<path:filename>/info', methods=['GET'])
def dataset_info(filename):
    engine = get_engine()
    try:
        meta = engine.load_dataset(filename)
        return jsonify({
            "filename": filename,
            "columns": engine.get_columns(filename),
            "bounds": engine.get_bounds(filename),
            "feature_count": engine.get_feature_count(filename),
            "crs": meta.get("crs"),
        })
    except FileNotFoundError:
        return jsonify({"error": "Dataset not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@api.route('/datasets/<path:filename>/features', methods=['GET'])
def get_features(filename):
    """
    Smart feature endpoint: auto-decides between full polygons and overview mode.

    Query params:
      bbox: minx,miny,maxx,maxy (EPSG:4326)
      zoom: current map zoom level
      limit: max features (default 3000)
      offset: pagination offset
      filter_*: attribute filters
      mode: force 'full' or 'overview' (optional, auto if omitted)
    """
    engine = get_engine()

    bbox = request.args.get('bbox')
    if bbox:
        bbox = [float(x) for x in bbox.split(',')]

    zoom = request.args.get('zoom', type=float)
    limit = int(request.args.get('limit', 3000))
    offset = int(request.args.get('offset', 0))
    mode = request.args.get('mode')  # 'full', 'overview', or None (auto)

    filters = {}
    for key, val in request.args.items():
        if key.startswith('filter_'):
            filters[key[7:]] = val

    try:
        # Auto-decide mode based on feature count in viewport
        if mode is None and bbox:
            count = engine.get_bbox_count(filename, bbox=bbox, filters=filters)
            if count > OVERVIEW_THRESHOLD:
                mode = 'overview'
            else:
                mode = 'full'
        elif mode is None:
            mode = 'full'

        if mode == 'overview':
            # Pick grid size based on zoom level
            if zoom is not None:
                if zoom >= 10:
                    grid_size = 0.02
                elif zoom >= 8:
                    grid_size = 0.05
                elif zoom >= 6:
                    grid_size = 0.2
                elif zoom >= 4:
                    grid_size = 0.5
                else:
                    grid_size = 1.0
            else:
                grid_size = 0.5

            geojson = engine.get_features_overview(
                filename, bbox=bbox, grid_size=grid_size, filters=filters
            )
        else:
            geojson = engine.get_features_bbox(
                filename, bbox=bbox, limit=limit, offset=offset, filters=filters
            )
            geojson['overview'] = False

        return jsonify(geojson)

    except FileNotFoundError:
        return jsonify({"error": "Dataset not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@api.route('/datasets/<path:filename>/values/<column>', methods=['GET'])
def unique_values(filename, column):
    engine = get_engine()
    try:
        return jsonify(engine.get_unique_values(filename, column))
    except FileNotFoundError:
        return jsonify({"error": "Dataset not found"}), 404


@api.route('/datasets/<path:filename>/stats', methods=['GET'])
def dataset_stats(filename):
    engine = get_engine()
    try:
        return jsonify(engine.get_stats(filename))
    except FileNotFoundError:
        return jsonify({"error": "Dataset not found"}), 404
