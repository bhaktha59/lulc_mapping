"""
Configuration and constants for Tamil Nadu LULC Mapping Workflow.
Defines LULC classes, color palette, feature stacks, and Earth Engine configurations.
"""

import os

# Base Directories
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PORTAL_DIR = os.path.dirname(BASE_DIR)
DATA_DIR = os.path.join(PORTAL_DIR, "data")
PROJECTS_DIR = os.path.join(DATA_DIR, "projects")

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(PROJECTS_DIR, exist_ok=True)

# Google Earth Engine Configuration
PROJECT_ID = "favorable-bolt-489809-c7"

# Standard Tamil Nadu LULC Classification Scheme (Configurable per study area)
DEFAULT_LULC_CLASSES = {
    1: {
        "id": 1,
        "name": "Forest",
        "color": "#006400",
        "desc": "Reserve forests, hill canopy & dense woodland vegetation",
        "min_samples": 30,
    },
    2: {
        "id": 2,
        "name": "Waterbodies",
        "color": "#0000FF",
        "desc": "Lakes, reservoirs, irrigation tanks & perennial streams",
        "min_samples": 20,
    },
    3: {
        "id": 3,
        "name": "Cropland",
        "color": "#32CD32",
        "desc": "Active agricultural plains, intensive crops, paddy & orchards",
        "min_samples": 50,
    },
    4: {
        "id": 4,
        "name": "Fallowland",
        "color": "#F4A460",
        "desc": "Temporarily uncropped agricultural arable plots & seasonal fallows",
        "min_samples": 30,
    },
    5: {
        "id": 5,
        "name": "Land with scrub",
        "color": "#9ACD32",
        "desc": "Foothill thorn scrub, open bushland & degraded vegetation",
        "min_samples": 25,
    },
    6: {
        "id": 6,
        "name": "Land without scrub",
        "color": "#D2B48C",
        "desc": "Open vacant ground, uncultivated sheet soil & open barren plain",
        "min_samples": 25,
    },
    7: {
        "id": 7,
        "name": "Built-up / settlements",
        "color": "#FF0000",
        "desc": "Towns, rural hamlets, residential buildings, roads & paved infrastructure",
        "min_samples": 40,
    },
    8: {
        "id": 8,
        "name": "Barren land / Rocky",
        "color": "#808080",
        "desc": "Exposed sheet rock, hill outcrops, dry boulder terrain & quarries",
        "min_samples": 20,
    },
}

LULC_CLASSES = DEFAULT_LULC_CLASSES
LULC_PALETTE = [LULC_CLASSES[i]["color"] for i in range(1, 9)]

def get_default_classes():
    """Returns a deep copy of the default Tamil Nadu classification scheme."""
    import copy
    return copy.deepcopy(DEFAULT_LULC_CLASSES)


# 14 Multi-Source Predictor Features
FEATURE_NAMES = [
    # 6 Surface Reflectance Optical Bands
    "blue",
    "green",
    "red",
    "nir",
    "swir1",
    "swir2",
    # 6 Spectral Indices
    "ndvi",
    "ndbi",
    "mndwi",
    "bsi",
    "ui",
    "savi",
    # 2 SRTM Topographic Bands
    "elevation",
    "slope",
]

# Seasonal Filtering Window: Post-monsoon dry winter (Jan 1 to Apr 1)
def get_temporal_window(year: int):
    return (f"{year}-01-01", f"{year}-04-01")

