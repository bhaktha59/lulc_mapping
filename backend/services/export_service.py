"""
Export Service for Tamil Nadu LULC Mapping.
Handles GeoTIFF, High-Resolution PNG/JPEG map exports, CSV statistics, and GeoJSON vectors.
"""

import os
import json
import csv
import io
import re
import urllib.request
import zipfile
import ee
from config import LULC_CLASSES, LULC_PALETTE
from services.gee_pipeline import (
    initialize_gee,
    get_landsat_composite_for_geometry,
    compute_spectral_indices,
    build_full_feature_stack,
)


def sanitize_filename(name: str) -> str:
    """Sanitizes project name for clean, valid file system and HTTP header filenames."""
    if not name:
        return "LULC"
    clean = re.sub(r'[^\w\-_.]', '_', str(name).strip())
    clean = re.sub(r'_+', '_', clean)
    return clean or "LULC"


def generate_area_stats_csv(area_stats, project_name, year):
    """
    Generates CSV string with class-wise area quantification.
    """
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([f"# Project: {project_name} - Year: {year}"])
    writer.writerow(["Class_ID", "Class_Name", "Pixel_Count", "Area_Hectares", "Area_SqKm", "Percentage", "Color_Hex", "Description"])
    for row in area_stats:
        writer.writerow([
            row["class_id"],
            row["name"],
            row.get("pixel_count", 0),
            row["area_ha"],
            row["area_sqkm"],
            row["percentage"],
            row["color"],
            row.get("description", ""),
        ])
    return output.getvalue()


def generate_accuracy_csv(accuracy_info, project_name, year, project_classes=None):
    """
    Generates CSV string with confusion matrix, PA, UA, OA, and Kappa.
    Supports dynamic classes.
    """
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([f"# Accuracy Assessment Report - Project: {project_name} - Year: {year}"])
    if accuracy_info.get("algorithm_name") or accuracy_info.get("algorithm"):
        writer.writerow([f"Classification Algorithm: {accuracy_info.get('algorithm_name', accuracy_info.get('algorithm'))}"])
    writer.writerow([f"Overall Accuracy (%): {accuracy_info.get('overall_accuracy', 0)}"])
    writer.writerow([f"Cohen's Kappa Coefficient: {accuracy_info.get('kappa_coefficient', 0)}"])
    writer.writerow([f"Validation Holdout Sample Count: {accuracy_info.get('validation_sample_size', 0)}"])
    writer.writerow([])

    # Per class PA / UA table
    writer.writerow(["Class_ID", "Class_Name", "Producer_Accuracy_PA_pct", "User_Accuracy_UA_pct"])
    per_class = accuracy_info.get("per_class", {})
    sorted_cids = sorted(per_class.keys(), key=lambda x: int(x))

    for cid_str in sorted_cids:
        cdata = per_class[cid_str]
        cid = int(cid_str)
        writer.writerow([
            cid,
            cdata.get("name", f"Class {cid}"),
            cdata.get("producers_accuracy", 0.0),
            cdata.get("users_accuracy", 0.0),
        ])

    writer.writerow([])
    writer.writerow(["# Confusion Matrix (Rows = Ground Truth Reference, Columns = RF Predicted)"])
    header = ["Ref_Class"] + [f"Pred_{per_class[c]['name']}" for c in sorted_cids]
    writer.writerow(header)
    matrix = accuracy_info.get("confusion_matrix", [])
    for cid_str in sorted_cids:
        cid = int(cid_str)
        cname = per_class[cid_str]["name"]
        if cid < len(matrix):
            # Extract only the columns corresponding to sorted_cids
            row_vals = [
                matrix[cid][int(c_col)] if (isinstance(matrix[cid], list) and int(c_col) < len(matrix[cid])) else 0
                for c_col in sorted_cids
            ]
        elif (cid - 1) < len(matrix):
            idx = cid - 1
            row_vals = matrix[idx][:len(sorted_cids)] if isinstance(matrix[idx], list) else [0] * len(sorted_cids)
        else:
            row_vals = [0] * len(sorted_cids)
        writer.writerow([cname] + list(row_vals))

    return output.getvalue()


def _get_bbox_coordinates(ee_geom):
    """Safely extracts simple 5-vertex rectangular bounding box coordinates for fast EE exports."""
    try:
        return ee_geom.bounds().getInfo()["coordinates"]
    except Exception:
        return None


