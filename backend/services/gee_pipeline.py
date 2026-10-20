"""
Google Earth Engine Pipeline for Tamil Nadu LULC Mapping.
Acquires satellite imagery for any uploaded study area in Tamil Nadu,
handles cloud masking, compositing, 14-band feature extraction, and tile URL generation.
"""

import ee
from config import PROJECT_ID, get_temporal_window, FEATURE_NAMES

_gee_initialized = False


def initialize_gee():
    """Initializes Google Earth Engine with the authenticated project."""
    global _gee_initialized
    if _gee_initialized:
        return True
    try:
        ee.Initialize(project=PROJECT_ID)
        _gee_initialized = True
        return True
    except Exception as e:
        print(f"Earth Engine initialization error: {e}")
        return False


def mask_landsat_sr(image):
    """
    Applies bitwise cloud and shadow masking using QA_PIXEL and QA_RADSAT.
    """
    qa = image.select("QA_PIXEL")
    dilated_cloud = 1 << 1
    cirrus = 1 << 2
    cloud = 1 << 3
    shadow = 1 << 4
    snow = 1 << 5

    mask = (
        qa.bitwiseAnd(dilated_cloud)
        .eq(0)
        .And(qa.bitwiseAnd(cirrus).eq(0))
        .And(qa.bitwiseAnd(cloud).eq(0))
        .And(qa.bitwiseAnd(shadow).eq(0))
        .And(qa.bitwiseAnd(snow).eq(0))
    )

    radsat = image.select("QA_RADSAT")
    mask = mask.And(radsat.eq(0))
    return image.updateMask(mask)


def scale_landsat_sr(image):
    """
    Scales surface reflectance: optical bands * 0.0000275 - 0.2.
    """
    optical = image.select(["SR_B.*"]).multiply(0.0000275).add(-0.2)
    return image.addBands(optical, None, True)


def mask_s2_sr(image):
    """
    Applies bitwise and scene classification masking to Sentinel-2 Level-2A SR imagery.
    Masks clouds and cirrus using QA60, and shadows/clouds using the SCL band.
    """
    qa = image.select("QA60")
    cloud_bit = 1 << 10
    cirrus_bit = 1 << 11
    qa_mask = qa.bitwiseAnd(cloud_bit).eq(0).And(qa.bitwiseAnd(cirrus_bit).eq(0))

    scl = image.select("SCL")
    # SCL values to mask out:
    # 3: Cloud shadows, 8: Cloud medium prob, 9: Cloud high prob, 10: Thin cirrus
    scl_mask = (
        scl.neq(3)
        .And(scl.neq(8))
        .And(scl.neq(9))
        .And(scl.neq(10))
    )
    return image.updateMask(qa_mask.And(scl_mask))


def scale_s2_sr(image):
    """
    Scales Sentinel-2 Level-2A surface reflectance: divide by 10000.0 (multiply by 0.0001).
    """
    optical = image.select(["B2", "B3", "B4", "B8", "B11", "B12"]).multiply(0.0001)
    return image.addBands(optical, None, True)


