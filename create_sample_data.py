"""
Create a minimal sample GeoPackage with synthetic IACS-like field data.
Uses a few agricultural parcels around Europe for demonstration.
"""
import geopandas as gpd
from shapely.geometry import Polygon
import numpy as np
import os

np.random.seed(42)

def make_parcel(cx, cy, size=0.005, irregular=True):
    """Create a slightly irregular polygon around center point."""
    n = 5 if irregular else 4
    angles = np.sort(np.random.uniform(0, 2 * np.pi, n))
    r = size * (1 + np.random.uniform(-0.3, 0.3, n))
    xs = cx + r * np.cos(angles)
    ys = cy + r * np.sin(angles)
    coords = list(zip(xs, ys))
    coords.append(coords[0])
    return Polygon(coords)

# Sample regions: (center_lon, center_lat, country, num_parcels)
regions = [
    (11.5, 48.1, "DE", "Germany", 30),
    (2.3, 48.8, "FR", "France", 25),
    (12.5, 41.9, "IT", "Italy", 20),
    (5.1, 52.1, "NL", "Netherlands", 15),
    (-3.7, 40.4, "ES", "Spain", 20),
    (16.3, 48.2, "AT", "Austria", 15),
]

crop_types = [
    ("110", "Wheat", "Cereals", "Arable land", "A1"),
    ("120", "Barley", "Cereals", "Arable land", "A1"),
    ("130", "Maize", "Cereals", "Arable land", "A1"),
    ("210", "Rapeseed", "Oilseeds", "Arable land", "A2"),
    ("310", "Potatoes", "Root crops", "Arable land", "A3"),
    ("410", "Sugar beet", "Root crops", "Arable land", "A3"),
    ("510", "Grassland", "Grass", "Permanent grassland", "B1"),
    ("610", "Vineyard", "Permanent crops", "Permanent crops", "C1"),
    ("710", "Olive grove", "Permanent crops", "Permanent crops", "C1"),
    ("810", "Fallow", "Fallow", "Arable land", "A9"),
]

records = []
field_counter = 0

for cx, cy, nation_code, nation_name, n_parcels in regions:
    for i in range(n_parcels):
        field_counter += 1
        # Spread parcels in a grid-like pattern with some randomness
        row, col = divmod(i, 5)
        px = cx + col * 0.012 + np.random.uniform(-0.003, 0.003)
        py = cy + row * 0.012 + np.random.uniform(-0.003, 0.003)
        
        crop = crop_types[np.random.randint(len(crop_types))]
        size = np.random.uniform(0.003, 0.008)
        field_size = round(np.random.uniform(0.5, 25.0), 2)
        crop_area = round(field_size * np.random.uniform(0.7, 1.0), 2)
        
        records.append({
            "field_id": f"{nation_code}_{field_counter:05d}",
            "farm_id": f"FARM_{nation_code}_{np.random.randint(1, 50):03d}",
            "crop_code": crop[0],
            "crop_name": crop[1],
            "EC_trans_n": crop[2],
            "EC_hcat_n": crop[3],
            "EC_hcat_c": crop[4],
            "organic": bool(np.random.random() < 0.15),
            "field_size": field_size,
            "crop_area": crop_area,
            "nation": nation_code,
            "year": int(np.random.choice([2021, 2022, 2023])),
            "geometry": make_parcel(px, py, size),
        })

gdf = gpd.GeoDataFrame(records, crs="EPSG:4326")

out_path = os.path.join(os.path.dirname(__file__), "data", "sample_iacs.gpkg")
gdf.to_file(out_path, driver="GPKG", layer="fields")
print(f"Created {out_path} with {len(gdf)} features")

# Also create a small parquet version for testing
try:
    parquet_path = os.path.join(os.path.dirname(__file__), "data", "sample_iacs.parquet")
    gdf.to_parquet(parquet_path)
    print(f"Created {parquet_path} with {len(gdf)} features")
except Exception as e:
    print(f"Parquet creation skipped: {e}")