# Satellite Dataset Registry (Extensible Architecture)
SATELLITE_DATASETS = {
    "landsat_8_9": {
        "id": "landsat_8_9",
        "name": "Landsat 8 OLI & Landsat 9 OLI-2 Combined",
        "short_name": "Landsat 8 & 9",
        "sensor_family": "Landsat",
        "native_res_m": 30,
        "resolution_desc": "30 m (Optical & SWIR)",
        "is_operational": True,
        "min_year": 2022,
        "max_year": 2026,
        "collections": ["LANDSAT/LC08/C02/T1_L2", "LANDSAT/LC09/C02/T1_L2"],
    },
    "landsat_9": {
        "id": "landsat_9",
        "name": "Landsat 9 OLI-2",
        "short_name": "Landsat 9",
        "sensor_family": "Landsat",
        "native_res_m": 30,
        "resolution_desc": "30 m (Optical & SWIR)",
        "is_operational": True,
        "min_year": 2022,
        "max_year": 2026,
        "collections": ["LANDSAT/LC09/C02/T1_L2"],
    },
    "landsat_8": {
        "id": "landsat_8",
        "name": "Landsat 8 OLI",
        "short_name": "Landsat 8",
        "sensor_family": "Landsat",
        "native_res_m": 30,
        "resolution_desc": "30 m (Optical & SWIR)",
        "is_operational": True,
        "min_year": 2013,
        "max_year": 2026,
        "collections": ["LANDSAT/LC08/C02/T1_L2"],
    },
    "landsat_5_7": {
        "id": "landsat_5_7",
        "name": "Landsat 5 TM & Landsat 7 ETM+ Combined",
        "short_name": "Landsat 5 & 7",
        "sensor_family": "Landsat",
        "native_res_m": 30,
        "resolution_desc": "30 m (Optical & SWIR)",
        "is_operational": True,
        "min_year": 1984,
        "max_year": 2012,
        "collections": ["LANDSAT/LT05/C02/T1_L2", "LANDSAT/LE07/C02/T1_L2"],
    },
    "sentinel_2": {
        "id": "sentinel_2",
        "name": "Sentinel-2A & Sentinel-2B MSI Harmonized",
        "short_name": "Sentinel-2A & 2B",
        "sensor_family": "Sentinel",
        "native_res_m": 10,
        "resolution_desc": "10 m (Optical & NIR) / 20 m (SWIR)",
        "is_operational": True,
        "min_year": 2015,
        "max_year": 2026,
        "collections": ["COPERNICUS/S2_SR_HARMONIZED"],
    },
    "sentinel_2a": {
        "id": "sentinel_2a",
        "name": "Sentinel-2A MSI",
        "short_name": "Sentinel-2A",
        "sensor_family": "Sentinel",
        "native_res_m": 10,
        "resolution_desc": "10 m (Optical & NIR) / 20 m (SWIR)",
        "is_operational": True,
        "min_year": 2015,
        "max_year": 2026,
        "collections": ["COPERNICUS/S2_SR_HARMONIZED"],
    },
    "sentinel_2b": {
        "id": "sentinel_2b",
        "name": "Sentinel-2B MSI",
        "short_name": "Sentinel-2B",
        "sensor_family": "Sentinel",
        "native_res_m": 10,
        "resolution_desc": "10 m (Optical & NIR) / 20 m (SWIR)",
        "is_operational": True,
        "min_year": 2017,
        "max_year": 2026,
        "collections": ["COPERNICUS/S2_SR_HARMONIZED"],
    },
    # Future placeholder: Landsat 10 (Landsat Next)
    # Marked as NOT operational so it is NEVER displayed in active UI dropdowns,
    # but the architectural hook is ready when officially released.
    "landsat_10": {
        "id": "landsat_10",
        "name": "Landsat 10 (Landsat Next)",
        "short_name": "Landsat 10",
        "sensor_family": "Landsat",
        "native_res_m": 10,
        "resolution_desc": "10 m (Landsat Next Planned)",
        "is_operational": False, # Future readiness; not displayed in operational lists
        "min_year": 2030,
        "max_year": 2040,
        "collections": ["LANDSAT/LC10/C02/T1_L2"],
    },
}

