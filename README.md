# IACS Viewer

A web-based GIS application for exploring **IACS** (Integrated Administration and Control System) agricultural parcel data from the [Europe-LAND HE Project](https://zenodo.org/records/15692199).

IACS data describes millions of agricultural field parcels across the European Union — including crop types, field sizes, organic status, and geographic boundaries. This viewer lets you browse and filter that data interactively on a map, without needing any GIS software.

![Python](https://img.shields.io/badge/Python-3.11+-blue)
![Flask](https://img.shields.io/badge/Flask-3.x-green)
![DuckDB](https://img.shields.io/badge/DuckDB-1.0+-yellow)
![License](https://img.shields.io/badge/License-MIT-lightgrey)

---

## Features

- **Interactive map** — Leaflet-based map with a dark basemap, showing crop-colored parcels
- **DuckDB-powered queries** — fast in-process spatial and attribute filtering (no external database needed)
- **Viewport loading** — only fetches features visible on the current screen area
- **Zoom-adaptive display** — shows clustered overview points when zoomed out, full polygon geometries when zoomed in
- **Attribute filters** — filter parcels by nation, year, crop type, EC category, and organic status
- **Feature inspector** — click any parcel on the map to see its full attribute details
- **Dynamic legend** — automatically shows crop types currently visible on screen
- **Multi-format support** — works with GeoPackage (`.gpkg`) and GeoParquet (`.parquet` / `.geoparquet`) files
- **Built-in data catalog** — browse and download IACS datasets directly from Zenodo within the app
- **Automatic CRS handling** — transparently reprojects data from EPSG:3035 (or other CRS) to web-friendly EPSG:4326

---

## Quick Start

### Prerequisites

- **Python 3.11 or newer** — [Download Python](https://www.python.org/downloads/)
- **pip** (comes with Python) or **[uv](https://docs.astral.sh/uv/)** (faster alternative)

### Option A: Run with pip (simplest)

1. **Clone the repository** (or download and unzip it):

   ```bash
   git clone <repository-url>
   cd iacs-viewer
   ```

2. **Create a virtual environment and install dependencies:**

   ```bash
   python -m venv .venv
   source .venv/bin/activate        # On macOS / Linux
   # .venv\Scripts\activate          # On Windows
   pip install flask duckdb geopandas shapely fiona pyarrow python-dotenv requests waitress
   ```

3. **Generate sample data** (optional — creates a small demo dataset):

   ```bash
   python create_sample_data.py
   ```

4. **Start the application:**

   ```bash
   python app.py
   ```

5. **Open your browser** at [http://localhost:5000](http://localhost:5000).

### Option B: Run with uv (recommended)

[uv](https://docs.astral.sh/uv/) is a fast Python package manager that handles virtual environments automatically.

1. **Install uv** (if you don't have it):

   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh    # macOS / Linux
   # powershell -c "irm https://astral.sh/uv/install.ps1 | iex"  # Windows
   ```

2. **Clone and run:**

   ```bash
   git clone <repository-url>
   cd iacs-viewer
   uv sync                # creates .venv and installs everything from uv.lock
   uv run python app.py   # starts the server
   ```

3. **Open your browser** at [http://localhost:5000](http://localhost:5000).

### Option C: Run with Docker

1. **Clone the repository:**

   ```bash
   git clone <repository-url>
   cd iacs-viewer
   ```

2. **Start with Docker Compose:**

   ```bash
   docker compose up --build
   ```

3. **Open your browser** at [http://localhost:5000](http://localhost:5000).

   The `data/` folder is mounted as a volume, so you can add datasets without rebuilding the container.

---

## Getting Data

### Use the built-in Data Catalog

The easiest way to get real IACS data:

1. Start the app and open it in your browser.
2. Click the **"Data Catalog"** button in the top-right header.
3. Browse available datasets from [Zenodo](https://zenodo.org/records/15692199).
4. Click **Download** on any dataset — the app will download and extract it automatically.
5. Once extracted, the dataset appears in the **Dataset** dropdown on the left sidebar.

### Manually add data files

You can also place data files directly into the `data/` folder:

1. Download GeoPackage (`.gpkg`) or GeoParquet (`.parquet` / `.geoparquet`) files from [Zenodo](https://zenodo.org/records/15692199) or any other source.
2. Copy them into the `data/` directory at the project root.
3. Reload the app (or click the dataset dropdown) — they appear automatically.

### Generate sample data

For testing without downloading anything:

```bash
python create_sample_data.py
```

This creates ~125 synthetic IACS parcels across 6 EU countries in both GeoPackage and GeoParquet formats.

---

## How to Use the Viewer

Once the app is running and you have data loaded:

1. **Select a dataset** from the dropdown in the left sidebar.
2. **Pan and zoom** the map to explore parcels. The app automatically loads features in the current viewport.
3. **Apply filters** to narrow down parcels by nation, year, crop type, EC category, or organic status. Click "Apply Filters" after making selections.
4. **Click a parcel** on the map to see its full details in the "Feature Details" panel.
5. **Check the legend** at the bottom of the sidebar to see what crop types are currently displayed and their colors.

### Understanding the display modes

- **Zoomed out** (below zoom level 12): The map shows **clustered overview points**. Each circle represents a group of parcels in that area. The size indicates how many parcels are in the cluster.
- **Zoomed in** (zoom level 12+): The map shows **full polygon outlines** of individual parcels, colored by crop type.

---

## Project Structure

```
iacs-viewer/
├── app.py                          # Flask entry point — run this to start the server
├── create_sample_data.py           # Script to generate demo IACS data
├── data/                           # Place .gpkg / .parquet data files here
├── iacs_viewer/
│   ├── __init__.py                 # App factory — creates and configures the Flask app
│   ├── config.py                   # Configuration (data directory, debug mode)
│   ├── query_engine.py             # DuckDB spatial query engine (core data logic)
│   ├── routes/
│   │   ├── api.py                  # REST API endpoints (datasets, features, filters)
│   │   ├── main.py                 # Serves the frontend HTML page
│   │   └── populate.py             # Data catalog & download manager (Zenodo integration)
│   ├── static/
│   │   ├── css/style.css           # Dark-theme UI styles
│   │   └── js/logic.js             # Map interaction, data loading, filtering logic
│   └── templates/
│       └── index.html              # Main HTML page (Leaflet map + sidebar UI)
├── docker-compose.yml              # Docker Compose config for containerized deployment
├── Dockerfile                      # Docker image build instructions
├── entrypoint.sh                   # Container startup script
├── pyproject.toml                  # Python project metadata and dependencies
└── uv.lock                         # Locked dependency versions (for uv)
```

---

## API Reference

The app exposes a REST API that the frontend uses. You can also query it directly (e.g., with `curl` or from other scripts).

| Endpoint | Method | Description |
|---|---|---|
| `/api/datasets` | GET | List all available datasets (files in `data/`) |
| `/api/datasets/<file>/info` | GET | Dataset metadata: bounds, columns, feature count, CRS |
| `/api/datasets/<file>/features` | GET | GeoJSON features with spatial + attribute filtering |
| `/api/datasets/<file>/values/<column>` | GET | Unique values for a column (for filter dropdowns) |
| `/api/datasets/<file>/stats` | GET | Summary statistics (unique counts, value distributions) |
| `/api/populate/catalog` | GET | Fetch available datasets from Zenodo |
| `/api/populate/download` | POST | Start downloading a dataset from Zenodo |
| `/api/populate/downloads/status` | GET | Check download progress |

### Features endpoint query parameters

`GET /api/datasets/<file>/features`

| Parameter | Example | Description |
|---|---|---|
| `bbox` | `9.5,46.3,17.2,49.0` | Bounding box (minx,miny,maxx,maxy) in EPSG:4326 |
| `zoom` | `10` | Current map zoom level (determines overview vs. full mode) |
| `limit` | `3000` | Maximum number of features to return (default: 3000) |
| `offset` | `0` | Pagination offset |
| `mode` | `full` or `overview` | Force display mode (auto-detected if omitted) |
| `filter_nation` | `AT` | Filter by nation code |
| `filter_year` | `2023` | Filter by year |
| `filter_crop_name` | `Wheat` | Filter by crop name |
| `filter_EC_hcat_n` | `Arable land` | Filter by EC category |
| `filter_organic` | `true` | Filter by organic status |

---

## Configuration

The app can be configured via environment variables or a `.env` file in the project root:

| Variable | Default | Description |
|---|---|---|
| `DATA_DIR` | `data` | Path to the directory containing data files |
| `SECRET_KEY` | `dev-secret-key` | Flask secret key (change for production) |
| `FLASK_ENV` | `development` | Set to `production` to disable debug mode |

Example `.env` file:

```
DATA_DIR=/path/to/my/iacs-data
SECRET_KEY=my-secret-key
FLASK_ENV=production
```

---

## Technology Stack

| Component | Technology | Purpose |
|---|---|---|
| Backend | [Flask](https://flask.palletsprojects.com/) | Web framework serving API and frontend |
| Query Engine | [DuckDB](https://duckdb.org/) | In-process analytical database with spatial extensions |
| Map | [Leaflet](https://leafletjs.com/) | Interactive web map rendering |
| Basemap | [CartoDB Dark Matter](https://carto.com/basemaps/) | Dark-themed map tiles |
| Data Formats | GeoPackage, GeoParquet | OGC-standard geospatial file formats |
| Production Server | [Waitress](https://docs.pylonsproject.org/projects/waitress/) | Production-grade WSGI server |

---

## Troubleshooting

### "No datasets found"

Make sure you have data files in the `data/` directory. Either:
- Run `python create_sample_data.py` to generate sample data
- Use the built-in Data Catalog to download real datasets
- Manually place `.gpkg` or `.parquet` files in `data/`

### "DuckDB spatial extension error"

DuckDB automatically downloads its spatial extension on first use. Make sure you have internet access on first run, or install it manually:

```python
import duckdb
con = duckdb.connect()
con.execute("INSTALL spatial")
```

### Map shows no parcels

- Check that you have selected a dataset in the dropdown
- Try zooming in to the area where the data is located (the map auto-zooms to the dataset bounds)
- Check the browser developer console (F12) for error messages

### Docker: permission errors

If you get permission errors with Docker, make sure the `data/` directory exists and is writable:

```bash
mkdir -p data
chmod 755 data
```

---

## License

MIT License — see [LICENSE](LICENSE) for details.

## Data Source

The IACS harmonized dataset is produced by the [Europe-LAND Horizon Europe Project](https://zenodo.org/records/15692199) and available under open-access terms from Zenodo.
