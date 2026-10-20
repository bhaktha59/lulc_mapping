"""
FastAPI Backend Application for LULC Mapping Portal.
Runs on Port 8001 (isolated from original Pappireddipatti project on 8000).
Implements the full 7-step automated workflow without requiring python-multipart.
1. Project Creation
2. Shapefile Upload & Boundary Extraction
3. Satellite Band Preparation & Indices Compositing
4. Ground-Truth Reference Point Digitization & QGIS Starter Kit
5. Supervised Machine Learning Classification (Random Forest & Support Vector Machine)
6. Independent Accuracy Assessment (OA, Kappa, PA, UA, Confusion Matrix)
7. Final Map Display, Area Statistics & High-Quality GIS Exports
"""

import os
import sys
import json
import uuid
import shutil
import datetime
from typing import Optional
from contextlib import asynccontextmanager
from pydantic import BaseModel
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response, JSONResponse

# Add backend directory to sys.path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config import (
    PROJECTS_DIR,
    LULC_CLASSES,
    LULC_PALETTE,
    SUPPORTED_YEARS,
    STUDY_YEAR_DATASET_OPTIONS,
    SATELLITE_DATASETS,
    get_default_classes,
)
from services.shapefile_service import process_shapefile_zip
from services.gee_pipeline import (
    initialize_gee,
    get_satellite_composite_for_geometry,
    get_landsat_composite_for_geometry,
    check_satellite_availability,
    compute_spectral_indices,
    build_full_feature_stack,
    get_layer_map_tile_url,
)
from services.sampling_service import (
    create_qgis_starter_package,
    parse_and_split_reference_points,
)
from services.classifier_service import (
    run_classification_workflow,
    run_random_forest_workflow,
    run_svm_workflow,
    extract_rf_feature_importance,
)
from services.export_service import (
    generate_area_stats_csv,
    generate_accuracy_csv,
    get_geotiff_download_url,
    get_map_image_render_url,
    generate_and_cache_geotiff,
    generate_and_cache_map_image,
    export_points_geojson,
    export_points_csv,
    create_complete_export_bundle,
    sanitize_filename,
)


def extract_file_bytes(body: bytes) -> bytes:
    """
    Extracts raw file bytes from either a raw binary stream or multipart/form-data.
    Zero external dependencies required (no python-multipart needed).
    """
    if not body:
        return b""
    if body.startswith(b"PK\x03\x04"):
        return body
    pk_start = body.find(b"PK\x03\x04")
    if pk_start != -1:
        eocd_pos = body.rfind(b"PK\x05\x06")
        if eocd_pos != -1 and eocd_pos >= pk_start:
            if len(body) >= eocd_pos + 22:
                comment_len = int.from_bytes(body[eocd_pos + 20 : eocd_pos + 22], "little")
                end_pos = eocd_pos + 22 + comment_len
                if end_pos <= len(body):
                    return body[pk_start:end_pos]
            return body[pk_start:]
        return body[pk_start:]
    if body.startswith(b"--"):
        header_end = body.find(b"\r\n\r\n")
        if header_end != -1:
            content = body[header_end + 4 :]
            last_boundary = content.rfind(b"\r\n--")
            if last_boundary != -1:
                return content[:last_boundary]
            return content
        header_end_lf = body.find(b"\n\n")
        if header_end_lf != -1:
            content = body[header_end_lf + 2 :]
            last_boundary = content.rfind(b"\n--")
            if last_boundary != -1:
                return content[:last_boundary]
            return content
    return body



@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Initializing Google Earth Engine for LULC Mapping Portal...")
    success = initialize_gee()
    if success:
        print("Google Earth Engine successfully authenticated & initialized.")
    else:
        print("Warning: Earth Engine initialization returned False. Check credentials.")
    yield


app = FastAPI(
    title="LULC Mapping API",
    description="Standalone Enterprise GIS & Remote Sensing Pipeline for Study Areas",
    version="1.0.0",
    lifespan=lifespan,
)

# Enable CORS for local Vite dev server and any web origin
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Helper to get project metadata
def get_project_metadata_path(project_id: str):
    return os.path.join(PROJECTS_DIR, project_id, "project_metadata.json")


def load_project_metadata(project_id: str):
    meta_path = get_project_metadata_path(project_id)
    if not os.path.exists(meta_path):
        raise HTTPException(status_code=404, detail=f"Project '{project_id}' not found.")
    with open(meta_path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_project_metadata(project_id: str, meta: dict):
    proj_dir = os.path.join(PROJECTS_DIR, project_id)
    os.makedirs(proj_dir, exist_ok=True)
    meta_path = get_project_metadata_path(project_id)
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2)


# Pydantic Request Models
class CreateProjectRequest(BaseModel):
    name: str
    district: str = "General"
    description: Optional[str] = ""
    target_year: int = 2025
    satellite_dataset: Optional[str] = "landsat_8_9"


class ClassifyRequest(BaseModel):
    year: Optional[int] = None
    algorithm: Optional[str] = "rf"
    dataset: Optional[str] = None


class UpdateClassesRequest(BaseModel):
    classes: dict