def check_satellite_availability(geometry, year: int, dataset: str = "auto"):
    """
    Checks if valid satellite scenes are available for the study area geometry and year.
    Returns availability status and scene count without needing full image compositing.
    """
    initialize_gee()
    ee_geom = ee.Geometry(geometry)
    start_date, end_date = get_temporal_window(year)
    ds_key = (dataset or "auto").lower().strip()

    if ds_key == "auto":
        if year >= 2022:
            ds_key = "landsat_8_9"
        elif year >= 2013:
            ds_key = "landsat_8"
        else:
            ds_key = "landsat_5_7"

    if ds_key == "landsat_10":
        return {
            "available": False,
            "scenes_count": 0,
            "year": year,
            "dataset": ds_key,
            "sensor": "Landsat 10 (Landsat Next)",
            "message": "Landsat 10 is not currently an operational dataset. Reserved for future mission deployment.",
        }

    if ds_key in ["sentinel_2", "sentinel_2a", "sentinel_2b"]:
        if year < 2015 or (ds_key == "sentinel_2b" and year < 2017):
            return {
                "available": False,
                "scenes_count": 0,
                "year": year,
                "dataset": ds_key,
                "sensor": "Sentinel-2",
                "message": f"Sentinel-2 data is not available for study year {year}.",
            }
        col = ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED").filterBounds(ee_geom).filterDate(start_date, end_date)
        if ds_key == "sentinel_2a":
            col = col.filter(ee.Filter.eq("SPACECRAFT_NAME", "Sentinel-2A"))
            sensor = "Sentinel-2A MSI"
            res = "10m"
        elif ds_key == "sentinel_2b":
            col = col.filter(ee.Filter.eq("SPACECRAFT_NAME", "Sentinel-2B"))
            sensor = "Sentinel-2B MSI"
            res = "10m"
        else:
            sensor = "Sentinel-2A & Sentinel-2B MSI Harmonized"
            res = "10m"
    elif ds_key == "landsat_9":
        col = ee.ImageCollection("LANDSAT/LC09/C02/T1_L2").filterBounds(ee_geom).filterDate(start_date, end_date)
        sensor = "Landsat 9 OLI-2"
        res = "30m"
    elif ds_key == "landsat_8":
        col = ee.ImageCollection("LANDSAT/LC08/C02/T1_L2").filterBounds(ee_geom).filterDate(start_date, end_date)
        sensor = "Landsat 8 OLI"
        res = "30m"
    elif ds_key == "landsat_8_9":
        col8 = ee.ImageCollection("LANDSAT/LC08/C02/T1_L2").filterBounds(ee_geom).filterDate(start_date, end_date)
        col9 = ee.ImageCollection("LANDSAT/LC09/C02/T1_L2").filterBounds(ee_geom).filterDate(start_date, end_date)
        col = col8.merge(col9)
        sensor = "Landsat 8 & 9"
        res = "30m"
    elif ds_key == "landsat_5_7":
        col5 = ee.ImageCollection("LANDSAT/LT05/C02/T1_L2").filterBounds(ee_geom).filterDate(start_date, end_date)
        col7 = ee.ImageCollection("LANDSAT/LE07/C02/T1_L2").filterBounds(ee_geom).filterDate(start_date, end_date)
        col = col5.merge(col7)
        sensor = "Landsat 5 & 7"
        res = "30m"
    else:
        col = ee.ImageCollection("LANDSAT/LC08/C02/T1_L2").filterBounds(ee_geom).filterDate(start_date, end_date)
        sensor = "Landsat 8"
        res = "30m"

    count = col.size().getInfo()
    if count == 0:
        wide_count = col.filterDate(f"{year-1}-12-01", f"{year}-05-15").size().getInfo()
        if wide_count > 0:
            count = wide_count

    available = count > 0
    return {
        "available": available,
        "scenes_count": count,
        "year": year,
        "dataset": ds_key,
        "sensor": sensor,
        "resolution": res,
        "message": (
            f"{count} valid scenes available for {sensor} ({res}) in {year}."
            if available
            else f"No valid imagery found for {sensor} in study year {year}. Please select another satellite dataset or study year."
        ),
    }


