"""
DuckDB-based query engine for IACS data.
Supports GeoPackage (.gpkg), GeoParquet (.parquet/.geoparquet) files.
Handles automatic CRS detection and reprojection to EPSG:4326 for web display.
Uses zoom-adaptive strategies: clustered centroids when zoomed out, full polygons when zoomed in.
"""
import duckdb
import json
import os
import re
import glob
import math

SPATIAL_EXTENSIONS = ('.gpkg', '.parquet', '.geoparquet')


class QueryEngine:
    def __init__(self, data_dir="data"):
        self.data_dir = data_dir
        self.conn = duckdb.connect(":memory:")
        self.conn.execute("INSTALL spatial; LOAD spatial;")
        self._loaded_datasets = {}

    # ------------------------------------------------------------------
    # Dataset discovery
    # ------------------------------------------------------------------
    def list_datasets(self):
        datasets = []
        for root, _dirs, files in os.walk(self.data_dir):
            for fname in sorted(files):
                if not fname.lower().endswith(SPATIAL_EXTENSIONS):
                    continue
                if fname.startswith('.'):
                    continue
                path = os.path.join(root, fname)
                rel = os.path.relpath(path, self.data_dir)
                fmt = "geopackage" if fname.endswith(".gpkg") else "geoparquet"
                datasets.append({
                    "name": rel,
                    "path": path,
                    "format": fmt,
                    "size_mb": round(os.path.getsize(path) / 1024 / 1024, 2),
                })
        return datasets

    # ------------------------------------------------------------------
    # Dataset loading & metadata
    # ------------------------------------------------------------------
    def _safe_view_name(self, filename):
        name = os.path.splitext(os.path.basename(filename))[0]
        name = re.sub(r'[^a-zA-Z0-9]', '_', name)
        return f"ds_{name}"

    def _detect_crs(self, col_type):
        m = re.search(r"EPSG:(\d+)", col_type)
        return int(m.group(1)) if m else None

    def load_dataset(self, filename):
        if filename in self._loaded_datasets:
            return self._loaded_datasets[filename]

        filepath = os.path.join(self.data_dir, filename)
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"Dataset not found: {filename}")

        view_name = self._safe_view_name(filename)

        if filename.endswith(".gpkg"):
            self.conn.execute(
                f"CREATE OR REPLACE VIEW {view_name} AS SELECT * FROM ST_Read('{filepath}')"
            )
        elif filename.endswith((".parquet", ".geoparquet")):
            self.conn.execute(
                f"CREATE OR REPLACE VIEW {view_name} AS SELECT * FROM read_parquet('{filepath}')"
            )
        else:
            raise ValueError(f"Unsupported format: {filename}")

        columns = self.conn.execute(f"DESCRIBE {view_name}").fetchall()

        geom_col = None
        geom_type = None
        for col_name, col_type, *_ in columns:
            if 'GEOMETRY' in col_type.upper() or col_name.lower() in ('geom', 'geometry', 'wkb_geometry', 'shape'):
                geom_col = col_name
                geom_type = col_type
                break

        if geom_col is None:
            geom_col = 'geom'
            geom_type = ''

        crs = self._detect_crs(geom_type or '')
        needs_reproject = crs is not None and crs != 4326

        meta = {
            'view_name': view_name,
            'geom_col': geom_col,
            'crs': crs,
            'needs_reproject': needs_reproject,
            'columns': [{"name": c[0], "type": c[1]} for c in columns],
        }
        self._loaded_datasets[filename] = meta
        return meta

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _meta(self, filename):
        return self.load_dataset(filename)

    def _attr_cols(self, filename):
        meta = self._meta(filename)
        return [c["name"] for c in meta["columns"] if c["name"] != meta["geom_col"]]

    def _geom_as_4326(self, filename):
        meta = self._meta(filename)
        g = meta['geom_col']
        if meta['needs_reproject']:
            src_crs = meta['crs']
            return f"ST_Transform({g}, 'EPSG:{src_crs}', 'EPSG:4326', true)"
        return g

    def _bbox_filter(self, filename, bbox):
        """Build a WHERE clause for bbox filtering in the source CRS."""
        meta = self._meta(filename)
        gcol = meta['geom_col']
        minx, miny, maxx, maxy = bbox
        if meta['needs_reproject']:
            src_crs = meta['crs']
            return (
                f"ST_Intersects({gcol}, "
                f"ST_Transform(ST_MakeEnvelope({minx}, {miny}, {maxx}, {maxy}), "
                f"'EPSG:4326', 'EPSG:{src_crs}', true))"
            )
        else:
            return f"ST_Intersects({gcol}, ST_MakeEnvelope({minx}, {miny}, {maxx}, {maxy}))"

    # ------------------------------------------------------------------
    # Public query methods
    # ------------------------------------------------------------------
    def get_columns(self, filename):
        return self._meta(filename)['columns']

    def get_feature_count(self, filename):
        meta = self._meta(filename)
        r = self.conn.execute(f"SELECT COUNT(*) FROM {meta['view_name']}").fetchone()
        return r[0]

    def get_bounds(self, filename):
        meta = self._meta(filename)
        geom_4326 = self._geom_as_4326(filename)
        r = self.conn.execute(f"""
            SELECT
                MIN(ST_XMin({geom_4326})),
                MIN(ST_YMin({geom_4326})),
                MAX(ST_XMax({geom_4326})),
                MAX(ST_YMax({geom_4326}))
            FROM {meta['view_name']}
        """).fetchone()
        return {"minx": r[0], "miny": r[1], "maxx": r[2], "maxy": r[3]}

    def get_features_bbox(self, filename, bbox=None, limit=2000, offset=0, filters=None):
        """Get features as GeoJSON FeatureCollection in EPSG:4326."""
        meta = self._meta(filename)
        view = meta['view_name']
        attr_cols = self._attr_cols(filename)
        geom_4326 = self._geom_as_4326(filename)

        select_parts = [f'"{c}"' for c in attr_cols]
        select_parts.append(f"ST_AsGeoJSON({geom_4326}) as __geojson__")
        select_clause = ", ".join(select_parts)

        where_parts = []
        params = []

        if bbox:
            where_parts.append(self._bbox_filter(filename, bbox))

        if filters:
            for col, val in filters.items():
                if col in attr_cols:
                    where_parts.append(f'"{col}"::VARCHAR = ?')
                    params.append(str(val))

        where_clause = (" WHERE " + " AND ".join(where_parts)) if where_parts else ""
        query = f"SELECT {select_clause} FROM {view}{where_clause} LIMIT {limit} OFFSET {offset}"
        result = self.conn.execute(query, params).fetchall()
        col_names = attr_cols + ["__geojson__"]

        features = []
        for row in result:
            row_dict = dict(zip(col_names, row))
            geojson_str = row_dict.pop("__geojson__")
            geometry = json.loads(geojson_str) if geojson_str else None

            props = {}
            for k, v in row_dict.items():
                if v is None:
                    props[k] = None
                elif isinstance(v, (int, float, str, bool)):
                    props[k] = v
                else:
                    props[k] = str(v)

            features.append({
                "type": "Feature",
                "geometry": geometry,
                "properties": props,
            })

        return {"type": "FeatureCollection", "features": features}

    def get_features_overview(self, filename, bbox=None, grid_size=0.5, filters=None):
        """
        Get a grid-aggregated overview for zoomed-out views.
        Groups features into grid cells and returns centroids with counts
        and dominant crop category. Much faster than loading all polygons.
        grid_size: size of grid cells in degrees (EPSG:4326)
        """
        meta = self._meta(filename)
        view = meta['view_name']
        attr_cols = self._attr_cols(filename)
        geom_4326 = self._geom_as_4326(filename)

        # Determine the best category column
        cat_col = None
        for candidate in ('EC_hcat_n', 'crop_name', 'EC_trans_n'):
            if candidate in attr_cols:
                cat_col = candidate
                break

        # Grid cell expressions
        cx = f"FLOOR(ST_X(ST_Centroid({geom_4326})) / {grid_size}) * {grid_size} + {grid_size / 2}"
        cy = f"FLOOR(ST_Y(ST_Centroid({geom_4326})) / {grid_size}) * {grid_size} + {grid_size / 2}"

        # Build aggregation query
        select_parts = [
            f"{cx} as grid_x",
            f"{cy} as grid_y",
            "COUNT(*) as feature_count",
        ]
        group_cols = ["grid_x", "grid_y"]

        if cat_col:
            # Get dominant category per grid cell using a subquery
            select_parts.append(f'MODE("{cat_col}") as dominant_category')

        select_clause = ", ".join(select_parts)

        where_parts = []
        params = []
        if bbox:
            where_parts.append(self._bbox_filter(filename, bbox))
        if filters:
            for col, val in filters.items():
                if col in attr_cols:
                    where_parts.append(f'"{col}"::VARCHAR = ?')
                    params.append(str(val))

        where_clause = (" WHERE " + " AND ".join(where_parts)) if where_parts else ""

        query = f"""
            SELECT {select_clause}
            FROM {view}{where_clause}
            GROUP BY grid_x, grid_y
            ORDER BY feature_count DESC
            LIMIT 5000
        """

        result = self.conn.execute(query, params).fetchall()

        features = []
        for row in result:
            grid_x, grid_y, count = row[0], row[1], row[2]
            dominant = row[3] if cat_col and len(row) > 3 else None

            features.append({
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [grid_x, grid_y]
                },
                "properties": {
                    "feature_count": count,
                    "dominant_category": dominant,
                    "grid_size": grid_size,
                },
            })

        return {
            "type": "FeatureCollection",
            "features": features,
            "overview": True,
        }

    def get_bbox_count(self, filename, bbox=None, filters=None):
        """Fast count of features in a bbox (to decide overview vs full)."""
        meta = self._meta(filename)
        view = meta['view_name']
        attr_cols = self._attr_cols(filename)

        where_parts = []
        params = []
        if bbox:
            where_parts.append(self._bbox_filter(filename, bbox))
        if filters:
            for col, val in filters.items():
                if col in attr_cols:
                    where_parts.append(f'"{col}"::VARCHAR = ?')
                    params.append(str(val))

        where_clause = (" WHERE " + " AND ".join(where_parts)) if where_parts else ""
        r = self.conn.execute(
            f"SELECT COUNT(*) FROM {view}{where_clause}", params
        ).fetchone()
        return r[0]

    def get_unique_values(self, filename, column):
        meta = self._meta(filename)
        attr_cols = self._attr_cols(filename)
        if column not in attr_cols:
            return []
        result = self.conn.execute(
            f'SELECT DISTINCT "{column}" FROM {meta["view_name"]} ORDER BY "{column}" LIMIT 500'
        ).fetchall()
        return [r[0] for r in result if r[0] is not None]

    def get_stats(self, filename):
        meta = self._meta(filename)
        view = meta['view_name']
        attr_cols = self._attr_cols(filename)
        count = self.get_feature_count(filename)
        stats = {"total_features": count, "columns": {}}

        for col in attr_cols:
            col_info = {}
            try:
                unique = self.conn.execute(
                    f'SELECT COUNT(DISTINCT "{col}") FROM {view}'
                ).fetchone()[0]
                col_info["unique_values"] = unique
                if unique <= 20:
                    vals = self.conn.execute(
                        f'SELECT "{col}", COUNT(*) as cnt FROM {view} GROUP BY "{col}" ORDER BY cnt DESC LIMIT 20'
                    ).fetchall()
                    col_info["value_counts"] = {str(v[0]): v[1] for v in vals}
            except Exception:
                pass
            stats["columns"][col] = col_info

        return stats

    def reload_datasets(self):
        """Clear cached views so new files are picked up."""
        self._loaded_datasets.clear()
