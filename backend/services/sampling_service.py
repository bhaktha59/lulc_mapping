"""
Sampling & QGIS Integration Service for Tamil Nadu LULC Mapping.
Prepares QGIS Starter Kits, generates stratified sampling grids,
parses user-uploaded reference points, and executes independent 70/30 spatial splits.
"""

import os
import json
import random
import csv
import io
import zipfile
from config import LULC_CLASSES


def generate_qml_style_content(classes=None):
    """
    Generates QGIS QML XML vector point styling file for the project's configured LULC scheme.
    Includes full <symbols> definitions with circular markers, white outlines, and exact class RGB colors.
    """
    scheme = classes or LULC_CLASSES
    categories_xml = ""
    symbols_xml = ""

    for idx, (cid_raw, cinfo) in enumerate(sorted(scheme.items(), key=lambda x: int(x[0]))):
        cid = int(cid_raw)
        hex_col = cinfo.get("color", "#888888").lstrip("#")
        if len(hex_col) == 6:
            r = int(hex_col[0:2], 16)
            g = int(hex_col[2:4], 16)
            b = int(hex_col[4:6], 16)
        else:
            r, g, b = 128, 128, 128
        cname = cinfo.get("name", f"Class {cid}")

        categories_xml += f"""
      <category symbol="{idx}" value="{cid}" label="{cid}. {cname}" render="true"/>"""

        symbols_xml += f"""
      <symbol name="{idx}" type="marker" clip_to_extent="1" alpha="1" force_rhr="0">
        <layer class="SimpleMarker" locked="0" pass="0" enabled="1">
          <prop k="color" v="{r},{g},{b},255"/>
          <prop k="joinstyle" v="bevel"/>
          <prop k="name" v="circle"/>
          <prop k="offset" v="0,0"/>
          <prop k="outline_color" v="255,255,255,255"/>
          <prop k="outline_style" v="solid"/>
          <prop k="outline_width" v="0.6"/>
          <prop k="outline_width_unit" v="MM"/>
          <prop k="scale_method" v="diameter"/>
          <prop k="size" v="4.2"/>
          <prop k="size_unit" v="MM"/>
          <prop k="vertical_anchor_point" v="1"/>
          <prop k="horizontal_anchor_point" v="1"/>
        </layer>
      </symbol>"""

    qml_content = f"""<!DOCTYPE qgis PUBLIC 'http://mrcc.com/qgis.dtd' 'SYSTEM'>
<qgis styleCategories="AllStyleCategories" version="3.28.0">
  <renderer-v2 attr="class_id" type="categorizedSymbol">
    <categories>{categories_xml}
    </categories>
    <symbols>{symbols_xml}
    </symbols>
  </renderer-v2>
  <blendMode>0</blendMode>
  <featureBlendMode>0</featureBlendMode>
</qgis>
"""
    return qml_content


def generate_grid_qml_style_content():
    """
    Generates QGIS QML polygon styling file for the stratified sampling grid.
    Visualizes Validation Grids (30% Holdout) in amber dashed fill and Non-Validation / Training Grids (70%) in emerald solid fill.
    """
    qml_content = """<!DOCTYPE qgis PUBLIC 'http://mrcc.com/qgis.dtd' 'SYSTEM'>
<qgis styleCategories="AllStyleCategories" version="3.28.0">
  <renderer-v2 attr="grid_type" type="categorizedSymbol">
    <categories>
      <category symbol="0" value="Non-Validation (Training) Grid" label="Non-Validation / Training Grids (70%)" render="true"/>
      <category symbol="1" value="Validation Grid" label="Validation Grids (30% Holdout)" render="true"/>
    </categories>
    <symbols>
      <symbol name="0" type="fill" clip_to_extent="1" alpha="1" force_rhr="0">
        <layer class="SimpleFill" locked="0" pass="0" enabled="1">
          <prop k="color" v="16,185,129,50"/>
          <prop k="outline_color" v="5,150,105,255"/>
          <prop k="outline_style" v="solid"/>
          <prop k="outline_width" v="0.5"/>
          <prop k="outline_width_unit" v="MM"/>
          <prop k="style" v="solid"/>
        </layer>
      </symbol>
      <symbol name="1" type="fill" clip_to_extent="1" alpha="1" force_rhr="0">
        <layer class="SimpleFill" locked="0" pass="0" enabled="1">
          <prop k="color" v="245,158,11,65"/>
          <prop k="outline_color" v="217,119,6,255"/>
          <prop k="outline_style" v="dash"/>
          <prop k="outline_width" v="0.7"/>
          <prop k="outline_width_unit" v="MM"/>
          <prop k="style" v="solid"/>
        </layer>
      </symbol>
    </symbols>
  </renderer-v2>
  <blendMode>0</blendMode>
  <featureBlendMode>0</featureBlendMode>
</qgis>
"""
    return qml_content


