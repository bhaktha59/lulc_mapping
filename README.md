# Land Use / Land Cover (LULC) Mapping System
### Multi-Area Remote Sensing & Machine Learning Classification Portal

Welcome to the **LULC Mapping Project**. This standalone enterprise application enables researchers, planners, and GIS specialists to perform land use / land cover classification for any study area (taluk, district, watershed, or forest division).

---

## 🏗️ Project Architecture

```
LULC_Mapping/
├── backend/                  # FastAPI & Google Earth Engine Pipeline (Port 8001)
│   ├── app.py                # REST API Endpoints for all 7 workflow steps
│   ├── config.py             # Official 8-class scheme, color palette, 14 feature bands
│   ├── requirements.txt      # Python dependencies
│   └── services/
│       ├── shapefile_service.py   # Zipped ESRI Shapefile extractor & UTM -> WGS 84 reprojector
│       ├── gee_pipeline.py        # Landsat surface reflectance compositing & index calculations
│       ├── sampling_service.py    # QGIS Starter Kit generator & 70/30 stratified sampling split
│       ├── classifier_service.py  # Random Forest 100-tree classifier & validation accuracy
│       └── export_service.py      # GeoTIFF, PNG/JPEG, CSV stats, and GeoJSON exporters
├── frontend/                 # Interactive React + Vite + Leaflet Web Application (Port 5174)
│   ├── package.json
│   ├── vite.config.js
│   ├── index.html
│   └── src/
│       ├── App.jsx           # 7-step guided workflow UI
│       ├── App.css           # Modern dark-mode styling
│       ├── index.css         # Theme tokens & Google fonts
│       ├── main.jsx
│       └── components/
│           └── MapViewer.jsx # Interactive Leaflet map with satellite basemap & GEE tile layers
├── qgis_tools/               # QGIS Starter Kit Assets & Documentation
│   ├── lulc_8class_style.qml           # Official Tamil Nadu 8-class QGIS symbology XML
│   ├── qgis_sample_collection_script.py# Automation script for QGIS Python Console
│   └── QGIS_GROUND_TRUTH_GUIDE.md      # Ground-truth digitization manual
├── package.json              # Root runner scripts (npm run dev, npm run backend)
└── README.md
```

---

## ⚡ Quick Start Guide (When opened in Antigravity)

### 1. Install Dependencies
Open a terminal in `LULC_Mapping`:
```powershell
# 1. Install frontend dependencies
npm run install:all

# 2. Install Python backend dependencies
cd backend
pip install -r requirements.txt
cd ..
```

### 2. Start Backend API Server
```powershell
npm run backend
```
*(Runs on Port 8001)*

### 3. Start Frontend Web Portal
```powershell
npm run dev
```
*(Runs on Port 5174: `http://localhost:5174`)*

---

## 🗺️ The 7-Step Workflow

1. **Project Setup**: Define study area name, Tamil Nadu district, and target year (2001–2025).
2. **Upload Boundary Shapefile**: Upload `.zip` containing `.shp`, `.shx`, `.dbf`, `.prj`. Automatic ellipsoidal reprojection from UTM Zone 44N to WGS 84.
3. **Satellite Band Preparation**: Acquire cloud-masked Landsat imagery and calculate 14 predictor bands (6 optical + 6 spectral indices + 2 topography).
4. **Ground-Truth & Validation (QGIS)**: Download tailored QGIS Starter Kit, digitize reference points, upload back, and auto-partition into 70% Training / 30% Independent Validation.
5. **Random Forest Classification**: Train a 100-tree Random Forest classifier on 14 bands with 70% training samples.
6. **Accuracy Assessment**: Evaluate against the independent 30% validation holdout. Overall Accuracy (OA), Cohen's Kappa, Producer's (PA), User's (UA), and 8x8 Confusion Matrix.
7. **LULC Map & GIS Export**: View thematic map, class-wise area statistics (ha, km², %), and export GeoTIFF (30 m), High-Res PNG/JPEG, and CSV tables.
