"""
API routes for querying IACS datasets via DuckDB.
"""
from flask import Blueprint, jsonify, request, current_app

api = Blueprint('api', __name__)


def get_engine():
    return current_app.config['QUERY_ENGINE']


@api.route('/datasets', methods=['GET'])
def list_datasets():
    """List available datasets. Optionally reload cache."""
    engine = get_engine()
    if request.args.get('reload'):
        engine.reload_datasets()
    return jsonify(engine.list_datasets())


@api.route('/datasets/<path:filename>/info', methods=['GET'])
def dataset_info(filename):
    """Get dataset metadata: columns, bounds, feature count."""
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
    Get features as GeoJSON. Supports bbox and attribute filtering.
    Query params:
      bbox: minx,miny,maxx,maxy (EPSG:4326)
      limit: max features (default 2000)
      offset: pagination offset
      filter_*: attribute filters, e.g. filter_nation=DE
    """
    engine = get_engine()

    bbox = request.args.get('bbox')
    if bbox:
        bbox = [float(x) for x in bbox.split(',')]

    limit = int(request.args.get('limit', 2000))
    offset = int(request.args.get('offset', 0))

    filters = {}
    for key, val in request.args.items():
        if key.startswith('filter_'):
            col = key[7:]
            filters[col] = val

    try:
        geojson = engine.get_features_bbox(
            filename, bbox=bbox, limit=limit, offset=offset, filters=filters
        )
        return jsonify(geojson)
    except FileNotFoundError:
        return jsonify({"error": "Dataset not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@api.route('/datasets/<path:filename>/values/<column>', methods=['GET'])
def unique_values(filename, column):
    engine = get_engine()
    try:
        values = engine.get_unique_values(filename, column)
        return jsonify(values)
    except FileNotFoundError:
        return jsonify({"error": "Dataset not found"}), 404


@api.route('/datasets/<path:filename>/stats', methods=['GET'])
def dataset_stats(filename):
    engine = get_engine()
    try:
        return jsonify(engine.get_stats(filename))
    except FileNotFoundError:
        return jsonify({"error": "Dataset not found"}), 404