def generate_raster_qml_style_content(classes=None):
    """
    Generates QGIS QML raster paletted styling file for classified GeoTIFF maps.
    """
    scheme = classes or LULC_CLASSES
    entries = ""
    for cid_raw, cinfo in sorted(scheme.items(), key=lambda x: int(x[0])):
        cid = int(cid_raw)
        color = cinfo.get("color", "#888888")
        cname = cinfo.get("name", f"Class {cid}")
        entries += f"""
        <paletteEntry value="{cid}" color="{color}" label="{cid}. {cname}" alpha="255"/>"""

    qml_content = f"""<!DOCTYPE qgis PUBLIC 'http://mrcc.com/qgis.dtd' 'SYSTEM'>
<qgis styleCategories="AllStyleCategories" version="3.28.0">
  <pipe>
    <rasterrenderer type="paletted" band="1" opacity="1">
      <colorPalette>{entries}
      </colorPalette>
    </rasterrenderer>
    <brightnesscontrast brightness="0" contrast="0"/>
    <huesaturation colorizeGreen="128" colorizeOn="0" colorizeRed="255" saturation="0" grayscaleMode="0" colorizeStrength="100" colorizeBlue="128"/>
    <rasterresampler maxOversampling="2"/>
  </pipe>
  <blendMode>0</blendMode>
</qgis>
"""
    return qml_content


def generate_qgis_guide_content(project_name, area_ha, classes=None):
    scheme = classes or LULC_CLASSES
    class_count = len(scheme)
    table_rows = ""
    for cid_raw, cinfo in sorted(scheme.items(), key=lambda x: int(x[0])):
        cid = int(cid_raw)
        name = cinfo.get("name", f"Class {cid}")
        desc = cinfo.get("desc") or cinfo.get("description") or "Land cover category"
        min_samp = cinfo.get("min_samples", 30)
        table_rows += f"| **{cid}** | **{name}** | {desc} | Recommended target: {min_samp}+ points |\n"

    return f"""# QGIS Ground-Truth Reference Point Digitization Guide
**Project:** {project_name}
**Study Area Area:** {area_ha:,.2f} ha (~{area_ha/100:.2f} km²)
**Classification Scheme:** {class_count} Dynamic Classes (Configured for this Study Area)

---

## 1. Setting Up QGIS
1. Launch **QGIS 3.x** (QGIS Desktop).
2. Install **QuickMapServices** plugin (via **Plugins -> Manage and Install Plugins...**).
3. Add a high-resolution satellite basemap: **Web -> QuickMapServices -> Google -> Google Satellite** (or ESRI Imagery).
4. Drag and drop `study_area_boundary.geojson` into your Layers panel to see your boundary.

---

## 2. Using the Classified Sampling Grids (Validation vs Non-Validation)
1. Drag and drop `stratified_sampling_grid.geojson` into QGIS.
2. Right-click the layer -> **Properties -> Symbology** -> **Style -> Load Style...** -> choose **`grid_symbology.qml`**.
3. You will immediately see two distinct grid types:
   - **Green Solid Grids (70% - Non-Validation / Training):** Use these cells to digitize samples for training the Random Forest model.
   - **Orange Dashed Grids (30% - Validation Holdout):** Strictly reserve these cells for collecting independent test/validation points. Spatial separation avoids spatial autocorrelation between training and test sets!

---

## 3. Opening & Styling Reference Points Template
1. Drag and drop `reference_points_template.geojson` into QGIS.
2. Right-click the layer -> **Properties -> Symbology** -> **Style -> Load Style...** -> choose **`lulc_symbology.qml`**.
3. All class names and custom color markers will display clearly with circular symbols.

---

## 4. Digitizing Ground Reference Samples
1. Select `reference_points_template` in Layers panel and click **Toggle Editing** (`Ctrl+E`).
2. Click **Add Point Feature** (`Ctrl+.`).
3. Click on recognizable features in the satellite imagery. Enter the **class_id** integer:

| Class ID | Class Name | Description / Characteristics | Sampling Requirement |
| :---: | :--- | :--- | :--- |
{table_rows}
4. You can also specify `split` (`Training` or `Validation`) depending on whether the point is placed inside a Green (Non-Validation) or Orange (Validation) grid cell.

---

## 5. Saving and Uploading Back to Web Portal
1. Click **Save Layer Edits** (`Ctrl+S`) and toggle off editing mode (`Ctrl+E`).
2. The file is saved directly into `reference_points_template.geojson` (or export as GeoJSON/CSV).
3. Return to the LULC Mapping Web Portal and upload your file in **Step 4: Ground Truth & Validation**.

*(Note: When you export the classified GeoTIFF from the portal later, you can also apply `lulc_raster_symbology.qml` directly to the raster layer in QGIS for 1-click styling!)*
"""