def get_satellite_composite_for_geometry(geometry, year: int, dataset: str = "auto"):
    """
    Generates a cloud-masked median satellite composite clipped to the user's boundary geometry.
    Supports Landsat (5, 7, 8, 9) and Sentinel-2 (2A, 2B, or combined 2A & 2B) depending on dataset and year.
    Returns composite image, scenes count, sensor description, native resolution, and temporal metadata.
    """
    initialize_gee()
    ee_geom = ee.Geometry(geometry)
    start_date, end_date = get_temporal_window(year)

    ds_key = (dataset or "auto").lower().strip()

    # Resolve "auto" based on target year
    if ds_key == "auto":
        if year >= 2022:
            ds_key = "landsat_8_9"
        elif year >= 2013:
            ds_key = "landsat_8"
        else:
            ds_key = "landsat_5_7"

    if ds_key == "landsat_10":
        raise ValueError(
            "Landsat 10 is not currently an operational dataset. "
            "Architecture hook is ready for future mission deployment."
        )

    if ds_key in ["sentinel_2", "sentinel_2a", "sentinel_2b"]:
        if year < 2015:
            raise ValueError(f"Sentinel-2 data is only available from 2015 onward (requested year: {year}).")
        if ds_key == "sentinel_2b" and year < 2017:
            raise ValueError(f"Sentinel-2B was launched in 2017; not available for year {year}.")

        s2_base = ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED").filterBounds(ee_geom)
        if ds_key == "sentinel_2a":
            s2_base = s2_base.filter(ee.Filter.eq("SPACECRAFT_NAME", "Sentinel-2A"))
            sensor_name = "Sentinel-2A MSI"
            res_desc = "10 m (Optical & NIR) / 20 m (SWIR)"
        elif ds_key == "sentinel_2b":
            s2_base = s2_base.filter(ee.Filter.eq("SPACECRAFT_NAME", "Sentinel-2B"))
            sensor_name = "Sentinel-2B MSI"
            res_desc = "10 m (Optical & NIR) / 20 m (SWIR)"
        else:
            sensor_name = "Sentinel-2A & Sentinel-2B MSI Harmonized"
            res_desc = "10 m (Optical & NIR) / 20 m (SWIR)"

        col = s2_base.filterDate(start_date, end_date).map(mask_s2_sr).map(scale_s2_sr)
        bands = ["B2", "B3", "B4", "B8", "B11", "B12"]
        names = ["blue", "green", "red", "nir", "swir1", "swir2"]
        native_res = "10m"

    elif ds_key == "landsat_9":
        col = (
            ee.ImageCollection("LANDSAT/LC09/C02/T1_L2")
            .filterBounds(ee_geom)
            .filterDate(start_date, end_date)
            .map(mask_landsat_sr)
            .map(scale_landsat_sr)
        )
        bands = ["SR_B2", "SR_B3", "SR_B4", "SR_B5", "SR_B6", "SR_B7"]
        names = ["blue", "green", "red", "nir", "swir1", "swir2"]
        sensor_name = "Landsat 9 OLI-2"
        res_desc = "30 m (Optical & SWIR)"
        native_res = "30m"

    elif ds_key == "landsat_8":
        col = (
            ee.ImageCollection("LANDSAT/LC08/C02/T1_L2")
            .filterBounds(ee_geom)
            .filterDate(start_date, end_date)
            .map(mask_landsat_sr)
            .map(scale_landsat_sr)
        )
        bands = ["SR_B2", "SR_B3", "SR_B4", "SR_B5", "SR_B6", "SR_B7"]
        names = ["blue", "green", "red", "nir", "swir1", "swir2"]
        sensor_name = "Landsat 8 OLI"
        res_desc = "30 m (Optical & SWIR)"
        native_res = "30m"

    elif ds_key == "landsat_8_9":
        col8 = (
            ee.ImageCollection("LANDSAT/LC08/C02/T1_L2")
            .filterBounds(ee_geom)
            .filterDate(start_date, end_date)
            .map(mask_landsat_sr)
            .map(scale_landsat_sr)
        )
        col9 = (
            ee.ImageCollection("LANDSAT/LC09/C02/T1_L2")
            .filterBounds(ee_geom)
            .filterDate(start_date, end_date)
            .map(mask_landsat_sr)
            .map(scale_landsat_sr)
        )
        col = col8.merge(col9)
        bands = ["SR_B2", "SR_B3", "SR_B4", "SR_B5", "SR_B6", "SR_B7"]
        names = ["blue", "green", "red", "nir", "swir1", "swir2"]
        sensor_name = "Landsat 8 OLI & Landsat 9 OLI-2"
        res_desc = "30 m (Optical & SWIR)"
        native_res = "30m"

    elif ds_key == "landsat_5_7":
        col5 = (
            ee.ImageCollection("LANDSAT/LT05/C02/T1_L2")
            .filterBounds(ee_geom)
            .filterDate(start_date, end_date)
            .map(mask_landsat_sr)
            .map(scale_landsat_sr)
        )
        col7 = (
            ee.ImageCollection("LANDSAT/LE07/C02/T1_L2")
            .filterBounds(ee_geom)
            .filterDate(start_date, end_date)
            .map(mask_landsat_sr)
            .map(scale_landsat_sr)
        )
        col = col5.merge(col7)
        bands = ["SR_B1", "SR_B2", "SR_B3", "SR_B4", "SR_B5", "SR_B7"]
        names = ["blue", "green", "red", "nir", "swir1", "swir2"]
        sensor_name = "Landsat 5 TM / Landsat 7 ETM+"
        res_desc = "30 m (Optical & SWIR)"
        native_res = "30m"

    else:
        return get_satellite_composite_for_geometry(geometry, year, dataset="auto")

    # Count scenes
    scenes_count = col.size().getInfo()
    window_used = [start_date, end_date]

    if scenes_count == 0:
        # Widen search to full dry season (Dec to May) if specific window had no scenes
        wide_start = f"{year-1}-12-01"
        wide_end = f"{year}-05-15"
        if ds_key in ["sentinel_2", "sentinel_2a", "sentinel_2b"]:
            wide_col = s2_base.filterDate(wide_start, wide_end).map(mask_s2_sr).map(scale_s2_sr)
        elif ds_key == "landsat_8_9":
            col8_wide = ee.ImageCollection("LANDSAT/LC08/C02/T1_L2").filterBounds(ee_geom).filterDate(wide_start, wide_end).map(mask_landsat_sr).map(scale_landsat_sr)
            col9_wide = ee.ImageCollection("LANDSAT/LC09/C02/T1_L2").filterBounds(ee_geom).filterDate(wide_start, wide_end).map(mask_landsat_sr).map(scale_landsat_sr)
            wide_col = col8_wide.merge(col9_wide)
        elif ds_key == "landsat_5_7":
            col5_wide = ee.ImageCollection("LANDSAT/LT05/C02/T1_L2").filterBounds(ee_geom).filterDate(wide_start, wide_end).map(mask_landsat_sr).map(scale_landsat_sr)
            col7_wide = ee.ImageCollection("LANDSAT/LE07/C02/T1_L2").filterBounds(ee_geom).filterDate(wide_start, wide_end).map(mask_landsat_sr).map(scale_landsat_sr)
            wide_col = col5_wide.merge(col7_wide)
        else:
            single_col_name = "LANDSAT/LC09/C02/T1_L2" if ds_key == "landsat_9" else "LANDSAT/LC08/C02/T1_L2"
            wide_col = ee.ImageCollection(single_col_name).filterBounds(ee_geom).filterDate(wide_start, wide_end).map(mask_landsat_sr).map(scale_landsat_sr)

        wide_count = wide_col.size().getInfo()
        if wide_count > 0:
            col = wide_col
            scenes_count = wide_count
            window_used = [wide_start, wide_end]

    median_img = col.median().select(bands, names).clip(ee_geom)
    return {
        "image": median_img,
        "scenes_count": scenes_count,
        "sensor": sensor_name,
        "dataset": ds_key,
        "resolution_desc": res_desc,
        "native_resolution": native_res,
        "analysis_resolution": 30,
        "temporal_window": window_used,
        "geometry": ee_geom,
        "is_available": scenes_count > 0,
    }