# ==========================================
# 0. GENERAL & METADATA ENDPOINTS
# ==========================================

@app.get("/api/health")
def health_check():
    """Health check endpoint to verify backend server connectivity."""
    return {"status": "ok", "message": "LULC Mapping Backend is running on port 8001."}


@app.get("/api/classes")
def get_lulc_classes():
    """Returns standard 8-class classification schema."""
    return {
        "classes": LULC_CLASSES,
        "palette": LULC_PALETTE,
        "supported_years": SUPPORTED_YEARS,
    }


@app.get("/api/satellite-options")
def get_satellite_options():
    """
    Returns available operational satellite datasets and study year options.
    Excludes non-operational datasets like Landsat 10 from active selection lists,
    while maintaining the extensible architecture.
    """
    operational_datasets = {
        k: v for k, v in SATELLITE_DATASETS.items() if v.get("is_operational", True)
    }
    return {
        "options": STUDY_YEAR_DATASET_OPTIONS,
        "datasets": operational_datasets,
        "supported_years": SUPPORTED_YEARS,
    }


@app.get("/api/projects/{project_id}/classes")
def get_project_classes(project_id: str):
    """Returns study-area configured LULC classes."""
    meta = load_project_metadata(project_id)
    classes = meta.get("classes") or get_default_classes()
    return {"classes": classes}


@app.post("/api/projects/{project_id}/classes")
def update_project_classes(project_id: str, payload: UpdateClassesRequest):
    """Updates study-area LULC classes and regenerates QGIS Starter package."""
    meta = load_project_metadata(project_id)
    proj_dir = os.path.join(PROJECTS_DIR, project_id)
    meta["classes"] = payload.classes

    # Regenerate QGIS package if boundary already exists
    b_path = os.path.join(proj_dir, "boundary.geojson")
    if os.path.exists(b_path):
        with open(b_path, "r", encoding="utf-8") as f:
            b_geo = json.load(f)
        create_qgis_starter_package(
            proj_dir,
            meta["name"],
            b_geo,
            meta.get("area_ha", 0),
            classes=payload.classes,
        )

    save_project_metadata(project_id, meta)
    return {"status": "success", "classes": meta["classes"]}


@app.get("/api/projects")
def list_projects(include_archived: bool = True):
    """
    Lists existing study area projects.
    Returns:
      - 'projects': active (non-archived) projects for standard selector
      - 'active_projects': active projects list
      - 'archived_projects': archived projects list
      - 'all_projects': complete list of all projects
    """
    all_projects = []
    if os.path.exists(PROJECTS_DIR):
        for pid in os.listdir(PROJECTS_DIR):
            p_dir = os.path.join(PROJECTS_DIR, pid)
            if os.path.isdir(p_dir):
                meta_path = os.path.join(p_dir, "project_metadata.json")
                if os.path.exists(meta_path):
                    try:
                        with open(meta_path, "r", encoding="utf-8") as f:
                            p_meta = json.load(f)
                            p_meta.setdefault("is_archived", False)
                            all_projects.append(p_meta)
                    except Exception as err:
                        print(f"Error reading project metadata {pid}: {err}")

    all_projects.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    active = [p for p in all_projects if not p.get("is_archived", False)]
    archived = [p for p in all_projects if p.get("is_archived", False)]

    return {
        "projects": active,
        "active_projects": active,
        "archived_projects": archived,
        "all_projects": all_projects,
    }


@app.post("/api/projects/{project_id}/archive")
def archive_project(project_id: str):
    """
    Archives a project so it no longer appears in the active project selector.
    Preserves all associated data: boundaries, samples, composites, classified rasters, and exports.
    """
    meta = load_project_metadata(project_id)
    meta["is_archived"] = True
    meta["archived_at"] = datetime.datetime.now().isoformat()
    save_project_metadata(project_id, meta)
    return {
        "status": "success",
        "message": f"Project '{meta.get('name', project_id)}' archived successfully.",
        "project": meta,
    }


@app.post("/api/projects/{project_id}/restore")
def restore_project(project_id: str):
    """
    Restores an archived project back to active status in the selector without losing any data.
    """
    meta = load_project_metadata(project_id)
    meta["is_archived"] = False
    meta["restored_at"] = datetime.datetime.now().isoformat()
    save_project_metadata(project_id, meta)
    return {
        "status": "success",
        "message": f"Project '{meta.get('name', project_id)}' restored to active list.",
        "project": meta,
    }