def generate_and_cache_geotiff(proj_dir, geometry, year: int, project_name: str, training_points, project_classes=None, algorithm="rf", satellite_dataset="auto"):
    """
    Generates a high-quality GeoTIFF raster from Earth Engine using selected algorithm (RF or SVM),
    caches it locally in proj_dir, and returns the absolute file path for direct FileResponse download.
    """
    safe_name = sanitize_filename(project_name)
    algo_clean = (algorithm or "rf").lower()
    algo_suffix = f"_{algo_clean}" if algo_clean != "rf" else ""
    cached_path = os.path.join(proj_dir, f"{safe_name}_LULC_{year}{algo_suffix}.tif")

    # If already generated and valid (> 1KB), return immediately
    if os.path.exists(cached_path) and os.path.getsize(cached_path) > 1000:
        return cached_path

    # Also check base filename if standard RF
    base_path = os.path.join(proj_dir, f"{safe_name}_LULC_{year}.tif")
    if algo_clean == "rf" and os.path.exists(base_path) and os.path.getsize(base_path) > 1000:
        return base_path

    initialize_gee()
    ee_geom = ee.Geometry(geometry)
    from services.classifier_service import FEATURE_NAMES, build_gee_classifier

    landsat_info = get_landsat_composite_for_geometry(geometry, year, dataset=satellite_dataset)
    composite_img = landsat_info["image"]
    with_indices = compute_spectral_indices(composite_img)
    feature_stack = build_full_feature_stack(with_indices, ee_geom)

    train_ee_features = [
        ee.Feature(ee.Geometry.Point([p["lon"], p["lat"]]), {"class_id": int(p["class_id"])})
        for p in training_points
    ]
    train_fc = ee.FeatureCollection(train_ee_features)
    train_samples = feature_stack.sampleRegions(
        collection=train_fc,
        properties=["class_id"],
        scale=30,
        tileScale=4
    )

    base_classifier, algo_code, _ = build_gee_classifier(algorithm)
    trained_classifier = base_classifier.train(
        features=train_samples,
        classProperty="class_id",
        inputProperties=FEATURE_NAMES
    )

    classified = feature_stack.select(FEATURE_NAMES).classify(trained_classifier).toByte()

    bbox = _get_bbox_coordinates(ee_geom)
    if not bbox:
        bbox = geometry["coordinates"] if geometry["type"] == "Polygon" else geometry["coordinates"][0]

    # Attempt download URL with 1024 dimensions, falling back to 512 if memory limits occur
    download_url = None
    for dim in [1024, 512]:
        try:
            download_url = classified.getDownloadURL({
                "name": f"{safe_name}_LULC_{year}{algo_suffix}",
                "dimensions": dim,
                "crs": "EPSG:4326",
                "region": bbox,
                "format": "GEO_TIFF",
            })
            if download_url:
                break
        except Exception as e:
            print(f"GeoTIFF getDownloadURL attempt at dim {dim} failed: {e}")

    if not download_url:
        raise RuntimeError("Earth Engine was unable to construct a GeoTIFF download URL.")

    # Fetch binary bytes from Earth Engine and save to disk
    req = urllib.request.Request(
        download_url,
        headers={"User-Agent": "TN-LULC-Portal/1.0"}
    )
    with urllib.request.urlopen(req, timeout=60) as response:
        tif_bytes = response.read()

    if len(tif_bytes) < 100:
        raise RuntimeError("Received invalid or truncated GeoTIFF payload from Earth Engine.")

    with open(cached_path, "wb") as f:
        f.write(tif_bytes)

    return cached_path