# Predefined Year & Satellite Dataset Options for Dropdown UI
STUDY_YEAR_DATASET_OPTIONS = [
    # Recent years with both Landsat 8 & 9 and Sentinel-2
    {"year": 2025, "dataset": "landsat_8_9", "label": "2025 (Landsat 8 & 9 - 30m)", "sensor": "Landsat 8 & 9", "res": "30m"},
    {"year": 2025, "dataset": "sentinel_2", "label": "2025 (Sentinel-2A & 2B - 10m)", "sensor": "Sentinel-2A & 2B", "res": "10m"},
    {"year": 2024, "dataset": "landsat_8_9", "label": "2024 (Landsat 8 & 9 - 30m)", "sensor": "Landsat 8 & 9", "res": "30m"},
    {"year": 2024, "dataset": "sentinel_2", "label": "2024 (Sentinel-2A & 2B - 10m)", "sensor": "Sentinel-2A & 2B", "res": "10m"},
    {"year": 2023, "dataset": "landsat_8_9", "label": "2023 (Landsat 8 & 9 - 30m)", "sensor": "Landsat 8 & 9", "res": "30m"},
    {"year": 2023, "dataset": "sentinel_2", "label": "2023 (Sentinel-2A & 2B - 10m)", "sensor": "Sentinel-2A & 2B", "res": "10m"},
    {"year": 2022, "dataset": "landsat_8_9", "label": "2022 (Landsat 8 & 9 - 30m)", "sensor": "Landsat 8 & 9", "res": "30m"},
    {"year": 2022, "dataset": "sentinel_2", "label": "2022 (Sentinel-2A & 2B - 10m)", "sensor": "Sentinel-2A & 2B", "res": "10m"},
    # Mid-period years with Landsat 8 and Sentinel-2
    {"year": 2021, "dataset": "landsat_8", "label": "2021 (Landsat 8 - 30m)", "sensor": "Landsat 8", "res": "30m"},
    {"year": 2021, "dataset": "sentinel_2", "label": "2021 (Sentinel-2A & 2B - 10m)", "sensor": "Sentinel-2A & 2B", "res": "10m"},
    {"year": 2020, "dataset": "landsat_8", "label": "2020 (Landsat 8 - 30m)", "sensor": "Landsat 8", "res": "30m"},
    {"year": 2020, "dataset": "sentinel_2", "label": "2020 (Sentinel-2A & 2B - 10m)", "sensor": "Sentinel-2A & 2B", "res": "10m"},
    {"year": 2019, "dataset": "landsat_8", "label": "2019 (Landsat 8 - 30m)", "sensor": "Landsat 8", "res": "30m"},
    {"year": 2019, "dataset": "sentinel_2", "label": "2019 (Sentinel-2A & 2B - 10m)", "sensor": "Sentinel-2A & 2B", "res": "10m"},
    {"year": 2018, "dataset": "landsat_8", "label": "2018 (Landsat 8 - 30m)", "sensor": "Landsat 8", "res": "30m"},
    {"year": 2018, "dataset": "sentinel_2", "label": "2018 (Sentinel-2A & 2B - 10m)", "sensor": "Sentinel-2A & 2B", "res": "10m"},
    {"year": 2017, "dataset": "landsat_8", "label": "2017 (Landsat 8 - 30m)", "sensor": "Landsat 8", "res": "30m"},
    {"year": 2017, "dataset": "sentinel_2", "label": "2017 (Sentinel-2A & 2B - 10m)", "sensor": "Sentinel-2A & 2B", "res": "10m"},
    {"year": 2016, "dataset": "landsat_8", "label": "2016 (Landsat 8 - 30m)", "sensor": "Landsat 8", "res": "30m"},
    {"year": 2016, "dataset": "sentinel_2a", "label": "2016 (Sentinel-2A - 10m)", "sensor": "Sentinel-2A", "res": "10m"},
    # Historic Landsat years
    {"year": 2011, "dataset": "landsat_5_7", "label": "2011 (Landsat 5 & 7 - 30m)", "sensor": "Landsat 5 & 7", "res": "30m"},
    {"year": 2006, "dataset": "landsat_5_7", "label": "2006 (Landsat 5 & 7 - 30m)", "sensor": "Landsat 5 & 7", "res": "30m"},
    {"year": 2001, "dataset": "landsat_5_7", "label": "2001 (Landsat 5 & 7 - 30m)", "sensor": "Landsat 5 & 7", "res": "30m"},
]

SUPPORTED_YEARS = sorted(list(set([opt["year"] for opt in STUDY_YEAR_DATASET_OPTIONS])), reverse=True)
