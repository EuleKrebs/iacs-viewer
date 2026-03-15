"""
DuckDB-based query engine for IACS data — persistent mode.

Uses a persistent DuckDB database to materialise datasets into native tables
with pre-computed EPSG:4326 geometry, bounding-box columns and centroid
columns.  This gives:

 • Instant metadata (bounds, count, columns) from a catalogue table
 • Very fast spatial filtering via numeric bbox columns (zone-map friendly)
 • Zero per-query coordinate transforms (done once at import)
 • Zero per-query ST_Centroid calls in overview mode (pre-computed)
"""

import duckdb
import json
import logging
import os
import re
import threading

logger = logging.getLogger(__name__)

SPATIAL_EXTENSIONS = ('.gpkg', '.parquet', '.geoparquet')

# Fallback bounding boxes per country (EPSG:4326)
EPSG3035_APPROX_BOUNDS = {
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

# Internal helper columns stored alongside user data
_INTERNAL_COLS = frozenset({
    '_bbox_minx', '_bbox_miny', '_bbox_maxx', '_bbox_maxy',
    '_centroid_x', '_centroid_y',
})


class QueryEngine:
    """Persistent DuckDB query engine with one-time import + fast queries.

    The connection to the persistent database is opened lazily on first
    use so that Flask's reloader (which spawns a parent *and* a child
    process) does not cause a DuckDB lock conflict.
    """

    def __init__(self, data_dir="data"):
        self.data_dir = data_dir
        os.makedirs(data_dir, exist_ok=True)

        self.db_path = os.path.join(data_dir, "iacs.duckdb")
        self._conn = None                    # opened lazily
        self._lock = threading.Lock()
        self._meta_cache = {}                # filename → meta dict

    # ------------------------------------------------------------------
    # Lazy connection
    # ------------------------------------------------------------------
    @property
    def conn(self):
        """Return the DuckDB connection, opening it on first access."""
        if self._conn is None:
            self._conn = duckdb.connect(self.db_path)
            self._setup()
        return self._conn

    # ------------------------------------------------------------------
    # Bootstrap
    # ------------------------------------------------------------------
    def _setup(self):
        """Load the spatial extension and create the catalogue table."""
        try:
            self._conn.execute("INSTALL spatial")
        except Exception:
            pass  # already installed, or auto-loaded
        self._conn.execute("LOAD spatial")

        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS _dataset_meta (
                filename      VARCHAR PRIMARY KEY,
                table_name    VARCHAR NOT NULL,
                file_mtime    DOUBLE  NOT NULL,
                file_size     BIGINT  NOT NULL,
                original_crs  INTEGER,
                bounds_minx   DOUBLE,
                bounds_miny   DOUBLE,
                bounds_maxx   DOUBLE,
                bounds_maxy   DOUBLE,
                feature_count BIGINT,
                columns_json  VARCHAR
            )
        """)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _safe_table_name(filename):
        name = os.path.splitext(os.path.basename(filename))[0]
        name = re.sub(r'[^a-zA-Z0-9]', '_', name)
        return f"ds_{name}"

    @staticmethod
    def _detect_crs(col_type):
        m = re.search(r"EPSG:(\d+)", col_type or "")
        return int(m.group(1)) if m else None

    def _meta(self, filename):
        return self.load_dataset(filename)

    def _attr_cols(self, filename):
        meta = self._meta(filename)
        return [
            c["name"] for c in meta["columns"]
            if c["name"] != "geometry" and c["name"] not in _INTERNAL_COLS
        ]

    @staticmethod
    def _bbox_where(bbox):
        """Fast numeric bounding-box filter (uses DuckDB zone maps)."""
        minx, miny, maxx, maxy = bbox
        return (
            f"_bbox_maxx >= {minx} AND _bbox_minx <= {maxx} "
            f"AND _bbox_maxy >= {miny} AND _bbox_miny <= {maxy}"
        )

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
    # Dataset loading & import
    # ------------------------------------------------------------------
    def load_dataset(self, filename):
        """
        Return metadata for *filename*.

        If the dataset has already been imported into the persistent DB and
        the source file has not changed, the cached catalogue row is used
        (instant).  Otherwise the file is imported first.
        """
        # Fast path — in-memory cache
        if filename in self._meta_cache:
            meta = self._meta_cache[filename]
            filepath = os.path.join(self.data_dir, filename)
            if os.path.exists(filepath):
                stat = os.stat(filepath)
                if (meta.get('file_mtime') == stat.st_mtime
                        and meta.get('file_size') == stat.st_size):
                    return meta

        filepath = os.path.join(self.data_dir, filename)
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"Dataset not found: {filename}")

        stat = os.stat(filepath)
        table_name = self._safe_table_name(filename)

        with self._lock:
            # Check the persistent catalogue
            row = self.conn.execute(
                "SELECT table_name, file_mtime, file_size, original_crs, "
                "       bounds_minx, bounds_miny, bounds_maxx, bounds_maxy, "
                "       feature_count, columns_json "
                "FROM _dataset_meta WHERE filename = ?",
                [filename],
            ).fetchone()

            if row and row[1] == stat.st_mtime and row[2] == stat.st_size:
                meta = self._row_to_meta(row, stat)
                self._meta_cache[filename] = meta
                return meta

            # Import (or re-import) the dataset
            return self._import_dataset(filename, filepath, table_name, stat)

    def _row_to_meta(self, row, stat):
        """Convert a _dataset_meta row into the dict used everywhere else."""
        return {
            'table_name':    row[0],
            'original_crs':  row[3],
            'crs':           f"EPSG:{row[3]}" if row[3] else None,
            'bounds':        {
                'minx': row[4], 'miny': row[5],
                'maxx': row[6], 'maxy': row[7],
            },
            'feature_count': row[8],
            'columns':       json.loads(row[9]) if row[9] else [],
            'file_mtime':    stat.st_mtime,
            'file_size':     stat.st_size,
        }

    def _import_dataset(self, filename, filepath, table_name, stat):
        """
        Import a spatial file into a native DuckDB table.

        All geometry is transformed to EPSG:4326 at import time.  Four
        helper columns are added:

          _bbox_minx / _bbox_miny / _bbox_maxx / _bbox_maxy
              Pre-computed bounding box of each feature in EPSG:4326.
              Used for fast numeric spatial filtering (zone-map friendly).

          _centroid_x / _centroid_y
              Pre-computed centroid in EPSG:4326.
              Used for instant grid-aggregation in overview mode.

        Must be called while self._lock is held.
        """
        logger.info("Importing dataset %s …", filename)

        try:
            # ---- 1. Read source into temp view to discover schema --------
            if filename.endswith(".gpkg"):
                src_sql = f"ST_Read('{filepath}')"
            else:
                src_sql = f"read_parquet('{filepath}')"

            self.conn.execute(
                f"CREATE OR REPLACE TEMP VIEW _import_src AS "
                f"SELECT * FROM {src_sql}"
            )
            columns = self.conn.execute("DESCRIBE _import_src").fetchall()

            # ---- 2. Detect geometry column & CRS -------------------------
            geom_col = None
            original_crs = None
            geom_candidates = ('geom', 'geometry', 'wkb_geometry', 'shape')
            for col_name, col_type, *_ in columns:
                upper = col_type.upper()
                if 'GEOMETRY' in upper or col_name.lower() in geom_candidates:
                    geom_col = col_name
                    original_crs = self._detect_crs(col_type)
                    break

            if geom_col is None:
                geom_col = columns[0][0]  # last resort

            # ---- 3. Build CTAS -------------------------------------------
            needs_reproject = original_crs is not None and original_crs != 4326
            if needs_reproject:
                geom_expr = (
                    f"ST_Transform(\"{geom_col}\", "
                    f"'EPSG:{original_crs}', 'EPSG:4326', true)"
                )
            else:
                geom_expr = f"\"{geom_col}\""

            attr_cols = [c[0] for c in columns if c[0] != geom_col]

            # _g is the 4326 geometry computed in a sub-select so that
            # expensive transforms are evaluated only once per row.
            inner_parts = [f'"{c}"' for c in attr_cols]
            inner_parts.append(f"{geom_expr} AS _g")

            outer_parts = [f'"{c}"' for c in attr_cols]
            outer_parts += [
                "_g AS geometry",
                "ST_XMin(_g) AS _bbox_minx",
                "ST_YMin(_g) AS _bbox_miny",
                "ST_XMax(_g) AS _bbox_maxx",
                "ST_YMax(_g) AS _bbox_maxy",
                "ST_X(ST_Centroid(_g)) AS _centroid_x",
                "ST_Y(ST_Centroid(_g)) AS _centroid_y",
            ]

            self.conn.execute(f"DROP TABLE IF EXISTS {table_name}")
            ctas = (
                f"CREATE TABLE {table_name} AS "
                f"SELECT {', '.join(outer_parts)} "
                f"FROM (SELECT {', '.join(inner_parts)} FROM _import_src) sub"
            )
            self.conn.execute(ctas)
            self.conn.execute("DROP VIEW IF EXISTS _import_src")

            # ---- 4. Compute & store metadata -----------------------------
            agg = self.conn.execute(f"""
                SELECT COUNT(*),
                       MIN(_bbox_minx), MIN(_bbox_miny),
                       MAX(_bbox_maxx), MAX(_bbox_maxy)
                FROM {table_name}
            """).fetchone()

            feature_count = agg[0]
            bounds = {
                'minx': agg[1] if agg[1] is not None else -10,
                'miny': agg[2] if agg[2] is not None else 35,
                'maxx': agg[3] if agg[3] is not None else 30,
                'maxy': agg[4] if agg[4] is not None else 72,
            }

            # Public columns (exclude internal helpers)
            col_info = self.conn.execute(f"DESCRIBE {table_name}").fetchall()
            public_columns = [
                {"name": c[0], "type": c[1]}
                for c in col_info
                if c[0] not in _INTERNAL_COLS
            ]

            columns_json = json.dumps(public_columns)

            self.conn.execute(
                "DELETE FROM _dataset_meta WHERE filename = ?", [filename]
            )
            self.conn.execute(
                "INSERT INTO _dataset_meta "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                [
                    filename, table_name,
                    stat.st_mtime, stat.st_size,
                    original_crs,
                    bounds['minx'], bounds['miny'],
                    bounds['maxx'], bounds['maxy'],
                    feature_count, columns_json,
                ],
            )

            meta = {
                'table_name':    table_name,
                'original_crs':  original_crs,
                'crs':           f"EPSG:{original_crs}" if original_crs else None,
                'bounds':        bounds,
                'feature_count': feature_count,
                'columns':       public_columns,
                'file_mtime':    stat.st_mtime,
                'file_size':     stat.st_size,
            }
            self._meta_cache[filename] = meta

            logger.info(
                "Imported %s: %s features, CRS=%s → EPSG:4326",
                filename, feature_count, original_crs,
            )
            return meta

        except Exception:
            # Clean up partial artefacts
            try:
                self.conn.execute(f"DROP TABLE IF EXISTS {table_name}")
            except Exception:
                pass
            try:
                self.conn.execute("DROP VIEW IF EXISTS _import_src")
            except Exception:
                pass
            raise

    # ------------------------------------------------------------------
    # Public query methods
    # ------------------------------------------------------------------
    def get_columns(self, filename):
        return self._meta(filename)['columns']

    def get_feature_count(self, filename):
        """Instant — returned from catalogue."""
        return self._meta(filename)['feature_count']

    def get_bounds(self, filename):
        """Instant — returned from catalogue."""
        return self._meta(filename)['bounds']

    def get_features_bbox(self, filename, bbox=None, limit=2000, offset=0,
                          filters=None):
        """Get features as GeoJSON FeatureCollection (EPSG:4326)."""
        meta = self._meta(filename)
        table = meta['table_name']
        attr_cols = self._attr_cols(filename)

        select_parts = [f'"{c}"' for c in attr_cols]
        select_parts.append("ST_AsGeoJSON(geometry) AS __geojson__")

        where_parts = []
        params = []

        if bbox:
            where_parts.append(self._bbox_where(bbox))

        if filters:
            for col, val in filters.items():
                if col in attr_cols:
                    where_parts.append(f'"{col}"::VARCHAR = ?')
                    params.append(str(val))

        where_clause = (" WHERE " + " AND ".join(where_parts)) if where_parts else ""
        query = (
            f"SELECT {', '.join(select_parts)} FROM {table}"
            f"{where_clause} LIMIT {limit} OFFSET {offset}"
        )

        with self._lock:
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

    def get_features_overview(self, filename, bbox=None, grid_size=0.5,
                              filters=None):
        """
        Fast grid-aggregated overview for zoomed-out views.

        Uses pre-computed _centroid_x / _centroid_y columns — no geometry
        operations at query time.  Bbox filtering is purely numeric.
        """
        meta = self._meta(filename)
        table = meta['table_name']
        attr_cols = self._attr_cols(filename)

        # Pick a category column for the dominant-category label
        cat_col = None
        for candidate in ('EC_hcat_n', 'crop_name', 'EC_trans_n'):
            if candidate in attr_cols:
                cat_col = candidate
                break

        half = grid_size / 2
        cx = f"FLOOR(_centroid_x / {grid_size}) * {grid_size} + {half}"
        cy = f"FLOOR(_centroid_y / {grid_size}) * {grid_size} + {half}"

        select_parts = [
            f"{cx} AS grid_x",
            f"{cy} AS grid_y",
            "COUNT(*) AS feature_count",
        ]
        if cat_col:
            select_parts.append(f'MODE("{cat_col}") AS dominant_category')

        where_parts = []
        params = []
        if bbox:
            where_parts.append(self._bbox_where(bbox))
        if filters:
            for col, val in filters.items():
                if col in attr_cols:
                    where_parts.append(f'"{col}"::VARCHAR = ?')
                    params.append(str(val))

        where_clause = (" WHERE " + " AND ".join(where_parts)) if where_parts else ""

        query = (
            f"SELECT {', '.join(select_parts)} FROM {table}"
            f"{where_clause} GROUP BY grid_x, grid_y "
            f"ORDER BY feature_count DESC LIMIT 5000"
        )

        with self._lock:
            result = self.conn.execute(query, params).fetchall()

        features = []
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
        with self._lock:
            result = self.conn.execute(
                f'SELECT DISTINCT "{column}" FROM {meta["table_name"]} '
                f'ORDER BY "{column}" LIMIT 500'
            ).fetchall()
        return [r[0] for r in result if r[0] is not None]

    def get_stats(self, filename):
        meta = self._meta(filename)
        table = meta['table_name']
        attr_cols = self._attr_cols(filename)
        stats = {"total_features": meta['feature_count'], "columns": {}}

        with self._lock:
            for col in attr_cols:
                col_info = {}
                try:
                    unique = self.conn.execute(
                        f'SELECT COUNT(DISTINCT "{col}") FROM {table}'
                    ).fetchone()[0]
                    col_info["unique_values"] = unique
                    if unique <= 20:
                        vals = self.conn.execute(
                            f'SELECT "{col}", COUNT(*) AS cnt FROM {table} '
                            f'GROUP BY "{col}" ORDER BY cnt DESC LIMIT 20'
                        ).fetchall()
                        col_info["value_counts"] = {
                            str(v[0]): v[1] for v in vals
                        }
                except Exception:
                    pass
                stats["columns"][col] = col_info

        return stats

    def reload_datasets(self):
        """Clear in-memory cache so next access re-checks the catalogue."""
        self._meta_cache.clear()
