"""
DuckDB-based query engine for IACS data.
Supports GeoPackage (.gpkg), GeoParquet (.parquet/.geoparquet) files.
Handles automatic CRS detection and reprojection to EPSG:4326 for web display.
"""
import duckdb
import json
import os
import re
import glob


# Extensions we recognise as spatial data
SPATIAL_EXTENSIONS = ('.gpkg', '.parquet', '.geoparquet')


class QueryEngine:
    def __init__(self, data_dir="data"):
        self.data_dir = data_dir
        self.conn = duckdb.connect(":memory:")
        self.conn.execute("INSTALL spatial; LOAD spatial;")
        self._loaded_datasets = {}  # filename -> {view_name, geom_col, crs, needs_reproject}

    # ------------------------------------------------------------------
    # Dataset discovery
    # ------------------------------------------------------------------
    def list_datasets(self):
        """List available spatial files in data directory (recursive)."""
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
    # Dataset loading
    # ------------------------------------------------------------------
    def _safe_view_name(self, filename):
        """Generate a valid SQL identifier from a filename/path."""
        name = os.path.splitext(os.path.basename(filename))[0]
        name = re.sub(r'[^a-zA-Z0-9]', '_', name)
        return f"ds_{name}"

    def _detect_crs(self, col_type):
        """Extract EPSG code from DuckDB column type like GEOMETRY('EPSG:3035')."""
        m = re.search(r"EPSG:(\d+)", col_type)
        if m:
            return int(m.group(1))
        return None

    def load_dataset(self, filename):
        """Register a dataset and detect geometry/CRS info. Returns metadata dict."""
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

        # Detect columns and geometry info
        columns = self.conn.execute(f"DESCRIBE {view_name}").fetchall()

        geom_col = None
        geom_type = None
        for col_name, col_type, *_ in columns:
            if 'GEOMETRY' in col_type.upper() or col_name.lower() in ('geom', 'geometry', 'wkb_geometry', 'shape'):
                geom_col = col_name
                geom_type = col_type
                break

        if geom_col is None:
            geom_col = 'geom'  # fallback
            geom_type = ''

        crs = self._detect_crs(geom_type)
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
        """SQL expression that yields the geometry in EPSG:4326."""
        meta = self._meta(filename)
        g = meta['geom_col']
        if meta['needs_reproject']:
            return f"ST_Transform({g}, 'EPSG:{meta['crs']}', 'EPSG:4326', true)"
        return g

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
        """Get bounding box in EPSG:4326."""
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
        """
        Get features as GeoJSON FeatureCollection.
        All geometries are returned in EPSG:4326.
        bbox: [minx, miny, maxx, maxy] in EPSG:4326
        """
        meta = self._meta(filename)
        view = meta['view_name']
        gcol = meta['geom_col']
        attr_cols = self._attr_cols(filename)
        geom_4326 = self._geom_as_4326(filename)

        select_parts = [f'"{c}"' for c in attr_cols]
        select_parts.append(f"ST_AsGeoJSON({geom_4326}) as __geojson__")
        select_clause = ", ".join(select_parts)

        where_parts = []
        params = []

        if bbox:
            minx, miny, maxx, maxy = bbox
            if meta['needs_reproject']:
                # Transform the bbox envelope into the source CRS for indexed filtering
                src_crs = meta['crs']
                where_parts.append(
                    f"ST_Intersects({gcol}, "
                    f"ST_Transform(ST_MakeEnvelope({minx}, {miny}, {maxx}, {maxy}), "
                    f"'EPSG:4326', 'EPSG:{src_crs}', true))"
                )
            else:
                where_parts.append(
                    f"ST_Intersects({gcol}, ST_MakeEnvelope({minx}, {miny}, {maxx}, {maxy}))"
                )

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
