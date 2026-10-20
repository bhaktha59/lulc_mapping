# QGIS Ground-Truth & Validation Sample Preparation Manual
**Tamil Nadu Land Use / Land Cover (LULC) Mapping Workflow**

This guide provides an end-to-end tutorial on preparing, digitizing, and validating reference points in QGIS for any study area in Tamil Nadu.

---

## 1. Prerequisites & Recommended QGIS Plugins

1. **Install QGIS Desktop 3.28+ LTR** (or any QGIS 3.x release).
2. Open QGIS and navigate to **Plugins -> Manage and Install Plugins...**:
   - **QuickMapServices**: Essential plugin providing one-click access to Google Satellite, Google Hybrid, ESRI World Imagery, and Bing Aerial basemaps.
   - *(Optional)* **Semi-Automatic Classification Plugin (SCP)** or **Lat Lon Tools** for fast coordinate capture.
3. Add the Google Satellite layer:
   - Go to **Web -> QuickMapServices -> Google -> Google Satellite** (or ESRI Imagery).

---

## 2. Using the Automated QGIS Starter Kit

When you upload your study area shapefile to the Tamil Nadu LULC Portal, the system automatically generates a tailored **`[ProjectName]_QGIS_Starter_Kit.zip`**.

Extract the ZIP archive. It contains:
1. `study_area_boundary.geojson` — Reprojected vector polygon of your study area in WGS 84.
2. `stratified_sampling_grid.geojson` — 2 km systematic grid to ensure spatial coverage across the taluk/district.
3. `lulc_8class_symbology.qml` — Preconfigured QGIS symbology with official Tamil Nadu color codes.
4. `reference_points_template.geojson` — Empty point layer pre-structured for digitization.

---

## 3. Digitization Workflow in QGIS

1. **Load Layers**:
   - Drag and drop `study_area_boundary.geojson` into QGIS.
   - Drag and drop `stratified_sampling_grid.geojson` into QGIS (set style to transparent fill with grey outline).
   - Drag and drop `reference_points_template.geojson` into QGIS.
2. **Apply Symbology**:
   - Right-click `reference_points_template` -> **Properties -> Symbology**.
   - Click the bottom button **Style -> Load Style...** -> Select `lulc_8class_symbology.qml`.
3. **Toggle Editing**:
   - Select the reference points layer and click **Toggle Editing** (`Ctrl+E` or the Yellow Pencil icon).
4. **Digitize Points**:
   - Click **Add Point Feature** (`Ctrl+.`).
   - Click on the map over a clear land cover feature and enter the integer `class_id` (1 through 8).

### Official 8-Class Scheme Reference

| Class ID | Class Name | Color Hex | Photo Interpretation Guide |
| :---: | :--- | :---: | :--- |
| **1** | **Forest** | `#006400` (Dark Green) | Dense canopy, reserve forest blocks, hill tree groves |
| **2** | **Waterbodies** | `#0000FF` (Blue) | Tanks (Eri), lakes, dams, river channels, reservoirs |
| **3** | **Cropland** | `#32CD32` (Lime Green) | Active green agricultural plots, paddy fields, plantations |
| **4** | **Fallowland** | `#F4A460` (Sandy Brown) | Plowed or dry agricultural plots without active crop cover |
| **5** | **Land with scrub** | `#9ACD32` (Yellow Green) | Foothill scrub, open thorny bushes, degraded vegetation |
| **6** | **Land without scrub** | `#D2B48C` (Tan/Light Brown) | Bare flat soil, open uncultivated plains, sheet soil |
| **7** | **Built-up / settlements** | `#FF0000` (Red) | Villages, towns, buildings, concrete roofs, paved roads |
| **8** | **Barren land / Rocky** | `#808080` (Grey) | Sheet rock, bare rocky outcrops, granite hills, quarries |

---

## 4. Sampling Best Practices for High Accuracy (>85%)

- **Minimum Sample Count:** Aim for at least 40–80 points per class across the study area (total 350–700 points).
- **Even Spatial Distribution:** Use the 2 km grid to ensure all sectors of the study area are represented.
- **Edge Avoidance:** Drop points inside homogeneous patches (at least 30 meters away from class boundaries) to avoid mixed-pixel contamination.
- **Built-up Details:** Include both rural hamlets/farmsteads and urban centers to capture diverse roofing types.

---

## 5. Exporting and Uploading to the Portal

1. When done digitizing, click **Toggle Editing** (`Ctrl+E`) and click **Save**.
2. Right-click the layer -> **Export -> Save Features As...**:
   - Format: **GeoJSON** or **Comma Separated Value [CSV]**.
   - CRS: **EPSG:4326 - WGS 84**.
3. Upload the exported file directly into **Step 4: Ground-Truth & Validation** in the Tamil Nadu LULC Portal.
4. The system will automatically perform a stratified 70% Training / 30% Independent Validation holdout split.
