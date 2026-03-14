# IACS Viewer

A web-based GIS application for exploring IACS (Integrated Administration and Control System) agricultural parcel data from the [Europe-LAND HE Project](https://zenodo.org/records/15692199).

## Features

- **Interactive map** with crop-type colored parcels (Leaflet + CartoDB dark basemap)
- **DuckDB-powered queries** — fast spatial + attribute filtering on GeoPackage and GeoParquet files
- **Bbox viewport loading** — only fetches features visible on screen
- **Attribute filters** — filter by nation, year, crop type, EC category, organic status
- **Feature inspector** — click any parcel to see full attribute details
- **Dynamic legend** — shows crop types currently on screen
- **Multi-format support** — drop `.gpkg` or `.parquet` files in `data/` and they appear automatically

## Quick Start

### 1. Install dependencies

```bash
python -m venv .venv
source .venv/bin/activate
pip install flask duckdb geopandas shapely fiona pyarrow python-dotenv requests
```

### 2. Create sample data (optional)

```bash
python create_sample_data.py
```

This creates a small GeoPackage + GeoParquet with ~125 synthetic IACS parcels across 6 EU countries.

### 3. Run the app

```bash
python app.py
```

Open [http://localhost:5000](http://localhost:5000) in your browser.

### Using your own data

Place any `.gpkg` or `.parquet` files in the `data/` directory. They will be automatically detected and available in the dataset selector.

## Architecture

```
iacs-viewer/
├── app.py                     # Flask entry point
├── create_sample_data.py      # Generate sample IACS data
├── data/                      # Drop .gpkg/.parquet files here
├── iacs_viewer/
│   ├── __init__.py            # App factory
│   ├── config.py              # Configuration
│   ├── query_engine.py        # DuckDB spatial query engine
│   ├── routes/
│   │   ├── api.py             # REST API (datasets, features, filters)
│   │   └── main.py            # Frontend route
│   ├── static/
│   │   ├── css/style.css      # Dark theme UI
│   │   └── js/logic.js        # Map + interaction logic
│   └── templates/
│       └── index.html         # Main page
└── pyproject.toml
```

## API Endpoints

| Endpoint | Description |
|---|---|
| `GET /api/datasets` | List available datasets |
| `GET /api/datasets/<file>/info` | Dataset metadata (bounds, columns, count) |
| `GET /api/datasets/<file>/features?bbox=&limit=&filter_*=` | GeoJSON features with spatial/attribute filters |
| `GET /api/datasets/<file>/values/<column>` | Unique values for filter dropdowns |
| `GET /api/datasets/<file>/stats` | Summary statistics |

## Dataset

The IACS dataset is available from [Zenodo](https://zenodo.org/records/15692199). Download GeoPackage or Parquet files and place them in the `data/` directory.

## License

MIT License