def _point_in_ring(x, y, ring):
    n = len(ring)
    if n < 3:
        return False
    inside = False
    p1x, p1y = ring[0]
    for i in range(1, n + 1):
        p2x, p2y = ring[i % n]
        if y > min(p1y, p2y):
            if y <= max(p1y, p2y):
                if x <= max(p1x, p2x):
                    if p1y != p2y:
                        xinters = (y - p1y) * (p2x - p1x) / (p2y - p1y) + p1x
                    if p1x == p2x or x <= xinters:
                        inside = not inside
        p1x, p1y = p2x, p2y
    return inside


def _point_in_geometry(x, y, geometry):
    gtype = geometry.get("type", "")
    coords = geometry.get("coordinates", [])
    if gtype == "Polygon":
        if not coords:
            return False
        if _point_in_ring(x, y, coords[0]):
            for hole in coords[1:]:
                if _point_in_ring(x, y, hole):
                    return False
            return True
        return False
    elif gtype == "MultiPolygon":
        for poly in coords:
            if not poly:
                continue
            if _point_in_ring(x, y, poly[0]):
                in_hole = False
                for hole in poly[1:]:
                    if _point_in_ring(x, y, hole):
                        in_hole = True
                        break
                if not in_hole:
                    return True
        return False
    return False


