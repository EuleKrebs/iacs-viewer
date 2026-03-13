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
import math

SPATIAL_EXTENSIONS = ('.gpkg', '.parquet', '.geoparquet')

# Known EPSG:3035 → EPSG:4326 approximate transform coefficients
# For rough bounding box conversion without scanning all geometries
EPSG3035_APPROX_BOUNDS = {
    # country_prefix: [minx, miny, maxx, maxy] in EPSG:4326
    'AT': [9.5, 46.3, 17.2, 49.0],
    'DE': [5.9, 47.3, 15.0, 55.1],
    'FR': [-5.1, 41.3, 9.6, 51.1],
    'IT': [6.6, 36.6, 18.5, 47.1],
    'ES': [-9.3, 36.0, 3.3, 43.8],
    'NL': [3.4, 50.8, 7.2, 53.5],
    'SE': [11.1, 55.3, 24.2, 69.1],
    'FI': [20.6, 59.8, 31.6, 70.1],
    'SK': [16.8, 47.7, 22.6, 49.6],
    'CZ': [12.1, 48.6, 18.9, 51.1],
    'PT': [-9.5, 36.9, -6.2, 42.2],
    'HR': [13.5, 42.4, 19.4, 46.6],
    'BG': [22.4, 41.2, 28.6, 44.2],
    'BE': [2.5, 49.5, 6.4, 51.5],
    'DK': [8.1, 54.6, 15.2, 57.8],
    'LV': [21.0, 55.7, 28.2, 58.1],
    'LT': [21.0, 53.9, 26.8, 56.5],
    'SI': [13.4, 45.4, 16.6, 46.9],
}


