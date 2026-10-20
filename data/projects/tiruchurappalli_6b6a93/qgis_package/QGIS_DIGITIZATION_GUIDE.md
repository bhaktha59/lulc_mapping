# QGIS Ground-Truth Reference Point Digitization Guide
**Project:** Tiruchurappalli
**Study Area Area:** 453,439.42 ha (~4534.39 km²)
**Classification Scheme:** 9 Dynamic Classes (Configured for this Study Area)

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
| **1** | **Forest** | Reserve forests, hill canopy & dense woodland vegetation | Recommended target: 30+ points |
| **2** | **River** | Lakes, reservoirs, irrigation tanks & perennial streams | Recommended target: 20+ points |
| **3** | **Cropland** | Active agricultural plains, intensive crops, paddy & orchards | Recommended target: 50+ points |
| **4** | **Fallowland** | Temporarily uncropped agricultural arable plots & seasonal fallows | Recommended target: 30+ points |
| **5** | **Land with scrub** | Foothill thorn scrub, open bushland & degraded vegetation | Recommended target: 25+ points |
| **6** | **Land without scrub** | Open vacant ground, uncultivated sheet soil & open barren plain | Recommended target: 25+ points |
| **7** | **Built-up / settlements** | Towns, rural hamlets, residential buildings, roads & paved infrastructure | Recommended target: 40+ points |
| **8** | **Barren land / Rocky** | Exposed sheet rock, hill outcrops, dry boulder terrain & quarries | Recommended target: 20+ points |
| **9** | **Tanks** | Study area specific land cover class | Recommended target: 25+ points |

4. You can also specify `split` (`Training` or `Validation`) depending on whether the point is placed inside a Green (Non-Validation) or Orange (Validation) grid cell.

---

## 5. Saving and Uploading Back to Web Portal
1. Click **Save Layer Edits** (`Ctrl+S`) and toggle off editing mode (`Ctrl+E`).
2. The file is saved directly into `reference_points_template.geojson` (or export as GeoJSON/CSV).
3. Return to the Tamil Nadu LULC Web Portal and upload your file in **Step 4: Ground Truth & Validation**.

*(Note: When you export the classified GeoTIFF from the portal later, you can also apply `lulc_raster_symbology.qml` directly to the raster layer in QGIS for 1-click styling!)*