@app.delete("/api/projects/{project_id}")
def delete_project(project_id: str):
    """
    Permanently deletes a study area project and all associated files.
    Enforces strict path checks to ensure only the specified project within PROJECTS_DIR is removed.
    """
    clean_id = project_id.strip()
    if not clean_id or ".." in clean_id or "/" in clean_id or "\\" in clean_id:
        raise HTTPException(status_code=400, detail="Invalid project ID format.")

    target_dir = os.path.abspath(os.path.join(PROJECTS_DIR, clean_id))
    abs_base = os.path.abspath(PROJECTS_DIR)

    if os.path.dirname(target_dir) != abs_base:
        raise HTTPException(status_code=400, detail="Unsafe project path detected.")

    if not os.path.exists(target_dir) or not os.path.isdir(target_dir):
        raise HTTPException(status_code=404, detail=f"Project '{clean_id}' not found.")

    try:
        shutil.rmtree(target_dir)
        return {
            "status": "success",
            "message": f"Project '{clean_id}' and all associated files have been permanently deleted.",
            "deleted_id": clean_id,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete project directory: {str(e)}")


# ==========================================
# STEP 1: CREATE A NEW PROJECT
# ==========================================

@app.post("/api/projects/create")
def create_project(payload: CreateProjectRequest):
    """
    Step 1: Creates a new isolated study area project directory and metadata.
    Initializes with configurable classes and chosen satellite dataset.
    """
    clean_name = "".join(c if c.isalnum() or c in ("-", "_") else "_" for c in payload.name.strip())
    project_id = f"{clean_name.lower()}_{uuid.uuid4().hex[:6]}"
    proj_dir = os.path.join(PROJECTS_DIR, project_id)
    os.makedirs(proj_dir, exist_ok=True)

    metadata = {
        "id": project_id,
        "name": payload.name.strip(),
        "district": payload.district.strip(),
        "description": payload.description.strip(),
        "target_year": payload.target_year,
        "satellite_dataset": payload.satellite_dataset or "landsat_8_9",
        "created_at": datetime.datetime.now().isoformat(),
        "current_step": 1,
        "has_boundary": False,
        "has_samples": False,
        "has_classification": False,
        "is_archived": False,
        "classes": get_default_classes(),
    }
    save_project_metadata(project_id, metadata)
    return {"status": "success", "project": metadata}


# ==========================================
# STEP 2: UPLOAD STUDY AREA SHAPEFILE
# ==========================================

@app.post("/api/projects/{project_id}/upload-boundary")
async def upload_study_area_shapefile(
    project_id: str,
    request: Request,
):
    """
    Step 2: Accepts a zipped ESRI Shapefile, parses polygons, reprojects to WGS 84,
    computes bounding box and area (ha / km²), and creates the QGIS starter package.
    """
    meta = load_project_metadata(project_id)
    proj_dir = os.path.join(PROJECTS_DIR, project_id)

    raw_bytes = await request.body()
    file_bytes = extract_file_bytes(raw_bytes)

    if not file_bytes:
        raise HTTPException(status_code=400, detail="Empty shapefile received.")

    try:
        shp_result = process_shapefile_zip(file_bytes, proj_dir)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Shapefile processing failed: {str(e)}")

    # Load the resulting boundary GeoJSON
    with open(shp_result["geojson_path"], "r", encoding="utf-8") as f:
        boundary_geojson = json.load(f)

    # Generate QGIS Starter Package for Step 4 preparation
    qgis_zip_path = create_qgis_starter_package(
        proj_dir,
        meta["name"],
        boundary_geojson,
        shp_result["area_ha"],
        classes=meta.get("classes"),
    )


    # Update metadata
    meta["has_boundary"] = True
    meta["current_step"] = max(meta.get("current_step", 1), 2)
    meta["area_ha"] = shp_result["area_ha"]
    meta["area_sqkm"] = shp_result["area_sqkm"]
    meta["bounds"] = shp_result["bounds"]
    meta["center"] = shp_result["center"]
    meta["vertex_count"] = shp_result["vertex_count"]
    meta["qgis_starter_kit"] = os.path.basename(qgis_zip_path)
    save_project_metadata(project_id, meta)

    return {
        "status": "success",
        "message": "Study area shapefile parsed and boundary established.",
        "area_ha": shp_result["area_ha"],
        "area_sqkm": shp_result["area_sqkm"],
        "bounds": shp_result["bounds"],
        "center": shp_result["center"],
        "vertex_count": shp_result["vertex_count"],
        "boundary_geojson": boundary_geojson,
    }


@app.get("/api/projects/{project_id}/boundary")
def get_project_boundary(project_id: str):
    """Retrieves boundary GeoJSON for Leaflet overlay."""
    proj_dir = os.path.join(PROJECTS_DIR, project_id)
    b_path = os.path.join(proj_dir, "boundary.geojson")
    if not os.path.exists(b_path):
        raise HTTPException(status_code=404, detail="Boundary GeoJSON not found for this project.")
    return FileResponse(b_path, media_type="application/geo+json")


@app.get("/api/projects/{project_id}/satellite-availability")
def check_project_satellite_availability(
    project_id: str,
    year: Optional[int] = Query(None),
    dataset: Optional[str] = Query(None),
):
    """
    Checks if valid satellite scenes are available for the study area boundary.
    Returns scene count, sensor, resolution, and warning message if no imagery exists.
    """
    meta = load_project_metadata(project_id)
    if not meta.get("has_boundary"):
        raise HTTPException(status_code=400, detail="Please upload a study area boundary shapefile first.")

    target_year = year or meta.get("target_year", 2025)
    target_dataset = dataset or meta.get("satellite_dataset", "auto")

    proj_dir = os.path.join(PROJECTS_DIR, project_id)
    b_path = os.path.join(proj_dir, "boundary.geojson")
    with open(b_path, "r", encoding="utf-8") as f:
        boundary_fc = json.load(f)
    geometry = boundary_fc["features"][0]["geometry"]

    availability = check_satellite_availability(geometry, target_year, target_dataset)
    return availability


# ==========================================
# STEP 3: SATELLITE BAND PREPARATION & INDICES
# ==========================================

@app.get("/api/projects/{project_id}/bands")
def prepare_satellite_bands(
    project_id: str,
    year: Optional[int] = Query(None),
    dataset: Optional[str] = Query(None),
):
    """
    Step 3: Acquires satellite surface reflectance imagery (Landsat or Sentinel-2),
    masks clouds/shadows, composites median pixels, calculates 6 spectral indices,
    adds SRTM topography, and returns Earth Engine tile URLs for map preview.
    """
    meta = load_project_metadata(project_id)
    if not meta.get("has_boundary"):
        raise HTTPException(status_code=400, detail="Please upload a study area boundary shapefile first.")

    target_year = year or meta.get("target_year", 2025)
    target_dataset = dataset or meta.get("satellite_dataset", "auto")
    proj_dir = os.path.join(PROJECTS_DIR, project_id)
    b_path = os.path.join(proj_dir, "boundary.geojson")

    with open(b_path, "r", encoding="utf-8") as f:
        boundary_fc = json.load(f)
    geometry = boundary_fc["features"][0]["geometry"]

    # Check for Landsat 10 explicitly
    if (target_dataset or "").lower() == "landsat_10":
        raise HTTPException(
            status_code=400,
            detail="Landsat 10 (Landsat Next) is not currently an operational dataset. Reserved for future satellite mission deployment."
        )

    # Acquire and build stack
    sat_info = get_satellite_composite_for_geometry(geometry, target_year, dataset=target_dataset)
    if not sat_info.get("is_available", True) or sat_info["scenes_count"] == 0:
        raise HTTPException(
            status_code=400,
            detail=f"No suitable {sat_info.get('sensor', 'satellite')} imagery found for study year {target_year} in this area. Please select an alternative satellite dataset (such as Landsat 8 & 9) or a different study year."
        )

    composite_img = sat_info["image"]
    with_indices = compute_spectral_indices(composite_img)
    feature_stack = build_full_feature_stack(with_indices, sat_info["geometry"])

    # Generate tile URLs for the preview layers
    tcc_tile = get_layer_map_tile_url(feature_stack, "tcc")
    fcc_tile = get_layer_map_tile_url(feature_stack, "fcc")
    ndvi_tile = get_layer_map_tile_url(feature_stack, "ndvi")
    ndbi_tile = get_layer_map_tile_url(feature_stack, "ndbi")
    mndwi_tile = get_layer_map_tile_url(feature_stack, "mndwi")

    # Update metadata current step & dataset
    meta["current_step"] = max(meta.get("current_step", 1), 3)
    meta["satellite_dataset"] = sat_info.get("dataset", target_dataset)
    meta["target_year"] = target_year
    save_project_metadata(project_id, meta)

    return {
        "status": "success",
        "year": target_year,
        "dataset": sat_info.get("dataset", target_dataset),
        "sensor": sat_info["sensor"],
        "scenes_count": sat_info["scenes_count"],
        "native_resolution": sat_info.get("native_resolution", "30m"),
        "resolution_desc": sat_info.get("resolution_desc", "30 m (Optical & SWIR)"),
        "analysis_resolution": 30,
        "temporal_window": sat_info["temporal_window"],
        "features_prepared": [
            "blue", "green", "red", "nir", "swir1", "swir2",
            "ndvi", "ndbi", "mndwi", "bsi", "ui", "savi",
            "elevation", "slope"
        ],
        "tile_layers": {
            "tcc": tcc_tile["tile_url"],
            "fcc": fcc_tile["tile_url"],
            "ndvi": ndvi_tile["tile_url"],
            "ndbi": ndbi_tile["tile_url"],
            "mndwi": mndwi_tile["tile_url"],
        },
    }


# ==========================================
# STEP 4: GROUND-TRUTH & VALIDATION SAMPLING
# ==========================================

@app.get("/api/projects/{project_id}/qgis-kit")
def download_qgis_starter_kit(project_id: str):
    """
    Downloads the pre-packaged QGIS Starter Kit ZIP containing:
    - study_area_boundary.geojson
    - lulc_8class_symbology.qml
    - reference_points_template.geojson
    - stratified_sampling_grid.geojson
    - QGIS_DIGITIZATION_GUIDE.md
    """
    meta = load_project_metadata(project_id)
    proj_dir = os.path.join(PROJECTS_DIR, project_id)
    kit_filename = meta.get("qgis_starter_kit", f"{meta['name']}_QGIS_Starter_Kit.zip")
    kit_path = os.path.join(proj_dir, kit_filename)

    b_path = os.path.join(proj_dir, "boundary.geojson")
    if os.path.exists(b_path):
        with open(b_path, "r", encoding="utf-8") as f:
            b_geo = json.load(f)
        kit_path = create_qgis_starter_package(
            proj_dir,
            meta["name"],
            b_geo,
            meta.get("area_ha", 0),
            classes=meta.get("classes"),
        )
    elif not os.path.exists(kit_path):
        raise HTTPException(status_code=400, detail="Boundary file not found. Upload shapefile first.")

    return FileResponse(
        kit_path,
        media_type="application/zip",
        filename=os.path.basename(kit_path),
    )


@app.post("/api/projects/{project_id}/upload-samples")
async def upload_ground_truth_samples(
    project_id: str,
    request: Request,
):
    """
    Step 4: Upload digitized ground-truth points (GeoJSON or CSV).
    Validates classes against the project's dynamic scheme, performs stratified
    70% training / 30% independent validation split, and updates project metadata.
    """
    meta = load_project_metadata(project_id)
    proj_dir = os.path.join(PROJECTS_DIR, project_id)

    filename = request.headers.get("x-filename", "samples.geojson")
    raw_bytes = await request.body()
    file_bytes = extract_file_bytes(raw_bytes)

    if not file_bytes:
        raise HTTPException(status_code=400, detail="Empty reference samples file received.")

    try:
        split_result = parse_and_split_reference_points(
            file_bytes,
            filename,
            project_classes=meta.get("classes"),
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Reference sample parsing error: {str(e)}")

    # Save training and validation points
    train_path = os.path.join(proj_dir, "training_points.json")
    val_path = os.path.join(proj_dir, "validation_points.json")

    with open(train_path, "w", encoding="utf-8") as f:
        json.dump(split_result["training_points"], f, indent=2)

    with open(val_path, "w", encoding="utf-8") as f:
        json.dump(split_result["validation_points"], f, indent=2)

    meta["has_samples"] = True
    meta["current_step"] = max(meta.get("current_step", 1), 4)
    meta["total_samples"] = split_result["total_points"]
    meta["training_samples_count"] = split_result["training_count"]
    meta["validation_samples_count"] = split_result["validation_count"]
    if split_result.get("confirmed_classes"):
        meta["classes"] = split_result["confirmed_classes"]
    save_project_metadata(project_id, meta)

    return {
        "status": "success",
        "message": f"Successfully parsed {split_result['total_points']} reference points across {len(split_result['class_breakdown'])} classes. Stratified into {split_result['training_count']} training points (70%) and {split_result['validation_count']} independent validation holdouts (30%).",
        "total_points": split_result["total_points"],
        "training_count": split_result["training_count"],
        "validation_count": split_result["validation_count"],
        "class_breakdown": split_result["class_breakdown"],
        "confirmed_classes": split_result.get("confirmed_classes", meta.get("classes")),
    }


# ==========================================
# STEP 5 & 6: MACHINE LEARNING CLASSIFICATION & ACCURACY
# ==========================================

@app.post("/api/projects/{project_id}/train-and-classify")
def execute_classification(
    project_id: str,
    year: Optional[int] = Query(None),
    algorithm: Optional[str] = Query(None),
    dataset: Optional[str] = Query(None),
    payload: Optional[ClassifyRequest] = None,
):
    """
    Step 5 & 6: Trains Supervised Classifier (Random Forest or Support Vector Machine)
    on 14 predictor bands with 70% training samples.
    Executes independent accuracy assessment on the 30% holdout validation points (OA, Kappa, PA, UA).
    Calculates class-wise area statistics (ha, km², %) and generates map tile URL.
    """
    meta = load_project_metadata(project_id)
    proj_dir = os.path.join(PROJECTS_DIR, project_id)

    target_year = year or (payload.year if payload else None) or meta.get("target_year", 2025)
    selected_algo = (payload.algorithm if payload and payload.algorithm else None) or algorithm or meta.get("selected_algorithm", "rf")
    selected_dataset = (payload.dataset if payload and payload.dataset else None) or dataset or meta.get("satellite_dataset", "auto")

    b_path = os.path.join(proj_dir, "boundary.geojson")
    train_path = os.path.join(proj_dir, "training_points.json")
    val_path = os.path.join(proj_dir, "validation_points.json")

    if not os.path.exists(b_path):
        raise HTTPException(status_code=400, detail="Boundary shapefile not found.")
    if not os.path.exists(train_path) or not os.path.exists(val_path):
        raise HTTPException(status_code=400, detail="Reference samples not found. Complete Step 4 first.")

    with open(b_path, "r", encoding="utf-8") as f:
        boundary_fc = json.load(f)
    geometry = boundary_fc["features"][0]["geometry"]

    with open(train_path, "r", encoding="utf-8") as f:
        training_pts = json.load(f)

    with open(val_path, "r", encoding="utf-8") as f:
        validation_pts = json.load(f)

    try:
        results = run_classification_workflow(
            proj_dir,
            geometry,
            target_year,
            training_pts,
            validation_pts,
            project_classes=meta.get("classes"),
            algorithm=selected_algo,
            satellite_dataset=selected_dataset,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"{selected_algo.upper()} classification failed: {str(e)}")

    # Update metadata
    meta["has_classification"] = True
    meta["current_step"] = max(meta.get("current_step", 1), 6)
    meta["latest_year"] = target_year
    meta["satellite_dataset"] = results.get("dataset", selected_dataset)
    meta["selected_algorithm"] = results.get("algorithm", selected_algo.upper())
    meta["overall_accuracy"] = results["accuracy"]["overall_accuracy"]
    meta["kappa"] = results["accuracy"]["kappa_coefficient"]
    save_project_metadata(project_id, meta)

    return results


# ==========================================
# STEP 7: MAP & RESULTS DISPLAY & EXPORT
# ==========================================

@app.get("/api/projects/{project_id}/results")
def get_classification_results(
    project_id: str,
    year: Optional[int] = Query(None),
    algorithm: Optional[str] = Query(None),
):
    """
    Step 7: Retrieves the stored LULC map tile URL, area statistics, and accuracy metrics.
    Supports optional algorithm filter ('rf' or 'svm').
    """
    meta = load_project_metadata(project_id)
    proj_dir = os.path.join(PROJECTS_DIR, project_id)
    target_year = year or meta.get("latest_year", meta.get("target_year", 2025))

    res_path = None
    if algorithm:
        algo_clean = algorithm.lower().strip()
        algo_path = os.path.join(proj_dir, f"classification_{target_year}_{algo_clean}.json")
        if os.path.exists(algo_path):
            res_path = algo_path

    if not res_path:
        base_path = os.path.join(proj_dir, f"classification_{target_year}.json")
        if os.path.exists(base_path):
            res_path = base_path

    if not res_path or not os.path.exists(res_path):
        raise HTTPException(
            status_code=404,
            detail=f"Classification results for year {target_year} not found. Run classification first."
        )

    with open(res_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        if "algorithm" not in data:
            data["algorithm"] = "RF"
            data["algorithm_name"] = "Random Forest (RF)"
        return data


@app.get("/api/projects/{project_id}/feature-importance")
def get_project_feature_importance(
    project_id: str,
    year: Optional[int] = Query(None),
):
    """
    Step 6: Retrieves or evaluates Random Forest Gini impurity feature importance
    across the 14 predictors using trained_classifier.explain().
    """
    meta = load_project_metadata(project_id)
    proj_dir = os.path.join(PROJECTS_DIR, project_id)
    target_year = year or meta.get("latest_year", meta.get("target_year", 2025))

    # 1. Check if already cached in classification results
    for fname in [f"classification_{target_year}_rf.json", f"classification_{target_year}.json"]:
        fpath = os.path.join(proj_dir, fname)
        if os.path.exists(fpath):
            try:
                with open(fpath, "r", encoding="utf-8") as jf:
                    data = json.load(jf)
                if data.get("feature_importance") and data["feature_importance"].get("ranked_features"):
                    return data["feature_importance"]
            except Exception:
                pass

    # 2. If not cached, compute via GEE explain() on existing training samples
    b_path = os.path.join(proj_dir, "boundary.geojson")
    train_path = os.path.join(proj_dir, "training_points.json")

    if not os.path.exists(b_path) or not os.path.exists(train_path):
        raise HTTPException(
            status_code=400,
            detail="Boundary shapefile and digitized training samples are required to compute feature importance."
        )

    with open(b_path, "r", encoding="utf-8") as f:
        boundary_fc = json.load(f)
    geometry = boundary_fc["features"][0]["geometry"]

    with open(train_path, "r", encoding="utf-8") as f:
        training_pts = json.load(f)

    try:
        importance = extract_rf_feature_importance(
            proj_dir,
            geometry,
            target_year,
            training_pts,
            satellite_dataset=meta.get("satellite_dataset", "auto"),
        )
        return importance
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to evaluate Random Forest feature importance: {str(e)}"
        )


@app.get("/api/projects/{project_id}/export/geotiff")
def export_geotiff(
    project_id: str,
    year: Optional[int] = Query(None),
    algorithm: Optional[str] = Query(None),
    download: bool = Query(True),
):
    """
    Exports classified 30 m GeoTIFF raster using selected algorithm (RF or SVM).
    If download=True (default), generates/caches locally and returns direct FileResponse.
    Falls back to Earth Engine direct download URL if needed.
    """
    meta = load_project_metadata(project_id)
    proj_dir = os.path.join(PROJECTS_DIR, project_id)
    target_year = year or meta.get("latest_year", meta.get("target_year", 2025))
    selected_algo = algorithm or meta.get("selected_algorithm", "rf")

    b_path = os.path.join(proj_dir, "boundary.geojson")
    train_path = os.path.join(proj_dir, "training_points.json")

    with open(b_path, "r", encoding="utf-8") as f:
        boundary_fc = json.load(f)
    geometry = boundary_fc["features"][0]["geometry"]

    with open(train_path, "r", encoding="utf-8") as f:
        training_pts = json.load(f)

    safe_name = sanitize_filename(meta["name"])
    filename = f"{safe_name}_LULC_{target_year}.tif"

    sat_dataset = meta.get("satellite_dataset", "auto")

    if download:
        try:
            cached_path = generate_and_cache_geotiff(
                proj_dir,
                geometry,
                target_year,
                meta["name"],
                training_pts,
                project_classes=meta.get("classes"),
                algorithm=selected_algo,
                satellite_dataset=sat_dataset,
            )
            return FileResponse(
                cached_path,
                media_type="image/tiff",
                filename=filename,
            )
        except Exception as e:
            print(f"Direct GeoTIFF generation notice: {e}, falling back to EE download URL.")

    try:
        url = get_geotiff_download_url(
            geometry,
            target_year,
            meta["name"],
            training_pts,
            project_classes=meta.get("classes"),
            satellite_dataset=sat_dataset,
        )
        return {"status": "success", "download_url": url, "filename": filename}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"GeoTIFF export failed: {str(e)}")


@app.get("/api/projects/{project_id}/export/image")
def export_map_image(
    project_id: str,
    year: Optional[int] = Query(None),
    algorithm: Optional[str] = Query(None),
    format: str = Query("png"),
    download: bool = Query(True),
):
    """
    Exports high-resolution PNG or JPEG map image using selected algorithm.
    If download=True (default), generates/caches locally and returns direct FileResponse.
    Falls back to image URL if needed.
    """
    meta = load_project_metadata(project_id)
    proj_dir = os.path.join(PROJECTS_DIR, project_id)
    target_year = year or meta.get("latest_year", meta.get("target_year", 2025))
    selected_algo = algorithm or meta.get("selected_algorithm", "rf")
    sat_dataset = meta.get("satellite_dataset", "auto")

    b_path = os.path.join(proj_dir, "boundary.geojson")
    train_path = os.path.join(proj_dir, "training_points.json")

    with open(b_path, "r", encoding="utf-8") as f:
        boundary_fc = json.load(f)
    geometry = boundary_fc["features"][0]["geometry"]

    with open(train_path, "r", encoding="utf-8") as f:
        training_pts = json.load(f)

    safe_name = sanitize_filename(meta["name"])
    ext = "jpg" if format.lower() in ["jpg", "jpeg"] else "png"
    filename = f"{safe_name}_LULC_{target_year}.{ext}"

    if download:
        try:
            cached_path = generate_and_cache_map_image(
                proj_dir,
                geometry,
                target_year,
                meta["name"],
                training_pts,
                project_classes=meta.get("classes"),
                img_format=ext,
                algorithm=selected_algo,
                satellite_dataset=sat_dataset,
            )
            return FileResponse(
                cached_path,
                media_type=f"image/{ext}",
                filename=filename,
            )
        except Exception as e:
            print(f"Direct map image generation notice: {e}, falling back to EE thumbnail URL.")

    try:
        url = get_map_image_render_url(
            geometry,
            target_year,
            training_pts,
            project_classes=meta.get("classes"),
            img_format=format,
            satellite_dataset=sat_dataset,
        )
        return {"status": "success", "image_url": url, "filename": filename, "format": format}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Image export failed: {str(e)}")


@app.get("/api/projects/{project_id}/export/csv")
def export_area_csv(
    project_id: str,
    year: Optional[int] = Query(None),
):
    """
    Downloads class-wise area quantification statistics as CSV.
    """
    meta = load_project_metadata(project_id)
    proj_dir = os.path.join(PROJECTS_DIR, project_id)
    target_year = year or meta.get("latest_year", meta.get("target_year", 2025))
    safe_name = sanitize_filename(meta["name"])

    res_path = os.path.join(proj_dir, f"classification_{target_year}.json")
    if not os.path.exists(res_path):
        raise HTTPException(status_code=404, detail="Classification not found.")

    with open(res_path, "r", encoding="utf-8") as f:
        res = json.load(f)

    csv_str = generate_area_stats_csv(res["area_statistics"], meta["name"], target_year)
    return Response(
        content=csv_str,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{safe_name}_LULC_Area_Stats_{target_year}.csv"'}
    )


@app.get("/api/projects/{project_id}/export/accuracy-csv")
def export_accuracy_matrix_csv(
    project_id: str,
    year: Optional[int] = Query(None),
):
    """
    Downloads confusion matrix, PA, UA, OA, and Kappa as CSV.
    """
    meta = load_project_metadata(project_id)
    proj_dir = os.path.join(PROJECTS_DIR, project_id)
    target_year = year or meta.get("latest_year", meta.get("target_year", 2025))
    safe_name = sanitize_filename(meta["name"])

    res_path = os.path.join(proj_dir, f"classification_{target_year}.json")
    if not os.path.exists(res_path):
        raise HTTPException(status_code=404, detail="Classification not found.")

    with open(res_path, "r", encoding="utf-8") as f:
        res = json.load(f)

    csv_str = generate_accuracy_csv(res["accuracy"], meta["name"], target_year, project_classes=meta.get("classes"))
    return Response(
        content=csv_str,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{safe_name}_Accuracy_Report_{target_year}.csv"'}
    )


@app.get("/api/projects/{project_id}/export/samples")
def export_ground_truth_samples(
    project_id: str,
    split: str = Query("all"),
    format: str = Query("geojson"),
):
    """
    Downloads digitized reference sample points (training, validation, or combined)
    as either GeoJSON or CSV with class metadata.
    """
    meta = load_project_metadata(project_id)
    proj_dir = os.path.join(PROJECTS_DIR, project_id)
    safe_name = sanitize_filename(meta["name"])
    classes = meta.get("classes")

    pts = []
    if split == "training":
        p_path = os.path.join(proj_dir, "training_points.json")
        if not os.path.exists(p_path):
            raise HTTPException(status_code=404, detail="Training samples not found.")
        with open(p_path, "r", encoding="utf-8") as f:
            pts = json.load(f)
        label = "Training"
    elif split == "validation":
        p_path = os.path.join(proj_dir, "validation_points.json")
        if not os.path.exists(p_path):
            raise HTTPException(status_code=404, detail="Validation samples not found.")
        with open(p_path, "r", encoding="utf-8") as f:
            pts = json.load(f)
        label = "Validation"
    else:
        train_p = os.path.join(proj_dir, "training_points.json")
        val_p = os.path.join(proj_dir, "validation_points.json")
        if os.path.exists(train_p):
            with open(train_p, "r", encoding="utf-8") as f:
                for p in json.load(f):
                    pc = dict(p)
                    pc["user_split"] = "Training"
                    pts.append(pc)
        if os.path.exists(val_p):
            with open(val_p, "r", encoding="utf-8") as f:
                for p in json.load(f):
                    pc = dict(p)
                    pc["user_split"] = "Validation"
                    pts.append(pc)
        if not pts:
            raise HTTPException(status_code=404, detail="No reference points found.")
        label = "GroundTruth_Reference"

    if format.lower() == "csv":
        csv_str = export_points_csv(pts, classes=classes, split_name=label)
        return Response(
            content=csv_str,
            media_type="text/csv",
            headers={"Content-Disposition": f'attachment; filename="{safe_name}_{label}_Points.csv"'}
        )
    else:
        fc = export_points_geojson(pts, classes=classes, split_name=label)
        return Response(
            content=json.dumps(fc, indent=2),
            media_type="application/geo+json",
            headers={"Content-Disposition": f'attachment; filename="{safe_name}_{label}_Points.geojson"'}
        )


@app.get("/api/projects/{project_id}/export/boundary")
def export_boundary_geojson(project_id: str):
    """Downloads study area boundary GeoJSON as an attachment."""
    meta = load_project_metadata(project_id)
    proj_dir = os.path.join(PROJECTS_DIR, project_id)
    safe_name = sanitize_filename(meta["name"])
    b_path = os.path.join(proj_dir, "boundary.geojson")
    if not os.path.exists(b_path):
        raise HTTPException(status_code=404, detail="Boundary file not found.")
    return FileResponse(
        b_path,
        media_type="application/geo+json",
        filename=f"{safe_name}_Study_Area_Boundary.geojson",
    )


@app.get("/api/projects/{project_id}/export/qml")
def export_qml_symbology(
    project_id: str,
    style_type: str = Query("raster"),
):
    """Downloads QGIS symbology style file (.qml) tailored to study area classes."""
    meta = load_project_metadata(project_id)
    proj_dir = os.path.join(PROJECTS_DIR, project_id)
    safe_name = sanitize_filename(meta["name"])
    qpack = os.path.join(proj_dir, "qgis_package")

    fn = "lulc_raster_symbology.qml" if style_type == "raster" else "lulc_symbology.qml"
    out_name = f"{safe_name}_Raster_Symbology.qml" if style_type == "raster" else f"{safe_name}_Vector_Symbology.qml"
    qp = os.path.join(qpack, fn)

    if not os.path.exists(qp):
        classes = meta.get("classes")
        if style_type == "raster":
            from services.sampling_service import generate_raster_qml_style_content
            content = generate_raster_qml_style_content(classes)
        else:
            from services.sampling_service import generate_qml_style_content
            content = generate_qml_style_content(classes)
        return Response(
            content=content,
            media_type="text/xml",
            headers={"Content-Disposition": f'attachment; filename="{out_name}"'}
        )
    return FileResponse(
        qp,
        media_type="text/xml",
        filename=out_name,
    )


@app.get("/api/projects/{project_id}/export/bundle")
def export_complete_package_bundle(
    project_id: str,
    year: Optional[int] = Query(None),
):
    """
    Downloads an All-In-One complete ZIP bundle containing all raster, vector,
    tabular, accuracy, and QGIS symbology files for the project.
    """
    meta = load_project_metadata(project_id)
    proj_dir = os.path.join(PROJECTS_DIR, project_id)
    target_year = year or meta.get("latest_year", meta.get("target_year", 2025))
    safe_name = sanitize_filename(meta["name"])

    try:
        bundle_path = create_complete_export_bundle(
            proj_dir,
            meta["name"],
            target_year,
            classes=meta.get("classes"),
        )
        return FileResponse(
            bundle_path,
            media_type="application/zip",
            filename=f"{safe_name}_Complete_LULC_Package_{target_year}.zip",
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Complete package bundling failed: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    print("Starting LULC Mapping Backend Server on http://localhost:8001 ...")
    uvicorn.run("app:app", host="127.0.0.1", port=8001, reload=True)