def generate_and_cache_map_image(proj_dir, geometry, year: int, project_name: str, training_points, project_classes=None, img_format="png", algorithm="rf", satellite_dataset="auto"):
    """
    Renders high-resolution map image thumbnail (PNG or JPEG) with project palette using selected algorithm (RF or SVM),
    caches it locally in proj_dir, and returns the absolute file path for direct FileResponse download.
    """
    safe_name = sanitize_filename(project_name)
    ext = "jpg" if img_format.lower() in ["jpg", "jpeg"] else "png"
    algo_clean = (algorithm or "rf").lower()
    algo_suffix = f"_{algo_clean}" if algo_clean != "rf" else ""
    cached_path = os.path.join(proj_dir, f"{safe_name}_LULC_{year}{algo_suffix}.{ext}")

    # If already generated and valid (> 1KB), return immediately
    if os.path.exists(cached_path) and os.path.getsize(cached_path) > 1000:
        return cached_path

    # Also check base file if RF
    base_path = os.path.join(proj_dir, f"{safe_name}_LULC_{year}.{ext}")
    if algo_clean == "rf" and os.path.exists(base_path) and os.path.getsize(base_path) > 1000:
        return base_path

    initialize_gee()
    ee_geom = ee.Geometry(geometry)
    from services.classifier_service import FEATURE_NAMES, build_gee_classifier

    classes_dict = project_classes or LULC_CLASSES
    class_ids = sorted([int(k) for k in classes_dict.keys()])
    min_cid = min(class_ids) if class_ids else 1
    max_cid = max(class_ids) if class_ids else 8

    palette_map = {}
    for cid_raw, cinfo in classes_dict.items():
        palette_map[int(cid_raw)] = cinfo.get("color", "#888888")
    ee_palette = [palette_map.get(i, "#000000") for i in range(min_cid, max_cid + 1)]

    landsat_info = get_landsat_composite_for_geometry(geometry, year, dataset=satellite_dataset)
    composite_img = landsat_info["image"]
    with_indices = compute_spectral_indices(composite_img)
    feature_stack = build_full_feature_stack(with_indices, ee_geom)

    train_ee_features = [
        ee.Feature(ee.Geometry.Point([p["lon"], p["lat"]]), {"class_id": int(p["class_id"])})
        for p in training_points
    ]
    train_fc = ee.FeatureCollection(train_ee_features)
    train_samples = feature_stack.sampleRegions(
        collection=train_fc,
        properties=["class_id"],
        scale=30,
        tileScale=4
    )

    base_classifier, algo_code, _ = build_gee_classifier(algorithm)
    trained_classifier = base_classifier.train(
        features=train_samples,
        classProperty="class_id",
        inputProperties=FEATURE_NAMES
    )

    classified = feature_stack.select(FEATURE_NAMES).classify(trained_classifier)
    visualized = classified.visualize(min=min_cid, max=max_cid, palette=ee_palette)

    bbox = _get_bbox_coordinates(ee_geom)
    if not bbox:
        bbox = geometry["coordinates"] if geometry["type"] == "Polygon" else geometry["coordinates"][0]

    thumb_url = None
    for dim in [1024, 768]:
        try:
            thumb_url = visualized.getThumbURL({
                "dimensions": dim,
                "region": bbox,
                "format": ext,
            })
            if thumb_url:
                break
        except Exception as e:
            print(f"Map image getThumbURL attempt at dim {dim} failed: {e}")

    if not thumb_url:
        raise RuntimeError("Earth Engine was unable to construct a map thumbnail URL.")

    req = urllib.request.Request(
        thumb_url,
        headers={"User-Agent": "TN-LULC-Portal/1.0"}
    )
    with urllib.request.urlopen(req, timeout=45) as response:
        img_bytes = response.read()

    if len(img_bytes) < 100:
        raise RuntimeError("Received invalid or truncated image payload from Earth Engine.")

    with open(cached_path, "wb") as f:
        f.write(img_bytes)

    return cached_path


def get_geotiff_download_url(geometry, year: int, project_name: str, training_points, project_classes=None, satellite_dataset="auto"):
    """Legacy helper returning Earth Engine URL."""
    initialize_gee()
    ee_geom = ee.Geometry(geometry)
    from services.classifier_service import FEATURE_NAMES

    landsat_info = get_landsat_composite_for_geometry(geometry, year, dataset=satellite_dataset)
    composite_img = landsat_info["image"]
    with_indices = compute_spectral_indices(composite_img)
    feature_stack = build_full_feature_stack(with_indices, ee_geom)

    train_ee_features = [
        ee.Feature(ee.Geometry.Point([p["lon"], p["lat"]]), {"class_id": int(p["class_id"])})
        for p in training_points
    ]
    train_fc = ee.FeatureCollection(train_ee_features)
    train_samples = feature_stack.sampleRegions(
        collection=train_fc,
        properties=["class_id"],
        scale=30,
        tileScale=4
    )

    rf_classifier = ee.Classifier.smileRandomForest(
        numberOfTrees=50,
        minLeafPopulation=2,
        bagFraction=0.8,
        seed=42
    ).train(
        features=train_samples,
        classProperty="class_id",
        inputProperties=FEATURE_NAMES
    )

    classified = feature_stack.select(FEATURE_NAMES).classify(rf_classifier).toByte()
    bbox = _get_bbox_coordinates(ee_geom) or (geometry["coordinates"] if geometry["type"] == "Polygon" else geometry["coordinates"][0])

    return classified.getDownloadURL({
        "name": f"{sanitize_filename(project_name)}_LULC_{year}",
        "dimensions": 1024,
        "crs": "EPSG:4326",
        "region": bbox,
        "format": "GEO_TIFF",
    })