class QueryEngine:
    def __init__(self, data_dir="data"):
        self.data_dir = data_dir
        self.conn = duckdb.connect(":memory:")
        self.conn.execute("INSTALL spatial; LOAD spatial;")
        self._loaded_datasets = {}
        self._bounds_cache = {}

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

    def _guess_country(self, filename):
        """Extract country code from filename like GSA-AT-2023.geoparquet."""
        bn = os.path.basename(filename).upper()
        for prefix in EPSG3035_APPROX_BOUNDS:
            if prefix in bn:
                return prefix
        return None

    # ------------------------------------------------------------------
    # Public query methods
    # ------------------------------------------------------------------
    def get_columns(self, filename):
        return self._meta(filename)['columns']

    def get_feature_count(self, filename):
        """Get feature count. Uses parquet metadata when possible (fast)."""
        meta = self._meta(filename)
        r = self.conn.execute(f"SELECT COUNT(*) FROM {meta['view_name']}").fetchone()
        return r[0]

    def get_bounds(self, filename):
        """
        Get bounding box in EPSG:4326.
        Uses a fast strategy:
        1. Check cache
        2. For projected data: use native CRS bounds (fast) + approximate transform
        3. For small files or 4326: compute directly
        4. Fall back to country-based approximation for very large files
        """
        if filename in self._bounds_cache:
            return self._bounds_cache[filename]

        meta = self._meta(filename)
        view = meta['view_name']
        gcol = meta['geom_col']

        if meta['needs_reproject']:
            # First try: compute bounds in native CRS (no transform = fast)
            # Then transform just the 4 corner values
            try:
                r = self.conn.execute(f"""
                    SELECT
                        MIN(ST_XMin({gcol})),
                        MIN(ST_YMin({gcol})),
                        MAX(ST_XMax({gcol})),
                        MAX(ST_YMax({gcol}))
                    FROM {view}
                """).fetchone()

                if r[0] is not None:
                    src_crs = meta['crs']
                    # Transform the bounding box corners to 4326
                    t = self.conn.execute(f"""
                        SELECT
                            ST_XMin(ST_Transform(ST_MakeEnvelope({r[0]}, {r[1]}, {r[2]}, {r[3]}),
                                'EPSG:{src_crs}', 'EPSG:4326', true)),
                            ST_YMin(ST_Transform(ST_MakeEnvelope({r[0]}, {r[1]}, {r[2]}, {r[3]}),
                                'EPSG:{src_crs}', 'EPSG:4326', true)),
                            ST_XMax(ST_Transform(ST_MakeEnvelope({r[0]}, {r[1]}, {r[2]}, {r[3]}),
                                'EPSG:{src_crs}', 'EPSG:4326', true)),
                            ST_YMax(ST_Transform(ST_MakeEnvelope({r[0]}, {r[1]}, {r[2]}, {r[3]}),
                                'EPSG:{src_crs}', 'EPSG:4326', true))
                    """).fetchone()

                    bounds = {"minx": t[0], "miny": t[1], "maxx": t[2], "maxy": t[3]}
                    self._bounds_cache[filename] = bounds
                    return bounds
            except Exception:
                pass

            # Fallback: country-based approximation
            country = self._guess_country(filename)
            if country and country in EPSG3035_APPROX_BOUNDS:
                b = EPSG3035_APPROX_BOUNDS[country]
                bounds = {"minx": b[0], "miny": b[1], "maxx": b[2], "maxy": b[3]}
                self._bounds_cache[filename] = bounds
                return bounds
        else:
            # EPSG:4326 — direct computation is fine
            try:
                r = self.conn.execute(f"""
                    SELECT
                        MIN(ST_XMin({gcol})),
                        MIN(ST_YMin({gcol})),
                        MAX(ST_XMax({gcol})),
                        MAX(ST_YMax({gcol}))
                    FROM {view}
                """).fetchone()
                if r[0] is not None:
                    bounds = {"minx": r[0], "miny": r[1], "maxx": r[2], "maxy": r[3]}
                    self._bounds_cache[filename] = bounds
                    return bounds
            except Exception:
                pass

        # Ultimate fallback: Europe
        return {"minx": -10, "miny": 35, "maxx": 30, "maxy": 72}

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

    def _native_grid_size(self, filename, grid_size_4326):
        """
        Convert a grid size in degrees (EPSG:4326) to approximate native CRS units.
        For EPSG:3035, 1 degree ≈ 100km ≈ 100000m.
        """
        meta = self._meta(filename)
        if meta['needs_reproject'] and meta['crs'] == 3035:
            return grid_size_4326 * 100000
        return grid_size_4326

    def get_features_overview(self, filename, bbox=None, grid_size=0.5, filters=None):
        """
        Fast grid-aggregated overview for zoomed-out views.
        Key optimization: grid grouping happens in NATIVE CRS (no per-row transform).
        Only the ~300 resulting grid centers get transformed to EPSG:4326.
        """
        meta = self._meta(filename)
        view = meta['view_name']
        gcol = meta['geom_col']
        attr_cols = self._attr_cols(filename)

        cat_col = None
        for candidate in ('EC_hcat_n', 'crop_name', 'EC_trans_n'):
            if candidate in attr_cols:
                cat_col = candidate
                break

        # Grid in native CRS (fast — no per-row transform)
        native_gs = self._native_grid_size(filename, grid_size)
        cx = f"FLOOR(ST_X(ST_Centroid({gcol})) / {native_gs}) * {native_gs} + {native_gs / 2}"
        cy = f"FLOOR(ST_Y(ST_Centroid({gcol})) / {native_gs}) * {native_gs} + {native_gs / 2}"

        select_parts = [
            f"{cx} as grid_x",
            f"{cy} as grid_y",
            "COUNT(*) as feature_count",
        ]

        if cat_col:
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

        # Now transform only the grid centers to 4326 (few hundred points max)
        needs_reproject = meta['needs_reproject']
        features = []

        if needs_reproject and result:
            src_crs = meta['crs']
            # Batch transform all grid centers in one query
            values_sql = ", ".join(
                f"({row[0]}, {row[1]})" for row in result
            )
            transform_query = f"""
                SELECT
                    ST_X(ST_Transform(ST_Point(x, y), 'EPSG:{src_crs}', 'EPSG:4326', true)),
                    ST_Y(ST_Transform(ST_Point(x, y), 'EPSG:{src_crs}', 'EPSG:4326', true))
                FROM (VALUES {values_sql}) AS t(x, y)
            """
            transformed = self.conn.execute(transform_query).fetchall()

            for i, row in enumerate(result):
                count = row[2]
                dominant = row[3] if cat_col and len(row) > 3 else None
                lon, lat = transformed[i]

                features.append({
                    "type": "Feature",
                    "geometry": {"type": "Point", "coordinates": [lon, lat]},
                    "properties": {
                        "feature_count": count,
                        "dominant_category": dominant,
                        "grid_size": grid_size,
                    },
                })
        else:
            for row in result:
                grid_x, grid_y, count = row[0], row[1], row[2]
                dominant = row[3] if cat_col and len(row) > 3 else None

                features.append({
                    "type": "Feature",
                    "geometry": {"type": "Point", "coordinates": [grid_x, grid_y]},
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
        self._bounds_cache.clear()