def generate_sampling_grid(geometry, grid_size_deg=0.018):
    """
    Generates a regular ~2 km spatial grid covering the study area.
    Filters cells to intersect the study area boundary, and systematically classifies cells into:
    - Non-Validation (Training) Grid (70%): For collecting training samples
    - Validation Grid (30% Holdout): For independent accuracy assessment validation samples
    """
    all_vertices = []
    gtype = geometry.get("type", "")
    coords = geometry.get("coordinates", [])

    if gtype == "Polygon":
        for ring in coords:
            all_vertices.extend(ring)
    elif gtype == "MultiPolygon":
        for poly in coords:
            for ring in poly:
                all_vertices.extend(ring)

    if not all_vertices:
        all_vertices = [[78.0, 10.0], [79.0, 11.0]]

    min_lon = min(pt[0] for pt in all_vertices)
    max_lon = max(pt[0] for pt in all_vertices)
    min_lat = min(pt[1] for pt in all_vertices)
    max_lat = max(pt[1] for pt in all_vertices)

    # Fast spatial hash bucket for boundary vertices
    vertex_bins = set()
    for vx, vy in all_vertices:
        c_bin = int((vx - min_lon) / grid_size_deg)
        r_bin = int((vy - min_lat) / grid_size_deg)
        vertex_bins.add((c_bin, r_bin))

    grid_features = []
    cur_lon = min_lon
    col_idx = 0
    raw_cells = []

    while cur_lon < max_lon:
        cur_lat = min_lat
        row_idx = 0
        while cur_lat < max_lat:
            c_min = cur_lon
            c_max = cur_lon + grid_size_deg
            r_min = cur_lat
            r_max = cur_lat + grid_size_deg
            c_center_x = round((c_min + c_max) / 2.0, 6)
            c_center_y = round((r_min + r_max) / 2.0, 6)

            # Check if this cell intersects study area
            intersects = False
            if (col_idx, row_idx) in vertex_bins:
                intersects = True
            elif _point_in_geometry(c_center_x, c_center_y, geometry):
                intersects = True
            else:
                for cx, cy in [(c_min, r_min), (c_max, r_min), (c_max, r_max), (c_min, r_max)]:
                    if _point_in_geometry(cx, cy, geometry):
                        intersects = True
                        break

            if intersects:
                raw_cells.append({
                    "col": col_idx,
                    "row": row_idx,
                    "poly": [
                        [round(c_min, 6), round(r_min, 6)],
                        [round(c_max, 6), round(r_min, 6)],
                        [round(c_max, 6), round(r_max, 6)],
                        [round(c_min, 6), round(r_max, 6)],
                        [round(c_min, 6), round(r_min, 6)],
                    ]
                })

            cur_lat += grid_size_deg
            row_idx += 1
        cur_lon += grid_size_deg
        col_idx += 1

    # Fallback if boundary check was completely empty
    if not raw_cells:
        raw_cells.append({
            "col": 0, "row": 0,
            "poly": [
                [round(min_lon, 6), round(min_lat, 6)],
                [round(max_lon, 6), round(min_lat, 6)],
                [round(max_lon, 6), round(max_lat, 6)],
                [round(min_lon, 6), round(max_lat, 6)],
                [round(min_lon, 6), round(min_lat, 6)],
            ]
        })

    # Classify grids into 70% Training (Non-Validation) and 30% Validation Holdout
    cell_id = 1
    for cell in raw_cells:
        c = cell["col"]
        r = cell["row"]
        # Deterministic spatial pseudo-random hash ensuring balanced 30/70 split across space
        spatial_hash = ((c * 73856093) ^ (r * 19349663) ^ 42) % 100
        is_val = spatial_hash < 30

        grid_type = "Validation Grid" if is_val else "Non-Validation (Training) Grid"
        split_name = "Validation" if is_val else "Training"
        role_desc = (
            "Independent Holdout Validation (30%): Digitize points here to independently test accuracy."
            if is_val
            else "Model Training Sampling (70%): Digitize points here to train the Random Forest model."
        )

        grid_features.append({
            "type": "Feature",
            "properties": {
                "grid_id": cell_id,
                "grid_type": grid_type,
                "split": split_name,
                "is_validation": is_val,
                "sampling_role": role_desc,
                "size_km": 2.0,
            },
            "geometry": {
                "type": "Polygon",
                "coordinates": [cell["poly"]],
            },
        })
        cell_id += 1

    return {
        "type": "FeatureCollection",
        "name": "stratified_sampling_grid",
        "features": grid_features,
    }