def get_landsat_composite_for_geometry(geometry, year: int, dataset: str = "auto"):
    """
    Backward-compatible wrapper forwarding to get_satellite_composite_for_geometry.
    """
    return get_satellite_composite_for_geometry(geometry, year, dataset=dataset)


def compute_spectral_indices(composite_img):
    """
    Calculates 6 standard spectral indices: NDVI, NDBI, MNDWI, BSI, UI, SAVI.
    """
    blue = composite_img.select("blue")
    green = composite_img.select("green")
    red = composite_img.select("red")
    nir = composite_img.select("nir")
    swir1 = composite_img.select("swir1")
    swir2 = composite_img.select("swir2")

    # 1. NDVI: (NIR - Red) / (NIR + Red)
    ndvi = nir.subtract(red).divide(nir.add(red).max(0.0001)).rename("ndvi")

    # 2. NDBI: (SWIR1 - NIR) / (SWIR1 + NIR)
    ndbi = swir1.subtract(nir).divide(swir1.add(nir).max(0.0001)).rename("ndbi")

    # 3. MNDWI: (Green - SWIR1) / (Green + SWIR1)
    mndwi = green.subtract(swir1).divide(green.add(swir1).max(0.0001)).rename("mndwi")

    # 4. BSI: ((SWIR1 + Red) - (NIR + Blue)) / ((SWIR1 + Red) + (NIR + Blue))
    bsi_num = swir1.add(red).subtract(nir.add(blue))
    bsi_den = swir1.add(red).add(nir.add(blue)).max(0.0001)
    bsi = bsi_num.divide(bsi_den).rename("bsi")

    # 5. UI: (SWIR2 - NIR) / (SWIR2 + NIR)
    ui = swir2.subtract(nir).divide(swir2.add(nir).max(0.0001)).rename("ui")

    # 6. SAVI: ((NIR - Red) * 1.5) / (NIR + Red + 0.5)
    savi = nir.subtract(red).multiply(1.5).divide(nir.add(red).add(0.5)).rename("savi")

    return composite_img.addBands([ndvi, ndbi, mndwi, bsi, ui, savi])


