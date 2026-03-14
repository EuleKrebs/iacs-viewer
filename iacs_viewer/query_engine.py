"""
DuckDB-based query engine for IACS data.
Supports both GeoPackage (.gpkg) and GeoParquet (.parquet) files.
"""
import duckdb
import json
import os
import glob


class QueryEngine:
    def __init__(self, data_dir="data"):
        self.data_dir = data_dir
        self.conn = duckdb.connect(":memory:")
        self.conn.execute("INSTALL spatial; LOAD spatial;")
        self._loaded_datasets = {}

    def list_datasets(self):
        """List available .gpkg and .parquet files in data directory."""
        datasets = []
        for ext in ("*.gpkg", "*.parquet"):
            for path in glob.glob(os.path.join(self.data_dir, ext)):
                name = os.path.basename(path)
                datasets.append({
                    "name": name,
                    "path": path,
                    "format": "geopackage" if name.endswith(".gpkg") else "geoparquet",
                    "size_mb": round(os.path.getsize(path) / 1024 / 1024, 2),
                })
        return datasets

    def _get_view_name(self, filename):
        """Generate a clean SQL view name from filename."""
        return "ds_" + os.path.splitext(filename)[0].replace("-", "_").replace(".", "_").replace(" ", "_")

    def load_dataset(self, filename):
        """Register a dataset file as a DuckDB view if not already loaded."""
        if filename in self._loaded_datasets:
            return self._loaded_datasets[filename]

        filepath = os.path.join(self.data_dir, filename)
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"Dataset not found: {filename}")

        view_name = self._get_view_name(filename)

        if filename.endswith(".gpkg"):
            self.conn.execute(
                f"CREATE OR REPLACE VIEW {view_name} AS SELECT * FROM ST_Read('{filepath}')"
            )
        elif filename.endswith(".parquet"):
            self.conn.execute(
                f"CREATE OR REPLACE VIEW {view_name} AS SELECT * FROM read_parquet('{filepath}')"
            )
        else:
            raise ValueError(f"Unsupported format: {filename}")

        self._loaded_datasets[filename] = view_name
        return view_name

    def get_columns(self, filename):
        """Get column names and types for a dataset."""
        view_name = self.load_dataset(filename)
        result = self.conn.execute(f"DESCRIBE {view_name}").fetchall()
        return [{"name": r[0], "type": r[1]} for r in result]

    def get_feature_count(self, filename):
        """Get total feature count."""
        view_name = self.load_dataset(filename)
        result = self.conn.execute(f"SELECT COUNT(*) FROM {view_name}").fetchone()
        return result[0]

    def get_bounds(self, filename):
        """Get the bounding box of all geometries."""
        view_name = self.load_dataset(filename)
        geom_col = self._get_geom_column(filename)
        result = self.conn.execute(f"""
            SELECT
                MIN(ST_XMin({geom_col})),
                MIN(ST_YMin({geom_col})),
                MAX(ST_XMax({geom_col})),
                MAX(ST_YMax({geom_col}))
            FROM {view_name}
        """).fetchone()
        return {"minx": result[0], "miny": result[1], "maxx": result[2], "maxy": result[3]}

    def _get_geom_column(self, filename):
        """Detect the geometry column name."""
        cols = self.get_columns(filename)
        for c in cols:
            if c["type"] in ("GEOMETRY", "BLOB", "WKB_GEOMETRY"):
                return c["name"]
            if c["name"].lower() in ("geom", "geometry", "wkb_geometry", "shape"):
                return c["name"]
        return "geom"

    def _get_attribute_columns(self, filename):
        """Get non-geometry column names."""
        cols = self.get_columns(filename)
        geom_col = self._get_geom_column(filename)
        return [c["name"] for c in cols if c["name"] != geom_col]

    def get_features_bbox(self, filename, bbox=None, limit=2000, offset=0, filters=None):
        """
        Get features as GeoJSON within optional bounding box.
        bbox: [minx, miny, maxx, maxy]
        filters: dict of {column: value} for exact match filtering
        """
        view_name = self.load_dataset(filename)
        geom_col = self._get_geom_column(filename)
        attr_cols = self._get_attribute_columns(filename)

        # Build SELECT with attribute columns + geometry as GeoJSON
        select_parts = [f'"{c}"' for c in attr_cols]
        select_parts.append(f"ST_AsGeoJSON({geom_col}) as __geojson__")
        select_clause = ", ".join(select_parts)

        where_parts = []
        params = []

        if bbox:
            minx, miny, maxx, maxy = bbox
            where_parts.append(
                f"ST_Intersects({geom_col}, ST_MakeEnvelope({minx}, {miny}, {maxx}, {maxy}))"
            )

        if filters:
            for col, val in filters.items():
                if col in attr_cols:
                    where_parts.append(f'"{col}" = ?')
                    params.append(val)

        where_clause = (" WHERE " + " AND ".join(where_parts)) if where_parts else ""

        query = f"SELECT {select_clause} FROM {view_name}{where_clause} LIMIT {limit} OFFSET {offset}"
        result = self.conn.execute(query, params).fetchall()

        # Column names for the result
        col_names = attr_cols + ["__geojson__"]

        features = []
        for row in result:
            row_dict = dict(zip(col_names, row))
            geojson_str = row_dict.pop("__geojson__")
            if geojson_str:
                geometry = json.loads(geojson_str)
            else:
                geometry = None

            # Clean properties: convert non-serializable types
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

        return {
            "type": "FeatureCollection",
            "features": features,
        }

    def get_unique_values(self, filename, column):
        """Get unique values for a column (for filter dropdowns)."""
        view_name = self.load_dataset(filename)
        attr_cols = self._get_attribute_columns(filename)
        if column not in attr_cols:
            return []
        result = self.conn.execute(
            f'SELECT DISTINCT "{column}" FROM {view_name} ORDER BY "{column}" LIMIT 500'
        ).fetchall()
        return [r[0] for r in result if r[0] is not None]

    def get_stats(self, filename):
        """Get summary statistics for the dataset."""
        view_name = self.load_dataset(filename)
        attr_cols = self._get_attribute_columns(filename)

        count = self.get_feature_count(filename)
        stats = {"total_features": count, "columns": {}}

        for col in attr_cols:
            col_info = {}
            try:
                unique = self.conn.execute(
                    f'SELECT COUNT(DISTINCT "{col}") FROM {view_name}'
                ).fetchone()[0]
                col_info["unique_values"] = unique
                if unique <= 20:
                    vals = self.conn.execute(
                        f'SELECT "{col}", COUNT(*) as cnt FROM {view_name} GROUP BY "{col}" ORDER BY cnt DESC LIMIT 20'
                    ).fetchall()
                    col_info["value_counts"] = {str(v[0]): v[1] for v in vals}
            except Exception:
                pass
            stats["columns"][col] = col_info

        return stats