def create_qgis_starter_package(project_dir, project_name, boundary_geojson, area_ha, classes=None):
    """
    Assembles a complete, downloadable QGIS Starter Kit ZIP archive tailored to the study area.
    Includes:
    - study_area_boundary.geojson
    - stratified_sampling_grid.geojson (Classified into Validation & Non-Validation grids)
    - grid_symbology.qml (Polygon style color-coding Validation vs Training grids)
    - reference_points_template.geojson (Schema-ready template with class fields)
    - lulc_symbology.qml & lulc_8class_symbology.qml (Complete Point Marker styles)
    - lulc_raster_symbology.qml (Raster paletted style for classified GeoTIFFs)
    - QGIS_DIGITIZATION_GUIDE.md (Detailed step-by-step instructions)
    """
    qgis_pack_dir = os.path.join(project_dir, "qgis_package")
    os.makedirs(qgis_pack_dir, exist_ok=True)

    # 1. Boundary GeoJSON
    b_path = os.path.join(qgis_pack_dir, "study_area_boundary.geojson")
    with open(b_path, "w", encoding="utf-8") as f:
        json.dump(boundary_geojson, f, indent=2)

    # 2. Vector Point QML Symbology
    qml_content = generate_qml_style_content(classes)
    qml_path = os.path.join(qgis_pack_dir, "lulc_symbology.qml")
    with open(qml_path, "w", encoding="utf-8") as f:
        f.write(qml_content)
    qml_legacy = os.path.join(qgis_pack_dir, "lulc_8class_symbology.qml")
    with open(qml_legacy, "w", encoding="utf-8") as f:
        f.write(qml_content)

    # 3. Grid Polygon QML Symbology (Validation vs Non-Validation grids)
    grid_qml_content = generate_grid_qml_style_content()
    grid_qml_path = os.path.join(qgis_pack_dir, "grid_symbology.qml")
    with open(grid_qml_path, "w", encoding="utf-8") as f:
        f.write(grid_qml_content)

    # 4. Raster Paletted QML Symbology (For classified GeoTIFFs)
    raster_qml_content = generate_raster_qml_style_content(classes)
    raster_qml_path = os.path.join(qgis_pack_dir, "lulc_raster_symbology.qml")
    with open(raster_qml_path, "w", encoding="utf-8") as f:
        f.write(raster_qml_content)

    # 5. Reference Points Template (Pre-populated with schema fields so QGIS detects columns immediately)
    geometry = boundary_geojson["features"][0]["geometry"]
    all_vertices = []
    gtype = geometry.get("type", "")
    coords = geometry.get("coordinates", [])
    if gtype == "Polygon" and coords:
        all_vertices = coords[0]
    elif gtype == "MultiPolygon" and coords and coords[0]:
        all_vertices = coords[0][0]

    mid_lon = round(sum(p[0] for p in all_vertices) / max(len(all_vertices), 1), 6) if all_vertices else 78.5
    mid_lat = round(sum(p[1] for p in all_vertices) / max(len(all_vertices), 1), 6) if all_vertices else 10.8

    scheme = classes or LULC_CLASSES
    first_cid = int(sorted(scheme.keys(), key=lambda x: int(x))[0]) if scheme else 1
    first_cname = (scheme.get(str(first_cid)) or {}).get("name", "Forest") if scheme else "Forest"

    template_fc = {
        "type": "FeatureCollection",
        "name": "reference_points_template",
        "crs": {"type": "name", "properties": {"name": "urn:ogc:def:crs:OGC:1.3:CRS84"}},
        "features": [
            {
                "type": "Feature",
                "properties": {
                    "class_id": first_cid,
                    "class_name": first_cname,
                    "split": "Training",
                    "grid_id": 1,
                    "notes": "Template reference point (edit class_id or delete when digitizing)",
                },
                "geometry": {
                    "type": "Point",
                    "coordinates": [mid_lon, mid_lat],
                },
            }
        ],
    }
    t_path = os.path.join(qgis_pack_dir, "reference_points_template.geojson")
    with open(t_path, "w", encoding="utf-8") as f:
        json.dump(template_fc, f, indent=2)

    # 6. Stratified Sampling Grid (Classified into Validation & Non-Validation)
    grid_fc = generate_sampling_grid(geometry)
    grid_path = os.path.join(qgis_pack_dir, "stratified_sampling_grid.geojson")
    with open(grid_path, "w", encoding="utf-8") as f:
        json.dump(grid_fc, f, indent=2)

    # 7. Digitization Guide
    guide_path = os.path.join(qgis_pack_dir, "QGIS_DIGITIZATION_GUIDE.md")
    with open(guide_path, "w", encoding="utf-8") as f:
        f.write(generate_qgis_guide_content(project_name, area_ha, classes))

    # 8. Add confirmed training and validation samples if already uploaded
    train_json = os.path.join(project_dir, "training_points.json")
    train_geo_path = None
    if os.path.exists(train_json):
        try:
            with open(train_json, "r", encoding="utf-8") as tf:
                train_data = json.load(tf)
            from services.export_service import export_points_geojson
            t_fc = export_points_geojson(train_data, classes=classes, split_name="Training")
            train_geo_path = os.path.join(qgis_pack_dir, "training_points.geojson")
            with open(train_geo_path, "w", encoding="utf-8") as f:
                json.dump(t_fc, f, indent=2)
        except Exception as e:
            print("Notice: Could not write training_points.geojson to qgis_package:", e)

    val_json = os.path.join(project_dir, "validation_points.json")
    val_geo_path = None
    if os.path.exists(val_json):
        try:
            with open(val_json, "r", encoding="utf-8") as vf:
                val_data = json.load(vf)
            from services.export_service import export_points_geojson
            v_fc = export_points_geojson(val_data, classes=classes, split_name="Validation")
            val_geo_path = os.path.join(qgis_pack_dir, "validation_points.geojson")
            with open(val_geo_path, "w", encoding="utf-8") as f:
                json.dump(v_fc, f, indent=2)
        except Exception as e:
            print("Notice: Could not write validation_points.geojson to qgis_package:", e)

    # 9. Create ZIP archive
    zip_path = os.path.join(project_dir, f"{project_name}_QGIS_Starter_Kit.zip")
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.write(b_path, arcname="study_area_boundary.geojson")
        zf.write(qml_path, arcname="lulc_symbology.qml")
        zf.write(qml_legacy, arcname="lulc_8class_symbology.qml")
        zf.write(grid_qml_path, arcname="grid_symbology.qml")
        zf.write(raster_qml_path, arcname="lulc_raster_symbology.qml")
        zf.write(t_path, arcname="reference_points_template.geojson")
        zf.write(grid_path, arcname="stratified_sampling_grid.geojson")
        zf.write(guide_path, arcname="QGIS_DIGITIZATION_GUIDE.md")
        if train_geo_path and os.path.exists(train_geo_path):
            zf.write(train_geo_path, arcname="training_points.geojson")
        if val_geo_path and os.path.exists(val_geo_path):
            zf.write(val_geo_path, arcname="validation_points.geojson")

    return zip_path