def get_map_image_render_url(geometry, year: int, training_points, project_classes=None, img_format="png", dimensions=1024, satellite_dataset="auto"):
    """Legacy helper returning thumbnail URL."""
    initialize_gee()
    ee_geom = ee.Geometry(geometry)
    from services.classifier_service import FEATURE_NAMES

    classes_dict = project_classes or LULC_CLASSES
    class_ids = sorted([int(k) for k in classes_dict.keys()])
    min_cid = min(class_ids) if class_ids else 1
    max_cid = max(class_ids) if class_ids else 8

    palette_map = {}
    for cid_raw, cinfo in classes_dict.items():
        palette_map[int(cid_raw)] = cinfo.get("color", "#888888")
    ee_palette = [palette_map.get(i, "#000000") for i in range(min_cid, max_cid + 1)]

    landsat_info = get_landsat_composite_for_geometry(geometry, year, dataset=satellite_dataset)
    composite_img = landsat_info["image"]
    with_indices = compute_spectral_indices(composite_img)
    feature_stack = build_full_feature_stack(with_indices, ee_geom)

    train_ee_features = [
        ee.Feature(ee.Geometry.Point([p["lon"], p["lat"]]), {"class_id": int(p["class_id"])})
        for p in training_points
    ]
    train_fc = ee.FeatureCollection(train_ee_features)
    train_samples = feature_stack.sampleRegions(
        collection=train_fc,
        properties=["class_id"],
        scale=30,
        tileScale=4
    )

    rf_classifier = ee.Classifier.smileRandomForest(
        numberOfTrees=50,
        minLeafPopulation=2,
        bagFraction=0.8,
        seed=42
    ).train(
        features=train_samples,
        classProperty="class_id",
        inputProperties=FEATURE_NAMES
    )

    classified = feature_stack.select(FEATURE_NAMES).classify(rf_classifier)
    visualized = classified.visualize(min=min_cid, max=max_cid, palette=ee_palette)
    bbox = _get_bbox_coordinates(ee_geom) or (geometry["coordinates"] if geometry["type"] == "Polygon" else geometry["coordinates"][0])

    return visualized.getThumbURL({
        "dimensions": dimensions,
        "region": bbox,
        "format": img_format,
    })


def export_points_geojson(points, classes=None, split_name="Sample"):
    """Converts internal point dictionaries to standard GeoJSON FeatureCollection."""
    features = []
    classes_dict = classes or LULC_CLASSES
    for p in points:
        cid = int(p.get("class_id", 1))
        cname = (classes_dict.get(str(cid)) or {}).get("name", f"Class {cid}")
        features.append({
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [round(float(p["lon"]), 6), round(float(p["lat"]), 6)],
            },
            "properties": {
                "class_id": cid,
                "class_name": cname,
                "split": p.get("user_split") or split_name,
            }
        })
    return {
        "type": "FeatureCollection",
        "name": f"{split_name}_points",
        "crs": {"type": "name", "properties": {"name": "urn:ogc:def:crs:OGC:1.3:CRS84"}},
        "features": features,
    }


def export_points_csv(points, classes=None, split_name="Sample"):
    """Converts internal point dictionaries to a downloadable CSV string."""
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["lon", "lat", "class_id", "class_name", "split"])
    classes_dict = classes or LULC_CLASSES
    for p in points:
        cid = int(p.get("class_id", 1))
        cname = (classes_dict.get(str(cid)) or {}).get("name", f"Class {cid}")
        writer.writerow([
            round(float(p["lon"]), 6),
            round(float(p["lat"]), 6),
            cid,
            cname,
            p.get("user_split") or split_name,
        ])
    return output.getvalue()