def build_full_feature_stack(composite_with_indices, geometry):
    """
    Adds SRTM 30 m digital elevation and slope to complete the 14-band predictor stack.
    """
    srtm = ee.Image("USGS/SRTMGL1_003").clip(geometry)
    elevation = srtm.select("elevation").rename("elevation")
    slope = ee.Terrain.slope(elevation).rename("slope")

    return composite_with_indices.addBands([elevation, slope])


def get_layer_map_tile_url(feature_stack, layer_type: str):
    """
    Generates Earth Engine tile fetcher URLs for TCC, FCC, NDVI, NDBI, and MNDWI.
    """
    if layer_type in ["tcc", "composite", "true_color"]:
        vis = {
            "bands": ["red", "green", "blue"],
            "min": 0.0,
            "max": 0.3,
            "gamma": 1.2,
        }
    elif layer_type in ["fcc", "false_color"]:
        vis = {
            "bands": ["nir", "red", "green"],
            "min": 0.0,
            "max": 0.4,
            "gamma": 1.2,
        }
    elif layer_type == "ndvi":
        vis = {
            "bands": ["ndvi"],
            "min": -0.1,
            "max": 0.7,
            "palette": ["#d73027", "#fee08b", "#a6d96a", "#006837"],
        }
    elif layer_type == "ndbi":
        vis = {
            "bands": ["ndbi"],
            "min": -0.4,
            "max": 0.25,
            "palette": ["#2b83ba", "#abdda4", "#ffffbf", "#d7191c"],
        }
    elif layer_type == "mndwi":
        vis = {
            "bands": ["mndwi"],
            "min": -0.5,
            "max": 0.2,
            "palette": ["#8c510a", "#f6e8c3", "#c7eae5", "#01665e"],
        }
    else:
        vis = {
            "bands": ["red", "green", "blue"],
            "min": 0.0,
            "max": 0.3,
        }

    map_id_dict = feature_stack.getMapId(vis)
    return {
        "layer_type": layer_type,
        "tile_url": map_id_dict["tile_fetcher"].url_format,
        "vis_params": vis,
    }