FALLBACK_PALETTE = [
    "#006400", "#0000FF", "#32CD32", "#F4A460", "#9ACD32", "#D2B48C",
    "#FF0000", "#808080", "#06B6D4", "#8B5CF6", "#F43F5E", "#EAB308",
    "#14B8A6", "#EC4899", "#A855F7", "#3B82F6", "#64748B"
]


def parse_and_split_reference_points(file_bytes, filename, project_classes=None, train_ratio=0.7, seed=42):
    """
    Parses user-uploaded reference points (GeoJSON or CSV), validates class IDs
    against the project's configured classes or dynamic IDs,
    and executes an independent stratified 70% Training / 30% Validation holdout split.
    """
    points = []
    classes_dict = project_classes or LULC_CLASSES

    # Build name-to-id mapping for robust class matching from class_name
    name_to_cid = {}
    valid_cids = set()
    for cid_k, cinfo in classes_dict.items():
        try:
            cid_int = int(cid_k)
            valid_cids.add(cid_int)
            cname = str(cinfo.get("name", "")).strip().lower()
            if cname:
                name_to_cid[cname] = cid_int
                clean_name = "".join(ch for ch in cname if ch.isalnum())
                name_to_cid[clean_name] = cid_int
        except (ValueError, TypeError):
            continue

    def resolve_class_id(props):
        # 1. Direct class_id or class
        raw_cid = props.get("class_id") if props.get("class_id") is not None else props.get("class")
        if raw_cid is None:
            raw_cid = props.get("label")

        if raw_cid is not None:
            try:
                val = int(raw_cid)
                if val in valid_cids or not valid_cids:
                    return val
            except (ValueError, TypeError):
                pass

        # 2. Check class_name string
        raw_name = props.get("class_name") or props.get("classname") or props.get("name") or props.get("label")
        if raw_name:
            n_str = str(raw_name).strip().lower()
            clean_str = "".join(ch for ch in n_str if ch.isalnum())
            if n_str in name_to_cid:
                return name_to_cid[n_str]
            if clean_str in name_to_cid:
                return name_to_cid[clean_str]
            for k, v in name_to_cid.items():
                if k in n_str or n_str in k:
                    return v

        # 3. Fallback: if raw_cid is a positive int, allow it
        if raw_cid is not None:
            try:
                val = int(raw_cid)
                if val > 0:
                    return val
            except (ValueError, TypeError):
                pass

        # 4. Only check props.get("id") if it strictly matches a known valid class ID
        raw_id = props.get("id")
        if raw_id is not None:
            try:
                val = int(raw_id)
                if val in valid_cids:
                    return val
            except (ValueError, TypeError):
                pass

        return None

    if filename.lower().endswith(".geojson") or filename.lower().endswith(".json"):
        data = json.loads(file_bytes.decode("utf-8"))
        features = data.get("features", [])
        for feat in features:
            props = feat.get("properties", {})
            geom = feat.get("geometry", {})
            notes = str(props.get("notes", ""))
            if len(features) > 1 and "Template reference point" in notes:
                continue
            if geom.get("type") == "Point" and geom.get("coordinates"):
                cid = resolve_class_id(props)
                if cid is not None and cid > 0:
                    lon, lat = geom["coordinates"][0], geom["coordinates"][1]
                    split_str = str(props.get("split", "")).lower()
                    u_split = "validation" if "val" in split_str else ("training" if "train" in split_str else None)
                    points.append({"lon": round(lon, 6), "lat": round(lat, 6), "class_id": cid, "user_split": u_split})

    elif filename.lower().endswith(".csv"):
        text = file_bytes.decode("utf-8", errors="ignore")
        reader = csv.DictReader(io.StringIO(text))
        for row in reader:
            notes = str(row.get("notes") or "")
            if "Template reference point" in notes:
                continue
            lat = row.get("latitude") or row.get("lat") or row.get("Y")
            lon = row.get("longitude") or row.get("lon") or row.get("lng") or row.get("X")
            if lat and lon:
                cid = resolve_class_id(row)
                if cid is not None and cid > 0:
                    try:
                        lat_f = float(lat)
                        lon_f = float(lon)
                        split_str = str(row.get("split") or "").lower()
                        u_split = "validation" if "val" in split_str else ("training" if "train" in split_str else None)
                        points.append({"lon": round(lon_f, 6), "lat": round(lat_f, 6), "class_id": cid, "user_split": u_split})
                    except (ValueError, TypeError):
                        continue

    if len(points) < 2:
        raise ValueError(
            f"Insufficient valid reference points found ({len(points)} point(s)). "
            "Please upload a file containing digitized ground-truth points with geographic coordinates and class_id."
        )

    # Group by class ID
    by_class = {}
    for pt in points:
        cid = pt["class_id"]
        by_class.setdefault(cid, []).append(pt)

    # If valid_cids is defined, drop any stray outlier class outside valid_cids with < 2 points
    if valid_cids:
        rogue_cids = [cid for cid, pts in by_class.items() if cid not in valid_cids and len(pts) < 2]
        for r_cid in rogue_cids:
            del by_class[r_cid]
            points = [p for p in points if p["class_id"] != r_cid]

    # Ensure each present class has at least 2 points for 70/30 split
    insufficient = []
    for cid, pts in sorted(by_class.items()):
        if len(pts) < 2:
            cname = (classes_dict.get(cid) or classes_dict.get(str(cid)) or {}).get("name", f"Class {cid}")
            insufficient.append(f"'{cname}' (Class {cid}): has {len(pts)} point, needs at least 2")

    if insufficient:
        raise ValueError(
            f"Each class requires at least 2 reference points for 70% training and 30% independent validation holdout. "
            f"Insufficient points found in: {'; '.join(insufficient)}."
        )

    # Stratified 70/30 Train/Val Split (respects user_split if provided from grids)
    random.seed(seed)
    training_points = []
    validation_points = []
    class_counts = {}
    confirmed_classes = {}

    for cid, pts in sorted(by_class.items()):
        random.shuffle(pts)
        n_pts = len(pts)

        user_val = [p for p in pts if p.get("user_split") == "validation"]
        user_trn = [p for p in pts if p.get("user_split") == "training"]

        if user_val and user_trn:
            train_subset = user_trn
            val_subset = user_val
        else:
            n_train = max(1, int(round(n_pts * train_ratio)))
            # Ensure at least 1 validation point if count > 1
            if n_pts > 1 and n_train == n_pts:
                n_train = n_pts - 1
            train_subset = pts[:n_train]
            val_subset = pts[n_train:]

        training_points.extend(train_subset)
        validation_points.extend(val_subset)

        # Retrieve or generate class info
        matched_info = classes_dict.get(cid) or classes_dict.get(str(cid))
        if matched_info:
            cname = matched_info.get("name", f"Class {cid}")
            color = matched_info.get("color", FALLBACK_PALETTE[(cid - 1) % len(FALLBACK_PALETTE)])
            desc = matched_info.get("desc") or matched_info.get("description", "")
            min_samp = matched_info.get("min_samples", 20)
        else:
            cname = f"Class {cid}"
            color = FALLBACK_PALETTE[(cid - 1) % len(FALLBACK_PALETTE)]
            desc = f"User digitized category {cid}"
            min_samp = 20

        class_counts[str(cid)] = {
            "id": cid,
            "name": cname,
            "color": color,
            "total": n_pts,
            "training": len(train_subset),
            "validation": len(val_subset),
            "min_samples": min_samp,
        }

        confirmed_classes[str(cid)] = {
            "id": cid,
            "name": cname,
            "color": color,
            "desc": desc,
            "min_samples": min_samp,
            "confirmed_points": n_pts,
        }

    return {
        "status": "success",
        "total_points": len(points),
        "training_count": len(training_points),
        "validation_count": len(validation_points),
        "class_breakdown": class_counts,
        "confirmed_classes": confirmed_classes,
        "training_points": training_points,
        "validation_points": validation_points,
    }