def create_complete_export_bundle(project_dir, project_name, target_year, classes=None):
    """
    Bundles all project artifacts into a complete downloadable ZIP:
    - Study Area Boundary (study_area_boundary.geojson)
    - Classified 30m GeoTIFF (if cached or available)
    - Classified Map Image (if cached or available)
    - Training Points (training_points.geojson & .csv)
    - Validation Points (validation_points.geojson & .csv)
    - Area Statistics CSV
    - Accuracy Report CSV
    - QGIS Raster Symbology (lulc_raster_symbology.qml)
    - QGIS Vector Symbology (lulc_symbology.qml)
    - Project Metadata (project_metadata.json)
    """
    safe_name = sanitize_filename(project_name)
    bundle_name = f"{safe_name}_Complete_LULC_Package_{target_year}.zip"
    bundle_path = os.path.join(project_dir, bundle_name)

    b_path = os.path.join(project_dir, "boundary.geojson")
    train_path = os.path.join(project_dir, "training_points.json")
    val_path = os.path.join(project_dir, "validation_points.json")
    res_path = os.path.join(project_dir, f"classification_{target_year}.json")

    res_data = None
    if os.path.exists(res_path):
        try:
            with open(res_path, "r", encoding="utf-8") as f:
                res_data = json.load(f)
        except Exception:
            pass

    with zipfile.ZipFile(bundle_path, "w", zipfile.ZIP_DEFLATED) as zf:
        # 1. Boundary GeoJSON
        if os.path.exists(b_path):
            zf.write(b_path, arcname="study_area_boundary.geojson")

        # 2. Area Statistics CSV & Accuracy Assessment CSV
        if res_data:
            if "area_statistics" in res_data:
                area_csv = generate_area_stats_csv(res_data["area_statistics"], project_name, target_year)
                zf.writestr(f"{safe_name}_LULC_Area_Stats_{target_year}.csv", area_csv)
            if "accuracy" in res_data:
                acc_csv = generate_accuracy_csv(res_data["accuracy"], project_name, target_year, project_classes=classes)
                zf.writestr(f"{safe_name}_Accuracy_Report_{target_year}.csv", acc_csv)

        # 3. Training Points (GeoJSON and CSV)
        if os.path.exists(train_path):
            try:
                with open(train_path, "r", encoding="utf-8") as f:
                    t_pts = json.load(f)
                t_fc = export_points_geojson(t_pts, classes=classes, split_name="Training")
                zf.writestr("training_points.geojson", json.dumps(t_fc, indent=2))
                t_csv = export_points_csv(t_pts, classes=classes, split_name="Training")
                zf.writestr("training_points.csv", t_csv)
            except Exception as e:
                print("Error bundling training points:", e)

        # 4. Validation Points (GeoJSON and CSV)
        if os.path.exists(val_path):
            try:
                with open(val_path, "r", encoding="utf-8") as f:
                    v_pts = json.load(f)
                v_fc = export_points_geojson(v_pts, classes=classes, split_name="Validation")
                zf.writestr("validation_points.geojson", json.dumps(v_fc, indent=2))
                v_csv = export_points_csv(v_pts, classes=classes, split_name="Validation")
                zf.writestr("validation_points.csv", v_csv)
            except Exception as e:
                print("Error bundling validation points:", e)

        # 5. QGIS Symbology files
        qpack = os.path.join(project_dir, "qgis_package")
        if os.path.exists(qpack):
            for qf in ["lulc_symbology.qml", "lulc_raster_symbology.qml", "grid_symbology.qml"]:
                qp = os.path.join(qpack, qf)
                if os.path.exists(qp):
                    zf.write(qp, arcname=qf)

        # 6. Cached GeoTIFF if exists
        cached_tif = os.path.join(project_dir, f"{safe_name}_LULC_{target_year}.tif")
        if os.path.exists(cached_tif):
            zf.write(cached_tif, arcname=f"{safe_name}_LULC_{target_year}.tif")

        # 7. Cached Map Image (PNG / JPG) if exists
        for ext in ["png", "jpg"]:
            cached_img = os.path.join(project_dir, f"{safe_name}_LULC_{target_year}.{ext}")
            if os.path.exists(cached_img):
                zf.write(cached_img, arcname=f"{safe_name}_LULC_{target_year}.{ext}")
                break

        # 8. Project Metadata
        meta_path = os.path.join(project_dir, "project_metadata.json")
        if os.path.exists(meta_path):
            zf.write(meta_path, arcname="project_metadata.json")

    return bundle_path

