import React, { useState, useEffect, useRef } from 'react';
import './App.css';
import MapViewer from './components/MapViewer.jsx';

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8001/api';

const TN_DISTRICTS = [
  'Ariyalur', 'Chengalpattu', 'Chennai', 'Coimbatore', 'Cuddalore', 'Dharmapuri',
  'Dindigul', 'Erode', 'Kallakurichi', 'Kanchipuram', 'Kanyakumari', 'Karur',
  'Krishnagiri', 'Madurai', 'Mayiladuthurai', 'Nagapattinam', 'Namakkal', 'Nilgiris',
  'Perambalur', 'Pudukkottai', 'Ramanathapuram', 'Ranipet', 'Salem', 'Sivaganga',
  'Tenkasi', 'Thanjavur', 'Theni', 'Thoothukudi', 'Tiruchirappalli', 'Tirunelveli',
  'Tirupathur', 'Tiruppur', 'Tiruvallur', 'Tiruvannamalai', 'Tiruvarur', 'Vellore',
  'Viluppuram', 'Virudhunagar'
];

const STEPS = [
  { id: 1, title: 'Project Setup', icon: '📁' },
  { id: 2, title: 'Upload Boundary', icon: '🗺️' },
  { id: 3, title: 'Band Preparation', icon: '🛰️' },
  { id: 4, title: 'Ground-Truth Samples', icon: '📍' },
  { id: 5, title: 'Classification', icon: '⚡' },
  { id: 6, title: 'Accuracy Assessment', icon: '📊' },
  { id: 7, title: 'LULC Map & Analytical Exports', icon: '💾' },
];

export const formatDatasetLabel = (datasetKey) => {
  if (!datasetKey) return 'Landsat 8 & 9 (30m)';
  if (datasetKey === 'landsat_8_9') return 'Landsat 8 & 9 (30m)';
  if (datasetKey === 'landsat_9') return 'Landsat 9 (30m)';
  if (datasetKey === 'landsat_8') return 'Landsat 8 (30m)';
  if (datasetKey === 'landsat_5_7') return 'Landsat 5 & 7 (30m)';
  if (datasetKey === 'sentinel_2') return 'Sentinel-2A & 2B (10m)';
  if (datasetKey === 'sentinel_2a') return 'Sentinel-2A (10m)';
  if (datasetKey === 'sentinel_2b') return 'Sentinel-2B (10m)';
  return datasetKey;
};

export const formatDatasetShortLabel = (datasetKey) => {
  if (!datasetKey) return 'Landsat 8 & 9';
  if (datasetKey === 'landsat_8_9') return 'Landsat 8 & 9';
  if (datasetKey === 'landsat_9') return 'Landsat 9';
  if (datasetKey === 'landsat_8') return 'Landsat 8';
  if (datasetKey === 'landsat_5_7') return 'Landsat 5 & 7';
  if (datasetKey === 'sentinel_2') return 'Sentinel-2';
  if (datasetKey === 'sentinel_2a') return 'Sentinel-2A';
  if (datasetKey === 'sentinel_2b') return 'Sentinel-2B';
  return datasetKey ? datasetKey.replace(/_/g, ' ') : 'Landsat';
};

export const getApplicableDatasets = (year) => {
  const y = year || 2025;
  if (y >= 2022) {
    return [
      { dataset: 'landsat_8_9', label: `${y} (Landsat 8 & 9 Combined - 30m)` },
      { dataset: 'sentinel_2', label: `${y} (Sentinel-2A & 2B Combined - 10m)` },
      { dataset: 'landsat_8', label: `${y} (Landsat 8 OLI - 30m)` },
      { dataset: 'landsat_9', label: `${y} (Landsat 9 OLI-2 - 30m)` },
      { dataset: 'sentinel_2a', label: `${y} (Sentinel-2A - 10m)` },
      { dataset: 'sentinel_2b', label: `${y} (Sentinel-2B - 10m)` },
    ];
  } else if (y >= 2017) {
    return [
      { dataset: 'landsat_8', label: `${y} (Landsat 8 OLI - 30m)` },
      { dataset: 'sentinel_2', label: `${y} (Sentinel-2A & 2B Combined - 10m)` },
      { dataset: 'sentinel_2a', label: `${y} (Sentinel-2A - 10m)` },
      { dataset: 'sentinel_2b', label: `${y} (Sentinel-2B - 10m)` },
    ];
  } else if (y >= 2015) {
    return [
      { dataset: 'landsat_8', label: `${y} (Landsat 8 OLI - 30m)` },
      { dataset: 'sentinel_2a', label: `${y} (Sentinel-2A - 10m)` },
    ];
  } else if (y >= 2013) {
    return [
      { dataset: 'landsat_8', label: `${y} (Landsat 8 OLI - 30m)` },
    ];
  } else {
    return [
      { dataset: 'landsat_5_7', label: `${y} (Landsat 5 & 7 Combined - 30m)` },
    ];
  }
};

export default function App() {
  // Theme state: defaults to 'light' mode
  const [theme, setTheme] = useState(() => localStorage.getItem('tn_lulc_theme') || 'light');

  const [projects, setProjects] = useState([]);
  const [currentProject, setCurrentProject] = useState(null);
  const [activeStep, setActiveStep] = useState(1);
  const [defaultLulcClasses, setDefaultLulcClasses] = useState({});
  const [projectClasses, setProjectClasses] = useState({});
  const [selectedAlgorithm, setSelectedAlgorithm] = useState('rf'); // 'rf' | 'svm'

  // Map state
  const [boundaryGeojson, setBoundaryGeojson] = useState(null);
  const [activeTileUrl, setActiveTileUrl] = useState(null);
  const [activeLayerName, setActiveLayerName] = useState('Study Area');
  const [layerOpacity, setLayerOpacity] = useState(0.9);
  const [trainingPoints, setTrainingPoints] = useState([]);
  const [validationPoints, setValidationPoints] = useState([]);
  const [showSamples, setShowSamples] = useState(true);

  // Loading & notification states
  const [loading, setLoading] = useState(false);
  const [statusMessage, setStatusMessage] = useState(null);
  const [backendStatus, setBackendStatus] = useState('checking'); // 'checking' | 'online' | 'offline'
  const [showNewProjectModal, setShowNewProjectModal] = useState(false);
  const [showClassesModal, setShowClassesModal] = useState(false);
  const [archivedProjects, setArchivedProjects] = useState([]);
  const [showProjectManagerModal, setShowProjectManagerModal] = useState(false);
  const [projectManagerTab, setProjectManagerTab] = useState('active'); // 'active' | 'archived'
  const [projectSearchTerm, setProjectSearchTerm] = useState('');
  const [deleteConfirmProject, setDeleteConfirmProject] = useState(null);
  const [deleteConfirmInput, setDeleteConfirmInput] = useState('');
  const [actionLoadingId, setActionLoadingId] = useState(null);

  // Step 1 Form State
  const [newProjName, setNewProjName] = useState('');
  const [newProjDistrict, setNewProjDistrict] = useState('Dharmapuri');
  const [newProjYear, setNewProjYear] = useState(2025);
  const [newProjDataset, setNewProjDataset] = useState('landsat_8_9');
  const [newProjDesc, setNewProjDesc] = useState('');

  // Class Management Editing State
  const [editingClasses, setEditingClasses] = useState({});

  // Step 3 State: Satellite bands & multi-sensor selection
  const [bandData, setBandData] = useState(null);
  const [activeDataset, setActiveDataset] = useState('landsat_8_9');
  const [selectedPreviewBand, setSelectedPreviewBand] = useState('tcc');
  const [availabilityInfo, setAvailabilityInfo] = useState(null);
  const [availabilityWarning, setAvailabilityWarning] = useState(null);
  const [checkingAvailability, setCheckingAvailability] = useState(false);

  // Step 4 State: Samples
  const [sampleSplitStats, setSampleSplitStats] = useState(null);

  // Step 5 & 6 & 7 State: Classification Results
  const [classificationResults, setClassificationResults] = useState(null);
  const [featureImportance, setFeatureImportance] = useState(null);
  const [loadingImportance, setLoadingImportance] = useState(false);
  const [showConfusionMatrix, setShowConfusionMatrix] = useState(false);

  // File Input Refs
  const shapefileInputRef = useRef(null);
  const samplesInputRef = useRef(null);

  // Sync theme attribute with document
  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('tn_lulc_theme', theme);
  }, [theme]);

  const toggleTheme = () => {
    setTheme((prev) => (prev === 'light' ? 'dark' : 'light'));
  };

  // Helper to format API errors clearly, especially network/backend offline errors
  const formatErrorMessage = (err, defaultPrefix = 'Operation failed') => {
    if (!err) return defaultPrefix;
    const msg = typeof err === 'string' ? err : err.message || '';
    if (
      msg.includes('Failed to fetch') ||
      msg.includes('NetworkError') ||
      err.name === 'TypeError'
    ) {
      return `${defaultPrefix}: Cannot connect to the FastAPI backend server at ${API_BASE}.\n\nPlease ensure the backend is running by opening a terminal and running:\n  npm run backend\n(or: python backend/app.py)`;
    }
    return `${defaultPrefix}: ${msg}`;
  };

  // Check Backend Connectivity Health
  const checkBackendHealth = async () => {
    try {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 3500);
      const res = await fetch(`${API_BASE}/health`, { signal: controller.signal });
      clearTimeout(timeoutId);
      if (res.ok) {
        setBackendStatus('online');
        return true;
      }
      setBackendStatus('offline');
      return false;
    } catch {
      setBackendStatus('offline');
      return false;
    }
  };

  // 1. Initial Load: Check Backend Health, Load Classes & Projects
  useEffect(() => {
    const init = async () => {
      const isOnline = await checkBackendHealth();
      if (isOnline) {
        fetch(`${API_BASE}/classes`)
          .then((r) => r.json())
          .then((data) => setDefaultLulcClasses(data.classes || {}))
          .catch(() => {});
        loadProjectsList();
      }
    };
    init();

    // Auto-reconnect poll: checks backend status every 5 seconds
    const interval = setInterval(async () => {
      const isOnline = await checkBackendHealth();
      if (isOnline && projects.length === 0) {
        fetch(`${API_BASE}/classes`)
          .then((r) => r.json())
          .then((data) => setDefaultLulcClasses(data.classes || {}))
          .catch(() => {});
        loadProjectsList();
      }
    }, 5000);

    return () => clearInterval(interval);
  }, [projects.length]);

  const loadProjectsList = async () => {
    try {
      const res = await fetch(`${API_BASE}/projects`);
      if (res.ok) {
        setBackendStatus('online');
        const data = await res.json();
        const activeList = data.active_projects || data.projects || [];
        const archivedList = data.archived_projects || [];
        setProjects(activeList);
        setArchivedProjects(archivedList);

        // Keep currentProject synchronized with active projects
        if (currentProject) {
          const stillActive = activeList.find((p) => p.id === currentProject.id);
          if (stillActive) {
            setCurrentProject((prev) => ({ ...prev, ...stillActive }));
          } else {
            // Project was archived or deleted: fallback to first available or reset
            if (activeList.length > 0) {
              selectProject(activeList[0]);
            } else {
              setCurrentProject(null);
              setActiveStep(1);
              setBoundaryGeojson(null);
              setActiveTileUrl(null);
              setBandData(null);
              setSampleSplitStats(null);
              setClassificationResults(null);
              setTrainingPoints([]);
              setValidationPoints([]);
            }
          }
        } else if (activeList.length > 0) {
          selectProject(activeList[0]);
        }
      } else {
        setBackendStatus('offline');
      }
    } catch (err) {
      console.log('Project fetch error:', err);
      setBackendStatus('offline');
    }
  };

  const selectProject = async (proj) => {
    setCurrentProject(proj);
    setActiveStep(proj.current_step || 1);
    setBoundaryGeojson(null);
    setActiveTileUrl(null);
    setBandData(null);
    setSampleSplitStats(null);
    setClassificationResults(null);
    setFeatureImportance(null);
    setShowConfusionMatrix(false);
    setTrainingPoints([]);
    setValidationPoints([]);
    setActiveDataset(proj.satellite_dataset || 'landsat_8_9');
    setAvailabilityWarning(null);
    setAvailabilityInfo(null);

    // Set classes for this project (from project metadata or default)
    const pClasses = proj.classes || defaultLulcClasses;
    setProjectClasses(pClasses);
    setEditingClasses(JSON.parse(JSON.stringify(pClasses)));

    // If project has boundary, load it
    if (proj.has_boundary) {
      try {
        const bRes = await fetch(`${API_BASE}/projects/${proj.id}/boundary`);
        if (bRes.ok) {
          const bGeo = await bRes.json();
          setBoundaryGeojson(bGeo);
        }
      } catch (e) {
        console.error('Error fetching boundary:', e);
      }
    }

    // If project has classification, load results
    if (proj.has_classification) {
      try {
        const cRes = await fetch(`${API_BASE}/projects/${proj.id}/results?year=${proj.target_year}`);
        if (cRes.ok) {
          const cData = await cRes.json();
          setClassificationResults(cData);
          setFeatureImportance(cData.feature_importance || null);
          setActiveTileUrl(cData.tile_url);
          const algoCode = (cData.algorithm || proj.selected_algorithm || 'RF').toUpperCase();
          setSelectedAlgorithm(algoCode.toLowerCase());
          setActiveLayerName(`LULC ${cData.year} (${algoCode}) Map`);
          if (cData.classes) {
            setProjectClasses(cData.classes);
          }
        }
      } catch (e) {
        console.error('Error fetching results:', e);
      }
    }
  };

  // Archive a completed or inactive study area project
  const handleArchiveProject = async (proj) => {
    if (!proj) return;
    setActionLoadingId(proj.id);
    try {
      const res = await fetch(`${API_BASE}/projects/${proj.id}/archive`, {
        method: 'POST',
      });
      if (res.ok) {
        setStatusMessage(`Project "${proj.name}" moved to archives.`);
        await loadProjectsList();
      } else {
        const err = await res.json();
        setStatusMessage(`Failed to archive: ${err.detail || 'Server error'}`);
      }
    } catch (e) {
      setStatusMessage(`Error archiving: ${e.message}`);
    } finally {
      setActionLoadingId(null);
    }
  };

  // Restore an archived project back to active selector
  const handleRestoreProject = async (proj) => {
    if (!proj) return;
    setActionLoadingId(proj.id);
    try {
      const res = await fetch(`${API_BASE}/projects/${proj.id}/restore`, {
        method: 'POST',
      });
      if (res.ok) {
        setStatusMessage(`Project "${proj.name}" restored to active list.`);
        await loadProjectsList();
      } else {
        const err = await res.json();
        setStatusMessage(`Failed to restore: ${err.detail || 'Server error'}`);
      }
    } catch (e) {
      setStatusMessage(`Error restoring: ${e.message}`);
    } finally {
      setActionLoadingId(null);
    }
  };

  // Permanently delete a project and all its files from disk after explicit confirmation
  const handleConfirmPermanentDelete = async () => {
    if (!deleteConfirmProject) return;
    const projId = deleteConfirmProject.id;
    const projName = deleteConfirmProject.name;
    setActionLoadingId(projId);
    try {
      const res = await fetch(`${API_BASE}/projects/${projId}`, {
        method: 'DELETE',
      });
      if (res.ok) {
        setStatusMessage(`Project "${projName}" and all associated files permanently deleted.`);
        setDeleteConfirmProject(null);
        setDeleteConfirmInput('');
        await loadProjectsList();
      } else {
        const err = await res.json();
        setStatusMessage(`Failed to delete: ${err.detail || 'Server error'}`);
      }
    } catch (e) {
      setStatusMessage(`Error deleting project: ${e.message}`);
    } finally {
      setActionLoadingId(null);
    }
  };

  // Switch or reload results for a specific algorithm (RF or SVM)
  const handleSwitchAlgorithm = async (newAlgo) => {
    const targetAlgo = (newAlgo || 'rf').toLowerCase();
    setSelectedAlgorithm(targetAlgo);
    if (!currentProject || !currentProject.has_classification) return;

    try {
      const res = await fetch(`${API_BASE}/projects/${currentProject.id}/results?year=${currentProject.target_year}&algorithm=${targetAlgo}`);
      if (res.ok) {
        const data = await res.json();
        setClassificationResults(data);
        setFeatureImportance(data.feature_importance || null);
        setActiveTileUrl(data.tile_url);
        const algoCode = (data.algorithm || targetAlgo).toUpperCase();
        setActiveLayerName(`LULC ${data.year} (${algoCode}) Map`);
        if (data.classes) setProjectClasses(data.classes);
        setStatusMessage(`Active algorithm switched to ${data.algorithm_name || algoCode}.`);
      }
    } catch (e) {
      console.log('No existing classification results for algorithm:', targetAlgo, e);
    }
  };

  const handleFetchFeatureImportance = async () => {
    if (!currentProject) return;
    setLoadingImportance(true);
    setStatusMessage('Evaluating Random Forest feature importance (Gini Impurity Decrease) across 14 predictors in GEE...');
    try {
      const res = await fetch(`${API_BASE}/projects/${currentProject.id}/feature-importance?year=${currentProject.target_year}`);
      const data = await res.json();
      if (res.ok) {
        setFeatureImportance(data);
        setStatusMessage(`Random Forest feature importance evaluated: Top predictor is ${data.ranked_features?.[0]?.feature} (${data.ranked_features?.[0]?.relative_importance_pct}%).`);
      } else {
        alert(data.detail || 'Feature importance could not be evaluated.');
      }
    } catch (e) {
      alert(`Error evaluating feature importance: ${e.message}`);
    } finally {
      setLoadingImportance(false);
    }
  };

  // =========================================================================
  // STEP 1: CREATE PROJECT
  // =========================================================================
  const handleCreateProject = async (e) => {
    e.preventDefault();
    if (!newProjName.trim()) return;

    setLoading(true);
    setStatusMessage('Setting up new study area project...');
    try {
      const res = await fetch(`${API_BASE}/projects/create`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: newProjName,
          district: newProjDistrict,
          target_year: newProjYear,
          satellite_dataset: newProjDataset,
          description: newProjDesc,
        }),
      });
      const data = await res.json();
      if (res.ok) {
        setShowNewProjectModal(false);
        setNewProjName('');
        await loadProjectsList();
        selectProject(data.project);
        setStatusMessage(`Project "${data.project.name}" created successfully!`);
      } else {
        alert(data.detail || 'Error creating project');
      }
    } catch (err) {
      alert(formatErrorMessage(err, 'Error creating project'));
    } finally {
      setLoading(false);
    }
  };

  // Save Project Classes Configuration
  const handleSaveClassesConfig = async () => {
    if (!currentProject) return;
    setLoading(true);
    setStatusMessage('Updating study area classification classes & sampling targets...');
    try {
      const res = await fetch(`${API_BASE}/projects/${currentProject.id}/classes`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ classes: editingClasses }),
      });
      const data = await res.json();
      if (res.ok) {
        setProjectClasses(data.classes);
        setCurrentProject((prev) => ({ ...prev, classes: data.classes }));
        setShowClassesModal(false);
        setStatusMessage('Study area LULC classes successfully updated!');
      } else {
        alert(data.detail || 'Failed to update classes.');
      }
    } catch (err) {
      alert(formatErrorMessage(err, 'Error saving classes'));
    } finally {
      setLoading(false);
    }
  };

  const handleResetToDefaultClasses = () => {
    setEditingClasses(JSON.parse(JSON.stringify(defaultLulcClasses)));
  };

  const handleAddClass = () => {
    const existingIds = Object.keys(editingClasses).map(Number);
    const nextId = existingIds.length > 0 ? Math.max(...existingIds) + 1 : 1;
    const newClass = {
      id: nextId,
      name: `Custom Class ${nextId}`,
      color: '#06b6d4',
      desc: 'Study area specific land cover class',
      min_samples: 25,
    };
    setEditingClasses((prev) => ({
      ...prev,
      [String(nextId)]: newClass,
    }));
  };

  const handleRemoveClass = (cid) => {
    if (Object.keys(editingClasses).length <= 2) {
      alert('A classification requires at least 2 classes.');
      return;
    }
    setEditingClasses((prev) => {
      const copy = { ...prev };
      delete copy[String(cid)];
      delete copy[Number(cid)];
      return copy;
    });
  };

  // =========================================================================
  // STEP 2: UPLOAD SHAPEFILE (with ZIP & nested directory support)
  // =========================================================================
  const handleShapefileUpload = async (e) => {
    const file = e.target.files?.[0];
    if (!file || !currentProject) return;

    if (!file.name.toLowerCase().endsWith('.zip')) {
      alert('Please upload a .zip archive containing the ESRI Shapefile components (.shp, .shx, .dbf, .prj).');
      return;
    }

    setLoading(true);
    setStatusMessage('Extracting shapefile, verifying required components (.shp, .shx, .dbf), and parsing geometry...');

    try {
      const res = await fetch(`${API_BASE}/projects/${currentProject.id}/upload-boundary`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/octet-stream',
          'X-Filename': file.name,
        },
        body: file,
      });
      const data = await res.json();

      if (res.ok) {
        setBoundaryGeojson(data.boundary_geojson);
        setCurrentProject((prev) => ({
          ...prev,
          has_boundary: true,
          area_ha: data.area_ha,
          area_sqkm: data.area_sqkm,
          bounds: data.bounds,
          current_step: Math.max(prev.current_step || 1, 2),
        }));
        setStatusMessage(
          `Shapefile '${data.shapefile_name || 'boundary'}' successfully processed! Area: ${Number(data.area_ha).toLocaleString()} ha (${data.area_sqkm} km²). Boundary displayed on map.`
        );
        setActiveStep(2);
      } else {
        alert(data.detail || 'Failed to process shapefile.');
      }
    } catch (err) {
      alert(formatErrorMessage(err, 'Shapefile upload failed'));
    } finally {
      setLoading(false);
      if (shapefileInputRef.current) shapefileInputRef.current.value = '';
    }
  };

  // =========================================================================
  // STEP 3: PREPARE SATELLITE BANDS & MULTI-SENSOR COMPOSITING
  // =========================================================================
  const handleCheckAvailability = async (datasetToTest) => {
    if (!currentProject || !currentProject.has_boundary) return;
    const datasetKey = datasetToTest || activeDataset || currentProject.satellite_dataset || 'landsat_8_9';
    setCheckingAvailability(true);
    setAvailabilityWarning(null);
    try {
      const res = await fetch(`${API_BASE}/projects/${currentProject.id}/satellite-availability?year=${currentProject.target_year}&dataset=${datasetKey}`);
      const data = await res.json();
      if (res.ok) {
        setAvailabilityInfo(data);
        if (!data.available || data.scenes_count === 0) {
          setAvailabilityWarning(data.message || `No suitable imagery scenes found for ${data.sensor} in ${data.year}.`);
        } else {
          setAvailabilityWarning(null);
        }
      } else {
        setAvailabilityWarning(data.detail || 'Unable to verify satellite imagery availability.');
      }
    } catch (err) {
      console.error('Availability check error:', err);
    } finally {
      setCheckingAvailability(false);
    }
  };

  const handlePrepareBands = async (overrideDataset) => {
    if (!currentProject) return;
    const datasetToUse = overrideDataset || activeDataset || currentProject.satellite_dataset || 'landsat_8_9';
    setLoading(true);
    setAvailabilityWarning(null);
    setStatusMessage(`Acquiring ${formatDatasetLabel(datasetToUse)} Surface Reflectance, applying cloud/shadow bitmasking, and compositing spectral indices in GEE...`);

    try {
      const res = await fetch(`${API_BASE}/projects/${currentProject.id}/bands?year=${currentProject.target_year}&dataset=${datasetToUse}`);
      const data = await res.json();

      if (res.ok) {
        setBandData(data);
        setActiveDataset(data.dataset || datasetToUse);
        setCurrentProject((prev) => ({
          ...prev,
          satellite_dataset: data.dataset || datasetToUse,
          current_step: Math.max(prev.current_step || 1, 3),
        }));
        setActiveTileUrl(data.tile_layers.tcc);
        setActiveLayerName(`${data.sensor || 'Satellite'} True Color (TCC) - ${data.year}`);
        setStatusMessage(`14 predictor bands acquired! Sensor: ${data.sensor} (${data.scenes_count} scenes composited at ${data.native_resolution || '30m'} native resolution).`);
      } else {
        const errorMsg = data.detail || 'Band preparation failed.';
        setAvailabilityWarning(errorMsg);
        setStatusMessage(`Warning: ${errorMsg}`);
      }
    } catch (err) {
      const formatted = formatErrorMessage(err, 'Error acquiring satellite bands');
      setAvailabilityWarning(formatted);
      alert(formatted);
    } finally {
      setLoading(false);
    }
  };

  const switchPreviewLayer = (layerKey, label) => {
    if (!bandData || !bandData.tile_layers[layerKey]) return;
    setSelectedPreviewBand(layerKey);
    setActiveTileUrl(bandData.tile_layers[layerKey]);
    setActiveLayerName(`${label} (${bandData.year})`);
  };

  // =========================================================================
  // ROBUST FILE DOWNLOAD HELPERS (Guaranteed to add directly to browser downloads)
  // =========================================================================
  const saveBlobToDisk = (blob, filename) => {
    const blobUrl = window.URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.style.display = 'none';
    link.href = blobUrl;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    setTimeout(() => {
      document.body.removeChild(link);
      window.URL.revokeObjectURL(blobUrl);
    }, 1500);
  };

  const triggerFileDownload = async (url, defaultFilename, statusPrefix = 'Downloading') => {
    setLoading(true);
    setStatusMessage(`${statusPrefix} "${defaultFilename}"...`);
    try {
      const res = await fetch(url);
      if (!res.ok) {
        let errDetail = 'Download request failed';
        try {
          const errData = await res.json();
          errDetail = errData.detail || errData.message || errDetail;
        } catch {}
        throw new Error(errDetail);
      }

      // Check if server returned a JSON fallback with download_url or image_url
      const contentType = res.headers.get('content-type') || '';
      if (contentType.includes('application/json')) {
        const data = await res.json();
        if (data.download_url) {
          setStatusMessage(`Fetching file payload for "${data.filename || defaultFilename}"...`);
          const fileRes = await fetch(data.download_url);
          const blob = await fileRes.blob();
          saveBlobToDisk(blob, data.filename || defaultFilename);
          setStatusMessage(`✓ Added "${data.filename || defaultFilename}" to downloads.`);
          return;
        } else if (data.image_url) {
          setStatusMessage(`Fetching image payload for "${data.filename || defaultFilename}"...`);
          const imgRes = await fetch(data.image_url);
          const blob = await imgRes.blob();
          saveBlobToDisk(blob, data.filename || defaultFilename);
          setStatusMessage(`✓ Added "${data.filename || defaultFilename}" to downloads.`);
          return;
        }
      }

      // Direct binary response (FileResponse, CSV, GeoJSON, etc.)
      const blob = await res.blob();
      const disposition = res.headers.get('Content-Disposition') || '';
      let filename = defaultFilename;
      const match = disposition.match(/filename=["']?([^"';]+)["']?/);
      if (match && match[1]) {
        filename = match[1].trim();
      }

      saveBlobToDisk(blob, filename);
      setStatusMessage(`✓ Added "${filename}" to downloads.`);
    } catch (err) {
      alert(formatErrorMessage(err, `Error downloading ${defaultFilename}`));
      setStatusMessage(`Download failed for ${defaultFilename}.`);
    } finally {
      setLoading(false);
    }
  };

  // =========================================================================
  // STEP 4: QGIS KIT & REFERENCE SAMPLE UPLOAD
  // =========================================================================
  const handleDownloadQgisKit = () => {
    if (!currentProject) return;
    const defaultName = `${currentProject.name}_QGIS_Starter_Kit.zip`;
    triggerFileDownload(
      `${API_BASE}/projects/${currentProject.id}/qgis-kit`,
      defaultName,
      'Preparing and downloading QGIS Starter Kit'
    );
  };

  const handleSamplesUpload = async (e) => {
    const file = e.target.files?.[0];
    if (!file || !currentProject) return;

    setLoading(true);
    setStatusMessage('Parsing reference points against study area classes and executing 70/30 stratified holdout split...');

    try {
      const res = await fetch(`${API_BASE}/projects/${currentProject.id}/upload-samples`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/octet-stream',
          'X-Filename': file.name,
        },
        body: file,
      });
      const data = await res.json();

      if (res.ok) {
        setSampleSplitStats(data);
        setStatusMessage(data.message);

        // Update confirmed classes
        if (data.confirmed_classes) {
          setProjectClasses(data.confirmed_classes);
          setEditingClasses(JSON.parse(JSON.stringify(data.confirmed_classes)));
        }

        // Refresh local project state
        setCurrentProject((prev) => ({
          ...prev,
          has_samples: true,
          total_samples: data.total_points,
          training_samples_count: data.training_count,
          validation_samples_count: data.validation_count,
          classes: data.confirmed_classes || prev.classes,
          current_step: Math.max(prev.current_step || 1, 4),
        }));
      } else {
        alert(data.detail || 'Sample upload failed.');
      }
    } catch (err) {
      alert(formatErrorMessage(err, 'Error uploading samples'));
    } finally {
      setLoading(false);
      if (samplesInputRef.current) samplesInputRef.current.value = '';
    }
  };

  // =========================================================================
  // STEP 5: RUN CLASSIFICATION (RANDOM FOREST OR SVM) & VALIDATION
  // =========================================================================
  const handleRunClassification = async (algoOverride) => {
    if (!currentProject) return;
    const algo = (algoOverride || selectedAlgorithm || 'rf').toLowerCase();
    const algoDisplayName = algo === 'svm' ? 'Support Vector Machine (SVM)' : 'Random Forest (RF)';
    setLoading(true);
    setStatusMessage(`Executing ${algoDisplayName} classification on 14 predictor bands and running independent holdout validation assessment...`);

    try {
      const dsKey = activeDataset || currentProject.satellite_dataset || 'landsat_8_9';
      const res = await fetch(`${API_BASE}/projects/${currentProject.id}/train-and-classify?year=${currentProject.target_year}&algorithm=${algo}&dataset=${dsKey}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          year: currentProject.target_year,
          algorithm: algo,
          dataset: dsKey,
        }),
      });
      const data = await res.json();

      if (res.ok) {
        setClassificationResults(data);
        setFeatureImportance(data.feature_importance || null);
        const resolvedAlgo = (data.algorithm || algo).toLowerCase();
        setSelectedAlgorithm(resolvedAlgo);
        setActiveTileUrl(data.tile_url);
        setActiveLayerName(`LULC ${data.year} (${(data.algorithm || algo).toUpperCase()}) Map`);
        setActiveStep(6);
        if (data.classes) {
          setProjectClasses(data.classes);
        }
        setStatusMessage(`${data.algorithm_name || algoDisplayName} Classification & Accuracy Assessment completed! OA: ${data.accuracy.overall_accuracy}%, Kappa: ${data.accuracy.kappa_coefficient}.`);
      } else {
        alert(data.detail || 'Classification failed.');
      }
    } catch (err) {
      alert(formatErrorMessage(err, 'Error running classification'));
    } finally {
      setLoading(false);
    }
  };

  // =========================================================================
  // STEP 7: DIRECT DOWNLOAD HANDLERS (Pop-up safe, adds directly to browser download center)
  // =========================================================================
  const triggerExport = (endpoint, queryParam = '') => {
    if (!currentProject) return;
    const url = `${API_BASE}/projects/${currentProject.id}/export/${endpoint}${queryParam}`;
    triggerFileDownload(url, `${currentProject.name}_${endpoint}.csv`, 'Exporting data');
  };

  const handleDownloadGeoTIFF = () => {
    if (!currentProject) return;
    const algo = (classificationResults?.algorithm || selectedAlgorithm || 'rf').toLowerCase();
    const defaultName = `${currentProject.name}_LULC_${currentProject.target_year}_${algo}.tif`;
    triggerFileDownload(
      `${API_BASE}/projects/${currentProject.id}/export/geotiff?year=${currentProject.target_year}&algorithm=${algo}&download=true`,
      defaultName,
      `Generating and downloading 30 m GeoTIFF (${algo.toUpperCase()})`
    );
  };

  const handleDownloadImage = (format = 'png') => {
    if (!currentProject) return;
    const ext = format.toLowerCase() === 'jpg' ? 'jpg' : 'png';
    const algo = (classificationResults?.algorithm || selectedAlgorithm || 'rf').toLowerCase();
    const defaultName = `${currentProject.name}_LULC_${currentProject.target_year}_${algo}.${ext}`;
    triggerFileDownload(
      `${API_BASE}/projects/${currentProject.id}/export/image?year=${currentProject.target_year}&algorithm=${algo}&format=${ext}&download=true`,
      defaultName,
      `Rendering and downloading ${ext.toUpperCase()} map image (${algo.toUpperCase()})`
    );
  };

  const handleDownloadStatsCsv = () => {
    if (!currentProject) return;
    const defaultName = `${currentProject.name}_LULC_Area_Stats_${currentProject.target_year}.csv`;
    triggerFileDownload(
      `${API_BASE}/projects/${currentProject.id}/export/csv?year=${currentProject.target_year}`,
      defaultName,
      'Exporting Class Area Statistics CSV'
    );
  };

  const handleDownloadAccuracyCsv = () => {
    if (!currentProject) return;
    const defaultName = `${currentProject.name}_Accuracy_Report_${currentProject.target_year}.csv`;
    triggerFileDownload(
      `${API_BASE}/projects/${currentProject.id}/export/accuracy-csv?year=${currentProject.target_year}`,
      defaultName,
      'Exporting Accuracy Assessment Report CSV'
    );
  };

  const handleDownloadSamples = (split = 'all', format = 'geojson') => {
    if (!currentProject) return;
    const ext = format === 'csv' ? 'csv' : 'geojson';
    const label = split === 'training' ? 'Training' : split === 'validation' ? 'Validation' : 'GroundTruth';
    const defaultName = `${currentProject.name}_${label}_Samples.${ext}`;
    triggerFileDownload(
      `${API_BASE}/projects/${currentProject.id}/export/samples?split=${split}&format=${format}`,
      defaultName,
      `Exporting ${label} samples (${ext.toUpperCase()})`
    );
  };

  const handleDownloadBoundary = () => {
    if (!currentProject) return;
    const defaultName = `${currentProject.name}_Study_Area_Boundary.geojson`;
    triggerFileDownload(
      `${API_BASE}/projects/${currentProject.id}/export/boundary`,
      defaultName,
      'Exporting Study Area Boundary GeoJSON'
    );
  };

  const handleDownloadQmlStyle = (styleType = 'raster') => {
    if (!currentProject) return;
    const defaultName = `${currentProject.name}_${styleType === 'raster' ? 'Raster' : 'Vector'}_Symbology.qml`;
    triggerFileDownload(
      `${API_BASE}/projects/${currentProject.id}/export/qml?style_type=${styleType}`,
      defaultName,
      `Exporting QGIS ${styleType} symbology (.qml)`
    );
  };

  const handleDownloadCompleteBundle = () => {
    if (!currentProject) return;
    const defaultName = `${currentProject.name}_Complete_LULC_Package_${currentProject.target_year}.zip`;
    triggerFileDownload(
      `${API_BASE}/projects/${currentProject.id}/export/bundle?year=${currentProject.target_year}`,
      defaultName,
      'Assembling Complete All-In-One GIS & Analytical Archive'
    );
  };

  // Determine current active classes for dynamic legend
  const activeLulcClasses = classificationResults?.classes || projectClasses || defaultLulcClasses;
  const activeClassesList = Object.entries(activeLulcClasses).sort((a, b) => Number(a[0]) - Number(b[0]));

  // Check if ground truth samples have been confirmed
  const areSamplesConfirmed = Boolean(
    currentProject?.has_samples || sampleSplitStats || classificationResults
  );

  return (
    <div className="app-container" data-theme={theme}>
      {/* 1. Header */}
      <header className="app-header">
        <div className="brand-section">
          <div className="brand-icon">🗺️</div>
          <div>
            <h1 className="brand-title">LULC Mapping</h1>
            <p className="brand-subtitle">Automated Remote Sensing & Supervised Classification Portal</p>
          </div>
        </div>

        {/* Central Information Section: Project, District, Year, Sensor, API Status */}
        <div className="header-center-info">
          {/* 1. Project */}
          <div
            className={`header-card ${currentProject ? 'active-project' : ''}`}
            title={currentProject ? `Study Area Project: ${currentProject.name}` : 'No active project selected'}
          >
            <span className="header-card-icon">📌</span>
            <div className="header-card-content">
              <span className="header-card-label">Project</span>
              <span className="header-card-value project-name">
                {currentProject?.name || 'None Selected'}
              </span>
            </div>
          </div>

          {/* 2. District */}
          <div
            className="header-card"
            title={currentProject ? `District: ${currentProject.district || 'General'}` : 'District'}
          >
            <span className="header-card-icon">🏛️</span>
            <div className="header-card-content">
              <span className="header-card-label">District</span>
              <span className="header-card-value district-name">
                {currentProject ? (currentProject.district || 'General') : '—'}
              </span>
            </div>
          </div>

          {/* 3. Year */}
          <div
            className="header-card"
            title={currentProject ? `Target Study Year: ${currentProject.target_year}` : 'Study Year'}
          >
            <span className="header-card-icon">📅</span>
            <div className="header-card-content">
              <span className="header-card-label">Year</span>
              <span className="header-card-value">
                {currentProject?.target_year || '—'}
              </span>
            </div>
          </div>

          {/* 4. Sensor */}
          <div
            className="header-card"
            title={currentProject ? `Satellite Sensor: ${formatDatasetLabel(currentProject.satellite_dataset)}` : 'Satellite Sensor'}
          >
            <span className="header-card-icon">🛰️</span>
            <div className="header-card-content">
              <span className="header-card-label">Sensor</span>
              <span className="header-card-value sensor-name">
                {currentProject ? formatDatasetShortLabel(currentProject.satellite_dataset) : '—'}
              </span>
            </div>
          </div>

          {/* 5. Dedicated API Status Indicator Container */}
          <div
            className={`api-status-container ${backendStatus}`}
            onClick={async () => {
              setStatusMessage('Checking backend server connection (Port 8001)...');
              const ok = await checkBackendHealth();
              if (ok) {
                await loadProjectsList();
                setStatusMessage('Connected to FastAPI backend on port 8001!');
              } else {
                setStatusMessage('Backend offline: Port 8001 not responding. Please run "npm run backend".');
              }
            }}
            title={
              backendStatus === 'online'
                ? 'API Online: FastAPI Backend connected on port 8001 (Click to re-verify)'
                : backendStatus === 'offline'
                ? 'API Offline: Cannot reach backend on port 8001 (Click to retry connection)'
                : 'API Status: Connecting to backend...'
            }
            role="button"
            tabIndex={0}
            aria-label={backendStatus === 'online' ? 'API Online' : 'API Offline'}
          >
            <span
              className={`status-pulse-dot ${
                backendStatus === 'online' ? 'green' : backendStatus === 'offline' ? 'red' : 'amber'
              }`}
            />
          </div>

          {/* 6. Theme Toggle: Icon-only Button */}
          <button
            type="button"
            className="theme-toggle-btn icon-only"
            onClick={toggleTheme}
            title={
              theme === 'light'
                ? 'Light Mode active · Click to switch to Dark Mode'
                : 'Dark Mode active · Click to switch to Light Mode'
            }
            aria-label={
              theme === 'light'
                ? 'Current theme: Light Mode. Switch to Dark Mode'
                : 'Current theme: Dark Mode. Switch to Light Mode'
            }
          >
            <span style={{ fontSize: '15px', lineHeight: 1 }}>{theme === 'light' ? '☀️' : '🌙'}</span>
          </button>
        </div>

        {/* Header Actions: Study Area Selector, Manage Button, Add Project Button */}
        <div className="header-actions">
          {/* Study Area Selector with integrated Manage option */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <select
              className="form-select"
              style={{ width: 'auto', minWidth: '150px', maxWidth: '210px', padding: '6px 26px 6px 10px', fontSize: '12px' }}
              value={currentProject?.id || ''}
              onChange={(e) => {
                if (e.target.value === '__manage__') {
                  setShowProjectManagerModal(true);
                  return;
                }
                const found = projects.find((p) => p.id === e.target.value);
                if (found) selectProject(found);
              }}
              title="Select Active Study Area Project"
            >
              {projects.length === 0 && <option value="">No Active Projects</option>}
              {projects.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.name} ({p.district || 'General'}) - {p.target_year}
                </option>
              ))}
              <option disabled>───────────────</option>
              <option value="__manage__">📁 Manage Projects...</option>
            </select>

            {/* Manage Projects Button */}
            <button
              className="btn-manage-projects"
              onClick={() => setShowProjectManagerModal(true)}
              title="Manage & Archive Study Area Projects"
            >
              <span>📁</span> Manage
            </button>
          </div>

          {/* Simplified "+ Add Project" Button */}
          <button
            type="button"
            className="btn-add-project"
            onClick={() => setShowNewProjectModal(true)}
            title="Create a new study area project"
          >
            <span className="plus-icon">+</span>
            <span>Add Project</span>
          </button>
        </div>
      </header>

      {/* Backend Offline Alert Banner */}
      {backendStatus === 'offline' && (
        <div className="backend-offline-banner">
          <div className="banner-left">
            <span className="banner-icon">⚠️</span>
            <div>
              <div className="banner-title">FastAPI Backend Server is Offline (Port 8001)</div>
              <div className="banner-desc">
                Cannot reach <code>{API_BASE}</code>. Open a terminal in <code>c:\LULC_Mapping</code> and run <code>npm run backend</code> (or <code>python backend/app.py</code>) to enable project creation, GEE satellite compositing, and machine learning.
              </div>
            </div>
          </div>
          <button
            className="btn-retry"
            onClick={async () => {
              const ok = await checkBackendHealth();
              if (ok) loadProjectsList();
            }}
          >
            🔄 Retry Connection
          </button>
        </div>
      )}

      {/* 2. Step Workflow Bar (Responsive & Aligned) */}
      <nav className="workflow-stepper" aria-label="Workflow Navigation">
        {STEPS.map((step, idx) => {
          const isCompleted = currentProject && currentProject.current_step > step.id;
          const isActive = activeStep === step.id;
          const stepTitle = step.id === 5
            ? (selectedAlgorithm === 'svm' ? 'SVM Classification' : 'RF Classification')
            : step.title;
          const stepIcon = step.id === 5
            ? (selectedAlgorithm === 'svm' ? '⚡' : '🌲')
            : step.icon;
          return (
            <React.Fragment key={step.id}>
              <button
                className={`step-item ${isActive ? 'active' : ''} ${isCompleted ? 'completed' : ''}`}
                onClick={() => setActiveStep(step.id)}
                title={`Step ${step.id}: ${stepTitle}`}
              >
                <div className="step-badge">{isCompleted ? '✓' : step.id}</div>
                <span>{stepIcon} {stepTitle}</span>
              </button>
              {idx < STEPS.length - 1 && <span className="step-arrow">›</span>}
            </React.Fragment>
          );
        })}
      </nav>

      {/* Status Bar / Spinner */}
      {statusMessage && (
        <div style={{
          background: theme === 'light' ? 'rgba(16, 185, 129, 0.1)' : 'rgba(16, 185, 129, 0.15)',
          borderBottom: '1px solid rgba(16, 185, 129, 0.25)',
          padding: '6px 20px',
          fontSize: '12px',
          color: theme === 'light' ? '#065f46' : '#34d399',
          display: 'flex',
          alignItems: 'center',
          gap: '10px',
          fontWeight: 500,
        }}>
          {loading && <div className="spinner" style={{ width: 14, height: 14 }} />}
          <span>{statusMessage}</span>
        </div>
      )}

      {/* 3. Main Workspace */}
      <div className="app-body">
        {/* Left Control Panel */}
        <aside className="sidebar-panel">
          {/* STEP 1: PROJECT SETUP */}
          {activeStep === 1 && (
            <div className="card">
              <h2 className="card-title">📁 Step 1: Study Area Project Setup</h2>
              <p className="card-desc">
                Define a dedicated, isolated project for your selected study area.
                LULC classes and ground-truth sampling requirements can be tailored specifically to your study area.
              </p>

              {currentProject ? (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
                  <div className="stat-grid">
                    <div className="stat-box">
                      <span className="stat-label">Project Name</span>
                      <span className="stat-val" style={{ fontSize: 14 }}>{currentProject.name}</span>
                    </div>
                    <div className="stat-box">
                      <span className="stat-label">District</span>
                      <span className="stat-val" style={{ fontSize: 14 }}>{currentProject.district}</span>
                    </div>
                    <div className="stat-box">
                      <span className="stat-label">Target Year &amp; Sensor</span>
                      <span className="stat-val" style={{ fontSize: 13, color: 'var(--accent-blue)' }}>
                        {currentProject.target_year} ({formatDatasetLabel(currentProject.satellite_dataset)})
                      </span>
                    </div>
                    <div className="stat-box">
                      <span className="stat-label">Boundary Status</span>
                      <span className="stat-val" style={{ color: currentProject.has_boundary ? '#059669' : '#d97706', fontSize: 13 }}>
                        {currentProject.has_boundary ? 'Uploaded ✓' : 'Pending ⏳'}
                      </span>
                    </div>
                  </div>

                  {/* Study Area Class Configuration Box */}
                  <div style={{
                    background: 'var(--bg-card-secondary)',
                    border: '1px solid var(--border-subtle)',
                    borderRadius: 10,
                    padding: 14,
                    display: 'flex',
                    flexDirection: 'column',
                    gap: 10
                  }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <span style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-main)' }}>
                        🏷️ Study Area Classes ({activeClassesList.length})
                      </span>
                      <button
                        className="btn-secondary"
                        style={{ padding: '4px 10px', fontSize: '11.5px' }}
                        onClick={() => setShowClassesModal(true)}
                      >
                        ⚙️ Configure Classes
                      </button>
                    </div>
                    <p style={{ fontSize: 11.5, color: 'var(--text-muted)', margin: 0 }}>
                      Sampling targets vary by landscape. Review and adapt the classes and minimum samples required for this study area.
                    </p>
                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                      {activeClassesList.map(([cid, cinfo]) => (
                        <div
                          key={cid}
                          style={{
                            display: 'flex',
                            alignItems: 'center',
                            gap: 5,
                            background: 'var(--bg-card)',
                            border: '1px solid var(--border-subtle)',
                            padding: '3px 8px',
                            borderRadius: 14,
                            fontSize: '11px',
                          }}
                        >
                          <span className="color-dot" style={{ background: cinfo.color, margin: 0 }} />
                          <span style={{ fontWeight: 500 }}>{cinfo.name}</span>
                          <span style={{ color: 'var(--text-dim)', fontSize: 10 }}>({cinfo.min_samples || 20}+)</span>
                        </div>
                      ))}
                    </div>
                  </div>

                  <button
                    className="btn-primary"
                    onClick={() => setActiveStep(2)}
                  >
                    Proceed to Step 2: Upload Shapefile ➔
                  </button>
                </div>
              ) : (
                <div style={{ textAlign: 'center', padding: '20px 0' }}>
                  <p style={{ color: 'var(--text-muted)', fontSize: 13, marginBottom: 14 }}>
                    No project selected. Create your first study area to begin.
                  </p>
                  <button
                    className="btn-primary"
                    style={{ margin: '0 auto' }}
                    onClick={() => setShowNewProjectModal(true)}
                  >
                    ➕ Create Study Area Project
                  </button>
                </div>
              )}
            </div>
          )}

          {/* STEP 2: UPLOAD SHAPEFILE */}
          {activeStep === 2 && (
            <div className="card">
              <h2 className="card-title">🗺️ Step 2: Upload Study Area Shapefile</h2>
              <p className="card-desc">
                Upload your study area boundary as an ESRI Shapefile ZIP archive.
                The ZIP archive can contain files in the root or inside nested subfolders.
                Required components: <code>.shp</code>, <code>.shx</code>, <code>.dbf</code>, and optionally <code>.prj</code>.
              </p>

              <input
                ref={shapefileInputRef}
                type="file"
                accept=".zip"
                style={{ display: 'none' }}
                onChange={handleShapefileUpload}
              />

              <div
                className="dropzone"
                onClick={() => shapefileInputRef.current?.click()}
              >
                <div className="dropzone-icon">📁</div>
                <div className="dropzone-text">Click or Drag & Drop Shapefile ZIP</div>
                <div className="dropzone-subtext">
                  Must contain .shp, .shx, and .dbf files (nested folders supported)
                </div>
              </div>

              {currentProject?.has_boundary && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                  <div className="stat-grid">
                    <div className="stat-box">
                      <span className="stat-label">Total Area (ha)</span>
                      <span className="stat-val" style={{ color: '#059669' }}>
                        {Number(currentProject.area_ha || 0).toLocaleString()} ha
                      </span>
                    </div>
                    <div className="stat-box">
                      <span className="stat-label">Area (km²)</span>
                      <span className="stat-val" style={{ color: '#059669' }}>
                        {currentProject.area_sqkm || 0} km²
                      </span>
                    </div>
                  </div>

                  <div style={{ display: 'flex', gap: 10 }}>
                    <button
                      className="btn-secondary"
                      style={{ flex: 1 }}
                      onClick={() => shapefileInputRef.current?.click()}
                    >
                      🔄 Re-upload Boundary
                    </button>
                    <button
                      className="btn-primary"
                      style={{ flex: 1 }}
                      onClick={() => setActiveStep(3)}
                    >
                      Step 3: Prepare Bands ➔
                    </button>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* STEP 3: SATELLITE BAND PREPARATION */}
          {activeStep === 3 && (
            <div className="card">
              <h2 className="card-title">🛰️ Step 3: Satellite Band Preparation & Indices</h2>
              <p className="card-desc">
                Acquire Level-2A Surface Reflectance satellite imagery for <b>{currentProject?.target_year}</b>.
                The Earth Engine pipeline applies cloud/shadow bitmasking (QA_PIXEL for Landsat, QA60 &amp; SCL for Sentinel-2),
                post-monsoon seasonal median compositing (Jan 1 – Apr 1), computes 6 spectral indices (NDVI, NDBI, MNDWI, BSI, UI, SAVI),
                and integrates SRTM 30 m topography (Elevation + Slope).
              </p>

              {/* Satellite Dataset Selector & Resolution Banner */}
              <div style={{
                background: 'var(--bg-card-secondary)',
                border: '1px solid var(--border-subtle)',
                borderRadius: 10,
                padding: 14,
                marginBottom: 14,
                display: 'flex',
                flexDirection: 'column',
                gap: 10,
              }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 6 }}>
                  <span style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-main)' }}>
                    📡 Satellite Mission &amp; Sensor Selection
                  </span>
                  <span style={{
                    fontSize: 11,
                    padding: '2px 8px',
                    borderRadius: 12,
                    background: (activeDataset || currentProject?.satellite_dataset)?.includes('sentinel')
                      ? 'rgba(14, 165, 233, 0.15)'
                      : 'rgba(16, 185, 129, 0.15)',
                    color: (activeDataset || currentProject?.satellite_dataset)?.includes('sentinel')
                      ? '#0284c7'
                      : '#059669',
                    fontWeight: 600,
                  }}>
                    {(activeDataset || currentProject?.satellite_dataset)?.includes('sentinel') ? '10m Optical & NIR / 20m SWIR' : '30m Multi-Spectral'}
                  </span>
                </div>

                <div style={{ display: 'flex', gap: 10, alignItems: 'center', flexWrap: 'wrap' }}>
                  <select
                    className="form-select"
                    style={{ flex: 1, minWidth: '220px', fontSize: 12.5 }}
                    value={activeDataset || currentProject?.satellite_dataset || 'landsat_8_9'}
                    onChange={(e) => {
                      const newDs = e.target.value;
                      setActiveDataset(newDs);
                      setAvailabilityWarning(null);
                      setAvailabilityInfo(null);
                    }}
                  >
                    {getApplicableDatasets(currentProject?.target_year).map((ds) => (
                      <option key={ds.dataset} value={ds.dataset}>
                        {ds.label}
                      </option>
                    ))}
                  </select>

                  <button
                    type="button"
                    className="btn-secondary"
                    style={{ fontSize: 11.5, padding: '6px 12px', whiteSpace: 'nowrap' }}
                    onClick={() => handleCheckAvailability(activeDataset || currentProject?.satellite_dataset)}
                    disabled={checkingAvailability || !currentProject?.has_boundary}
                  >
                    {checkingAvailability ? 'Checking...' : '🔍 Check Availability'}
                  </button>
                </div>

                {/* Spatial Resolution & Multi-Year Grid Callout */}
                <div style={{ fontSize: 11.5, color: 'var(--text-muted)', lineHeight: 1.5 }}>
                  • <b>Native Spatial Resolution:</b> {(activeDataset || currentProject?.satellite_dataset)?.includes('sentinel') ? '10 m (B2, B3, B4, B8) / 20 m (B11, B12)' : '30 m (Optical & SWIR)'}
                  <br />
                  • <b>Consistent Standard Grid:</b> Aligned on a 30 m pixel analysis grid to guarantee uniform comparability across multi-year and multi-sensor datasets.
                </div>
              </div>

              {/* Imagery Availability Warning Banner */}
              {availabilityWarning && (
                <div style={{
                  background: 'rgba(239, 68, 68, 0.1)',
                  border: '1px solid rgba(239, 68, 68, 0.3)',
                  color: '#dc2626',
                  padding: '12px 14px',
                  borderRadius: 8,
                  fontSize: 12.5,
                  lineHeight: 1.5,
                  marginBottom: 14,
                  display: 'flex',
                  gap: 10,
                  alignItems: 'flex-start',
                }}>
                  <span style={{ fontSize: 16 }}>⚠️</span>
                  <div>
                    <div style={{ fontWeight: 600 }}>Imagery Availability Warning</div>
                    <div>{availabilityWarning}</div>
                  </div>
                </div>
              )}

              {/* Imagery Availability Success Banner */}
              {availabilityInfo && availabilityInfo.available && !availabilityWarning && (
                <div style={{
                  background: 'rgba(16, 185, 129, 0.1)',
                  border: '1px solid rgba(16, 185, 129, 0.3)',
                  color: '#059669',
                  padding: '10px 14px',
                  borderRadius: 8,
                  fontSize: 12,
                  marginBottom: 14,
                  display: 'flex',
                  alignItems: 'center',
                  gap: 8,
                }}>
                  <span>✓</span>
                  <span>{availabilityInfo.message}</span>
                </div>
              )}

              <button
                className="btn-primary"
                onClick={() => handlePrepareBands(activeDataset || currentProject?.satellite_dataset)}
                disabled={loading || !currentProject?.has_boundary}
              >
                {loading ? <span className="spinner" /> : '⚡'} Acquire & Preprocess 14-Band Stack
              </button>

              {bandData && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 14, marginTop: 14 }}>
                  <div className="stat-grid">
                    <div className="stat-box">
                      <span className="stat-label">Sensor</span>
                      <span className="stat-val" style={{ fontSize: 13, color: 'var(--accent-blue)' }}>
                        {bandData.sensor}
                      </span>
                    </div>
                    <div className="stat-box">
                      <span className="stat-label">Native / Grid Resolution</span>
                      <span className="stat-val">{bandData.native_resolution || '30m'} Native / 30m Grid</span>
                    </div>
                    <div className="stat-box">
                      <span className="stat-label">Scenes Composited</span>
                      <span className="stat-val">{bandData.scenes_count} Scenes</span>
                    </div>
                  </div>

                  <div>
                    <span className="form-label" style={{ display: 'block', marginBottom: 8 }}>
                      Preview Spectral Layers on Map:
                    </span>
                    <div className="layer-button-grid">
                      <button
                        className={`layer-btn ${selectedPreviewBand === 'tcc' ? 'active' : ''}`}
                        onClick={() => switchPreviewLayer('tcc', 'True Color (TCC)')}
                      >
                        <span>🔴🟢🔵 True Color</span>
                      </button>
                      <button
                        className={`layer-btn ${selectedPreviewBand === 'fcc' ? 'active' : ''}`}
                        onClick={() => switchPreviewLayer('fcc', 'False Color (FCC)')}
                      >
                        <span>🟣 False Color (FCC)</span>
                      </button>
                      <button
                        className={`layer-btn ${selectedPreviewBand === 'ndvi' ? 'active' : ''}`}
                        onClick={() => switchPreviewLayer('ndvi', 'NDVI Vegetation')}
                      >
                        <span>🌿 NDVI Vegetation</span>
                      </button>
                      <button
                        className={`layer-btn ${selectedPreviewBand === 'ndbi' ? 'active' : ''}`}
                        onClick={() => switchPreviewLayer('ndbi', 'NDBI Built-up')}
                      >
                        <span>🏢 NDBI Built-up</span>
                      </button>
                      <button
                        className={`layer-btn ${selectedPreviewBand === 'mndwi' ? 'active' : ''}`}
                        onClick={() => switchPreviewLayer('mndwi', 'MNDWI Water')}
                      >
                        <span>💧 MNDWI Water</span>
                      </button>
                    </div>
                  </div>

                  <button
                    className="btn-primary"
                    onClick={() => setActiveStep(4)}
                  >
                    Step 4: Ground-Truth Samples ➔
                  </button>
                </div>
              )}
            </div>
          )}

          {/* STEP 4: GROUND-TRUTH & QGIS SAMPLING */}
          {activeStep === 4 && (
            <div className="card">
              <h2 className="card-title">📍 Step 4: Ground-Truth & Validation Samples</h2>
              <p className="card-desc">
                High classification accuracy requires pure reference samples tailored to the study area.
                Download the QGIS Starter Kit generated with your study boundary and configured classes,
                digitize points, and upload back. Points are automatically split into <b>70% Training / 30% Independent Validation</b>.
              </p>

              {/* QGIS Starter Kit Action */}
              <div style={{
                background: 'var(--bg-card-secondary)',
                border: '1px solid var(--border-subtle)',
                borderRadius: 10,
                padding: 14,
                display: 'flex',
                flexDirection: 'column',
                gap: 10
              }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-main)' }}>
                    📦 Tailored QGIS Starter Kit
                  </span>
                  <button
                    className="btn-secondary"
                    style={{ padding: '3px 8px', fontSize: '11px' }}
                    onClick={() => setShowClassesModal(true)}
                  >
                    Configure Classes
                  </button>
                </div>
                <div style={{ fontSize: 12, color: 'var(--text-muted)', lineHeight: 1.4 }}>
                  Includes study boundary GeoJSON, 2 km sampling grid (classified into Validation & Training cells), point & raster symbology (.qml), and step-by-step digitization guide.
                </div>
                <button
                  className="btn-secondary"
                  onClick={handleDownloadQgisKit}
                  disabled={!currentProject?.has_boundary}
                >
                  📥 Download QGIS Starter Kit (.zip)
                </button>
              </div>

              {/* Upload Digitized Points */}
              <input
                ref={samplesInputRef}
                type="file"
                accept=".geojson,.json,.csv"
                style={{ display: 'none' }}
                onChange={handleSamplesUpload}
              />

              <div
                className="dropzone"
                onClick={() => samplesInputRef.current?.click()}
              >
                <div className="dropzone-icon">📍</div>
                <div className="dropzone-text">Upload Digitized Points (.geojson or .csv)</div>
                <div className="dropzone-subtext">
                  Requires coordinates and 'class_id' matching your study area classes
                </div>
              </div>

              {/* Confirmed Ground-Truth Samples & Dynamic Legend Breakdown */}
              {sampleSplitStats && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                  <div style={{
                    padding: '8px 12px',
                    borderRadius: 8,
                    background: 'rgba(16, 185, 129, 0.1)',
                    border: '1px solid rgba(16, 185, 129, 0.3)',
                    fontSize: 12,
                    color: theme === 'light' ? '#065f46' : '#34d399',
                    fontWeight: 600,
                  }}>
                    ✓ Ground-Truth Samples Confirmed! Dynamic LULC Legend active.
                  </div>

                  <div className="stat-grid">
                    <div className="stat-box">
                      <span className="stat-label">Training Points (70%)</span>
                      <span className="stat-val" style={{ color: '#059669' }}>
                        {sampleSplitStats.training_count} pts
                      </span>
                    </div>
                    <div className="stat-box">
                      <span className="stat-label">Validation Holdout (30%)</span>
                      <span className="stat-val" style={{ color: 'var(--accent-blue)' }}>
                        {sampleSplitStats.validation_count} pts
                      </span>
                    </div>
                  </div>

                  <div className="table-container">
                    <table className="custom-table">
                      <thead>
                        <tr>
                          <th>Class</th>
                          <th>Total</th>
                          <th>Train (70%)</th>
                          <th>Val (30%)</th>
                        </tr>
                      </thead>
                      <tbody>
                        {Object.entries(sampleSplitStats.class_breakdown || {}).map(([cid, info]) => (
                          <tr key={cid}>
                            <td>
                              <span
                                className="color-dot"
                                style={{ background: info.color || activeLulcClasses[cid]?.color || '#888' }}
                              />
                              {info.name}
                            </td>
                            <td>{info.total}</td>
                            <td style={{ color: '#059669', fontWeight: 600 }}>{info.training}</td>
                            <td style={{ color: 'var(--accent-blue)', fontWeight: 600 }}>{info.validation}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>

                  <button
                    className="btn-primary"
                    onClick={() => setActiveStep(5)}
                  >
                    Step 5: Machine Learning Classification (RF / SVM) ➔
                  </button>
                </div>
              )}
            </div>
          )}

          {/* STEP 5: SUPERVISED MACHINE LEARNING CLASSIFICATION (RF & SVM) */}
          {activeStep === 5 && (
            <div className="card">
              <h2 className="card-title">⚡ Step 5: Supervised Classification (RF & SVM)</h2>
              <p className="card-desc">
                Select your preferred supervised machine learning algorithm for Land Use / Land Cover mapping.
                The model is trained on the 14 multi-source predictor stack using 70% ground-truth samples,
                while the remaining 30% independent holdouts are preserved for accuracy validation.
              </p>

              {/* Algorithm Selection Option Cards */}
              <div style={{ marginTop: 6, marginBottom: 2 }}>
                <span className="form-label" style={{ fontSize: 11.5, fontWeight: 600 }}>CHOOSE CLASSIFICATION ALGORITHM:</span>
              </div>
              <div className="algo-selector-grid">
                {/* Random Forest Option */}
                <div
                  className={`algo-card ${selectedAlgorithm === 'rf' ? 'active' : ''}`}
                  onClick={() => handleSwitchAlgorithm('rf')}
                  title="Select Random Forest classification algorithm"
                >
                  <div className="algo-card-header">
                    <div className="algo-card-title">
                      <span>🌲</span>
                      <span>Random Forest</span>
                    </div>
                    <span className="algo-pill">100 Trees</span>
                  </div>
                  <div className="algo-card-desc">
                    Ensemble decision trees (SmileRF). High tolerance to feature correlation across spectral indices and robust to noisy pixels.
                  </div>
                  <div className="algo-params-table">
                    <div className="algo-param-row"><span>Engine:</span> <b>SmileRF (GEE)</b></div>
                    <div className="algo-param-row"><span>Trees / Bagging:</span> <b>100 / 0.8</b></div>
                    <div className="algo-param-row"><span>Split Rule:</span> <b>Gini Impurity</b></div>
                  </div>
                </div>

                {/* Support Vector Machine Option */}
                <div
                  className={`algo-card ${selectedAlgorithm === 'svm' ? 'active' : ''}`}
                  onClick={() => handleSwitchAlgorithm('svm')}
                  title="Select Support Vector Machine classification algorithm"
                >
                  <div className="algo-card-header">
                    <div className="algo-card-title">
                      <span>⚡</span>
                      <span>Support Vector Machine</span>
                    </div>
                    <span className="algo-pill">RBF Kernel</span>
                  </div>
                  <div className="algo-card-desc">
                    Supervised classifier (LibSVM C-SVC) with non-linear Radial Basis Function (RBF) kernel. Optimizes maximum-margin boundaries.
                  </div>
                  <div className="algo-params-table">
                    <div className="algo-param-row"><span>Engine:</span> <b>LibSVM (GEE)</b></div>
                    <div className="algo-param-row"><span>Type / Kernel:</span> <b>C-SVC / RBF</b></div>
                    <div className="algo-param-row"><span>Decision:</span> <b>Voting (C=10)</b></div>
                  </div>
                </div>
              </div>

              {/* Configuration Summary */}
              <div style={{
                background: 'var(--bg-card-secondary)',
                border: '1px solid var(--border-subtle)',
                borderRadius: 10,
                padding: 12,
                display: 'flex',
                flexDirection: 'column',
                gap: 6,
                fontSize: 12,
                color: 'var(--text-muted)'
              }}>
                <div><b>Active Algorithm:</b> {selectedAlgorithm === 'svm' ? 'Support Vector Machine (LibSVM C-SVC, RBF Kernel)' : 'Random Forest (SmileRF, 100 Trees)'}</div>
                <div><b>Predictor Stack:</b> 6 Optical + 6 Spectral Indices + 2 Topography (14 Bands)</div>
                <div><b>Training Points:</b> {sampleSplitStats?.training_count || currentProject?.training_samples_count || '70%'} samples</div>
                <div><b>Validation Points:</b> {sampleSplitStats?.validation_count || currentProject?.validation_samples_count || '30%'} independent holdout points</div>
                <div><b>Spatial Resolution:</b> {formatDatasetLabel(activeDataset || currentProject?.satellite_dataset)} ({(activeDataset || currentProject?.satellite_dataset)?.includes('sentinel') ? '10m Native / 30m Standard Analysis Grid' : '30m Multi-Spectral Grid'})</div>
              </div>

              <button
                className="btn-primary"
                onClick={() => handleRunClassification(selectedAlgorithm)}
                disabled={loading || !currentProject?.has_samples}
              >
                {loading ? <span className="spinner" /> : (selectedAlgorithm === 'svm' ? '⚡' : '🚀')} Execute {selectedAlgorithm === 'svm' ? 'Support Vector Machine (SVM)' : 'Random Forest (RF)'} Classification
              </button>
            </div>
          )}

          {/* STEP 6: ACCURACY ASSESSMENT */}
          {activeStep === 6 && (
            <div className="card">
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 8 }}>
                <h2 className="card-title" style={{ margin: 0 }}>📊 Step 6: Independent Accuracy Assessment</h2>
                <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                  <button
                    className={`layer-btn ${selectedAlgorithm === 'rf' ? 'active' : ''}`}
                    style={{ padding: '4px 10px', fontSize: '11px', borderRadius: 6 }}
                    onClick={() => handleSwitchAlgorithm('rf')}
                    title="View Random Forest (RF) accuracy results"
                  >
                    🌲 RF
                  </button>
                  <button
                    className={`layer-btn ${selectedAlgorithm === 'svm' ? 'active' : ''}`}
                    style={{ padding: '4px 10px', fontSize: '11px', borderRadius: 6 }}
                    onClick={() => handleSwitchAlgorithm('svm')}
                    title="View Support Vector Machine (SVM) accuracy results"
                  >
                    ⚡ SVM
                  </button>
                </div>
              </div>

              <p className="card-desc">
                Rigorous evaluation of the <b>{classificationResults?.algorithm_name || (selectedAlgorithm === 'svm' ? 'Support Vector Machine (SVM)' : 'Random Forest (RF)')}</b> model using 30% independent holdout validation points not seen during model training.
              </p>

              {/* Algorithm Status Banner */}
              <div style={{
                background: 'rgba(16, 185, 129, 0.08)',
                border: '1px solid rgba(16, 185, 129, 0.25)',
                borderRadius: 8,
                padding: '8px 12px',
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                fontSize: '12px',
              }}>
                <span style={{ color: 'var(--text-main)', fontWeight: 600 }}>
                  Assessed Algorithm: {classificationResults?.algorithm_name || (selectedAlgorithm === 'svm' ? 'Support Vector Machine (SVM)' : 'Random Forest (RF)')}
                </span>
                <span className="algo-pill">
                  {classificationResults?.algorithm || (selectedAlgorithm === 'svm' ? 'SVM' : 'RF')}
                </span>
              </div>

              {classificationResults?.accuracy ? (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
                  <div className="stat-grid">
                    <div className="stat-box">
                      <span className="stat-label">Overall Accuracy (OA)</span>
                      <span className="stat-val" style={{ color: '#059669', fontSize: 20 }}>
                        {classificationResults.accuracy.overall_accuracy}%
                      </span>
                    </div>
                    <div className="stat-box">
                      <span className="stat-label">Cohen's Kappa (κ)</span>
                      <span className="stat-val" style={{ color: 'var(--accent-blue)', fontSize: 20 }}>
                        {classificationResults.accuracy.kappa_coefficient}
                      </span>
                    </div>
                  </div>

                  <div className="table-container">
                    <table className="custom-table">
                      <thead>
                        <tr>
                          <th>Class</th>
                          <th>Producer's (PA)</th>
                          <th>User's (UA)</th>
                        </tr>
                      </thead>
                      <tbody>
                        {Object.entries(classificationResults.accuracy.per_class || {}).map(([cid, met]) => (
                          <tr key={cid}>
                            <td>
                              <span className="color-dot" style={{ background: met.color }} />
                              {met.name}
                            </td>
                            <td style={{ color: met.producers_accuracy > 70 ? '#059669' : '#d97706', fontWeight: 600 }}>
                              {met.producers_accuracy}%
                            </td>
                            <td style={{ color: met.users_accuracy > 70 ? '#059669' : '#d97706', fontWeight: 600 }}>
                              {met.users_accuracy}%
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>

                  {/* Detailed Confusion Matrix Toggle & Grid */}
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                    <button
                      type="button"
                      className="btn-secondary"
                      style={{ fontSize: '11px', padding: '6px 10px', width: '100%', justifyContent: 'center' }}
                      onClick={() => setShowConfusionMatrix(!showConfusionMatrix)}
                    >
                      {showConfusionMatrix ? '▲ Hide Confusion Matrix' : '▼ View Cross-Tabulated Confusion Matrix'}
                    </button>

                    {showConfusionMatrix && classificationResults.accuracy.confusion_matrix && (
                      <div className="table-container" style={{ maxHeight: '300px', overflowX: 'auto', border: '1px solid var(--border-subtle)', borderRadius: 8, padding: 8 }}>
                        <table className="custom-table" style={{ fontSize: '11px' }}>
                          <thead>
                            <tr>
                              <th title="Ground-Truth Reference Class">Reference \ Predicted</th>
                              {Object.entries(classificationResults.accuracy.per_class || {}).map(([cid, met]) => (
                                <th key={`cm-th-${cid}`} style={{ textAlign: 'center', whiteSpace: 'nowrap' }} title={met.name}>
                                  <span className="color-dot" style={{ background: met.color, marginRight: 2 }} />
                                  {met.name.length > 8 ? `${met.name.slice(0, 7)}…` : met.name}
                                </th>
                              ))}
                              <th style={{ textAlign: 'center' }}>Total</th>
                              <th style={{ textAlign: 'center' }}>PA (%)</th>
                            </tr>
                          </thead>
                          <tbody>
                            {Object.entries(classificationResults.accuracy.per_class || {}).map(([cid, met]) => {
                              const cNum = parseInt(cid, 10);
                              const rawMat = classificationResults.accuracy.confusion_matrix;
                              const row = (cNum < rawMat.length && Array.isArray(rawMat[cNum])) ? rawMat[cNum] : [];
                              const refTotal = row.length > 0 ? row.reduce((a, b) => a + b, 0) : 0;
                              return (
                                <tr key={`cm-row-${cid}`}>
                                  <td style={{ fontWeight: 600, whiteSpace: 'nowrap' }}>
                                    <span className="color-dot" style={{ background: met.color }} />
                                    {met.name}
                                  </td>
                                  {Object.entries(classificationResults.accuracy.per_class || {}).map(([colCid]) => {
                                    const colNum = parseInt(colCid, 10);
                                    const val = (row.length > colNum) ? row[colNum] : 0;
                                    const isDiag = cNum === colNum;
                                    return (
                                      <td
                                        key={`cm-cell-${cid}-${colCid}`}
                                        style={{
                                          textAlign: 'center',
                                          fontWeight: isDiag ? 700 : 400,
                                          background: isDiag ? 'rgba(16, 185, 129, 0.15)' : 'transparent',
                                          color: isDiag ? '#059669' : (val > 0 ? 'var(--text-main)' : 'var(--text-dim)'),
                                        }}
                                      >
                                        {val}
                                      </td>
                                    );
                                  })}
                                  <td style={{ textAlign: 'center', fontWeight: 600 }}>{refTotal}</td>
                                  <td style={{ textAlign: 'center', fontWeight: 600, color: met.producers_accuracy > 70 ? '#059669' : '#d97706' }}>
                                    {met.producers_accuracy}%
                                  </td>
                                </tr>
                              );
                            })}
                            <tr style={{ borderTop: '2px solid var(--border-strong)', fontWeight: 600, background: 'var(--bg-card-hover)' }}>
                              <td>User's Accuracy (UA)</td>
                              {Object.entries(classificationResults.accuracy.per_class || {}).map(([cid, met]) => (
                                <td key={`cm-ua-${cid}`} style={{ textAlign: 'center', color: met.users_accuracy > 70 ? '#059669' : '#d97706' }}>
                                  {met.users_accuracy}%
                                </td>
                              ))}
                              <td colSpan={2} style={{ textAlign: 'center', color: '#059669' }}>
                                OA: {classificationResults.accuracy.overall_accuracy}%
                              </td>
                            </tr>
                          </tbody>
                        </table>
                      </div>
                    )}
                  </div>

                  {/* Random Forest Feature Importance Section */}
                  <div style={{
                    marginTop: 6,
                    padding: 12,
                    background: 'var(--bg-card)',
                    border: '1px solid var(--border-subtle)',
                    borderRadius: 8,
                    display: 'flex',
                    flexDirection: 'column',
                    gap: 10,
                  }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 6 }}>
                      <span style={{ fontWeight: 600, fontSize: 13, color: 'var(--text-main)', display: 'flex', alignItems: 'center', gap: 6 }}>
                        🌲 Random Forest Feature Importance (14 Bands)
                      </span>
                      {selectedAlgorithm === 'rf' && !featureImportance?.ranked_features && (
                        <button
                          type="button"
                          className="btn-secondary"
                          style={{ fontSize: '11px', padding: '4px 8px' }}
                          onClick={handleFetchFeatureImportance}
                          disabled={loadingImportance}
                        >
                          {loadingImportance ? 'Evaluating...' : '⚡ Compute Importance'}
                        </button>
                      )}
                    </div>

                    {selectedAlgorithm === 'svm' ? (
                      <div style={{
                        padding: '8px 10px',
                        background: 'rgba(59, 130, 246, 0.08)',
                        border: '1px solid rgba(59, 130, 246, 0.2)',
                        borderRadius: 6,
                        fontSize: 11,
                        color: 'var(--text-muted)',
                      }}>
                        ℹ️ Feature importance ranking is based on decision-tree node impurity reduction (Gini index) and is specific to Random Forest. It is not applicable to Support Vector Machine (SVM) hyperplanes.
                      </div>
                    ) : (featureImportance?.ranked_features || classificationResults?.feature_importance?.ranked_features) ? (
                      <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                        <p style={{ margin: 0, fontSize: 11, color: 'var(--text-muted)', lineHeight: 1.4 }}>
                          <b>Metric:</b> {(featureImportance || classificationResults?.feature_importance)?.metric || 'Gini Impurity Decrease'}. Measures total impurity reduction across 100 decision trees.
                        </p>

                        <div style={{ display: 'flex', flexDirection: 'column', gap: 6, maxHeight: '240px', overflowY: 'auto', paddingRight: 4 }}>
                          {(featureImportance?.ranked_features || classificationResults?.feature_importance?.ranked_features || []).map((item, idx) => {
                            const isOptical = ['blue', 'green', 'red', 'nir', 'swir1', 'swir2'].includes(item.feature);
                            const isIndex = ['ndvi', 'ndbi', 'mndwi', 'bsi', 'ui', 'savi'].includes(item.feature);
                            const catColor = isOptical ? '#3b82f6' : (isIndex ? '#10b981' : '#f59e0b');
                            const catLabel = isOptical ? 'Optical' : (isIndex ? 'Index' : 'Topo');

                            return (
                              <div key={item.feature} style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: 11 }}>
                                  <span style={{ display: 'flex', alignItems: 'center', gap: 6, fontWeight: 500 }}>
                                    <span style={{ color: 'var(--text-dim)', width: 16 }}>#{idx + 1}</span>
                                    <span style={{ fontFamily: 'var(--font-mono)', fontWeight: 600, color: 'var(--text-main)' }}>{item.feature}</span>
                                    <span style={{
                                      fontSize: 9,
                                      padding: '1px 5px',
                                      borderRadius: 4,
                                      background: `${catColor}20`,
                                      color: catColor,
                                      fontWeight: 600
                                    }}>
                                      {catLabel}
                                    </span>
                                  </span>
                                  <span style={{ fontFamily: 'var(--font-mono)', color: 'var(--text-muted)', fontSize: 11 }}>
                                    {item.relative_importance_pct}% <span style={{ color: 'var(--text-dim)', fontSize: 10 }}>({item.score})</span>
                                  </span>
                                </div>
                                <div style={{
                                  width: '100%',
                                  height: 6,
                                  background: 'var(--bg-dark)',
                                  borderRadius: 3,
                                  overflow: 'hidden',
                                }}>
                                  <div style={{
                                    width: `${Math.min(100, Math.max(3, item.relative_importance_pct))}%`,
                                    height: '100%',
                                    background: catColor,
                                    borderRadius: 3,
                                    transition: 'width 0.4s ease',
                                  }} />
                                </div>
                              </div>
                            );
                          })}
                        </div>

                        <div style={{
                          fontSize: 10,
                          color: 'var(--text-dim)',
                          lineHeight: 1.3,
                          borderTop: '1px dashed var(--border-subtle)',
                          paddingTop: 6,
                        }}>
                          ⚠️ <i>Caution: Predictor ranking reflects statistical association across sample splits in this feature stack; it does not indicate physical or causal influence.</i>
                        </div>
                      </div>
                    ) : (
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: 11, color: 'var(--text-muted)' }}>
                        <span>Feature importance not yet computed for this model run.</span>
                        <button
                          type="button"
                          className="btn-secondary"
                          style={{ fontSize: '10px', padding: '3px 8px' }}
                          onClick={handleFetchFeatureImportance}
                          disabled={loadingImportance}
                        >
                          {loadingImportance ? 'Computing in GEE...' : '⚡ Compute Now'}
                        </button>
                      </div>
                    )}
                  </div>

                  <div style={{ display: 'flex', gap: 10, marginTop: 4 }}>
                    <button
                      className="btn-secondary"
                      style={{ flex: 1 }}
                      onClick={() => triggerExport('accuracy-csv', `?year=${currentProject.target_year}`)}
                    >
                      📄 Export Accuracy Report
                    </button>
                    <button
                      className="btn-primary"
                      style={{ flex: 1 }}
                      onClick={() => setActiveStep(7)}
                    >
                      Step 7: Final Map & Export ➔
                    </button>
                  </div>
                </div>
              ) : (
                <div style={{ textAlign: 'center', padding: '16px 0' }}>
                  <p style={{ color: 'var(--text-muted)', fontSize: 13, marginBottom: 12 }}>
                    No classification results found for {selectedAlgorithm === 'svm' ? 'Support Vector Machine (SVM)' : 'Random Forest (RF)'}.
                  </p>
                  <button
                    className="btn-primary"
                    style={{ margin: '0 auto', maxWidth: '280px' }}
                    onClick={() => handleRunClassification(selectedAlgorithm)}
                    disabled={loading || !currentProject?.has_samples}
                  >
                    🚀 Run {selectedAlgorithm === 'svm' ? 'SVM' : 'RF'} Classification Now
                  </button>
                </div>
              )}
            </div>
          )}

          {/* STEP 7: FINAL MAP & EXPORT */}
          {activeStep === 7 && (
            <div className="card">
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 8 }}>
                <h2 className="card-title" style={{ margin: 0 }}>💾 Step 7: LULC Map & Analytical Exports</h2>
                <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                  <button
                    className={`layer-btn ${selectedAlgorithm === 'rf' ? 'active' : ''}`}
                    style={{ padding: '4px 10px', fontSize: '11px', borderRadius: 6 }}
                    onClick={() => handleSwitchAlgorithm('rf')}
                    title="Switch to Random Forest (RF) map"
                  >
                    🌲 RF
                  </button>
                  <button
                    className={`layer-btn ${selectedAlgorithm === 'svm' ? 'active' : ''}`}
                    style={{ padding: '4px 10px', fontSize: '11px', borderRadius: 6 }}
                    onClick={() => handleSwitchAlgorithm('svm')}
                    title="Switch to Support Vector Machine (SVM) map"
                  >
                    ⚡ SVM
                  </button>
                </div>
              </div>

              <p className="card-desc">
                Final classified thematic map for <b>{currentProject?.name} ({currentProject?.target_year})</b> produced using <b>{classificationResults?.algorithm_name || (selectedAlgorithm === 'svm' ? 'Support Vector Machine (SVM)' : 'Random Forest (RF)')}</b>.
                Explore class-wise area quantification and export data in GIS and spreadsheet formats.
              </p>

              {/* Opacity Slider */}
              <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12 }}>
                  <span className="form-label">Classification Opacity:</span>
                  <span style={{ fontFamily: 'var(--font-mono)', color: '#059669', fontWeight: 600 }}>
                    {Math.round(layerOpacity * 100)}%
                  </span>
                </div>
                <input
                  type="range"
                  min="0.1"
                  max="1.0"
                  step="0.05"
                  value={layerOpacity}
                  onChange={(e) => setLayerOpacity(parseFloat(e.target.value))}
                />
              </div>

              {/* Area Statistics Table */}
              {classificationResults?.area_statistics && (
                <div className="table-container">
                  <table className="custom-table">
                    <thead>
                      <tr>
                        <th>Class</th>
                        <th>Area (ha)</th>
                        <th>Area (km²)</th>
                        <th>%</th>
                      </tr>
                    </thead>
                    <tbody>
                      {classificationResults.area_statistics.map((st) => (
                        <tr key={st.class_id}>
                          <td>
                            <span className="color-dot" style={{ background: st.color }} />
                            {st.name}
                          </td>
                          <td>{Number(st.area_ha).toLocaleString()}</td>
                          <td>{st.area_sqkm}</td>
                          <td style={{ fontWeight: 600, color: 'var(--accent-blue)' }}>{st.percentage}%</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}

              {/* Comprehensive Download Centre */}
              <div className="download-centre-card">
                <div className="download-centre-header">
                  <div>
                    <h3 className="download-centre-title">📥 Study Area Download Centre</h3>
                    <p className="download-centre-subtitle">
                      Directly download all generated rasters, vectors, analytical reports, and QGIS symbology packages to your device.
                    </p>
                  </div>
                </div>

                {/* Complete Project Archive Bundle */}
                <div className="bundle-download-card">
                  <div className="bundle-info">
                    <span className="bundle-icon">📦</span>
                    <div>
                      <div className="bundle-title">Complete Project GIS Archive (.zip)</div>
                      <div className="bundle-desc">
                        One-click package containing GeoTIFF, PNG map, Training & Validation sample points, Study boundary, Area statistics CSV, Accuracy report CSV, and QGIS styles.
                      </div>
                    </div>
                  </div>
                  <button
                    className="btn-primary"
                    style={{ whiteSpace: 'nowrap', padding: '8px 14px', fontSize: '12.5px' }}
                    onClick={handleDownloadCompleteBundle}
                    disabled={loading}
                    title="Download complete all-in-one ZIP package"
                  >
                    📦 Download All (.zip)
                  </button>
                </div>

                {/* Category 1: Classified Raster & Imagery */}
                <div className="download-category">
                  <span className="download-category-title">🗺️ Thematic Raster & Imagery</span>
                  <div className="download-grid">
                    <button
                      className="download-action-btn"
                      onClick={handleDownloadGeoTIFF}
                      disabled={loading}
                      title="Download 30m resolution classified GeoTIFF raster"
                    >
                      <span className="download-btn-icon">🗺️</span>
                      <div className="download-btn-text">
                        <span className="download-btn-label">Classified GeoTIFF</span>
                        <span className="download-btn-sub">30m Raster (.tif)</span>
                      </div>
                    </button>
                    <button
                      className="download-action-btn"
                      onClick={() => handleDownloadImage('png')}
                      disabled={loading}
                      title="Download high-resolution map image visualization"
                    >
                      <span className="download-btn-icon">🖼️</span>
                      <div className="download-btn-text">
                        <span className="download-btn-label">Map Visualization</span>
                        <span className="download-btn-sub">High-Res PNG Image</span>
                      </div>
                    </button>
                  </div>
                </div>

                {/* Category 2: Analytical & Statistical Reports */}
                <div className="download-category">
                  <span className="download-category-title">📊 Quantification & Accuracy Reports</span>
                  <div className="download-grid">
                    <button
                      className="download-action-btn"
                      onClick={handleDownloadStatsCsv}
                      disabled={loading}
                      title="Download class-wise area quantification table in CSV format"
                    >
                      <span className="download-btn-icon">📊</span>
                      <div className="download-btn-text">
                        <span className="download-btn-label">Class Area Stats</span>
                        <span className="download-btn-sub">CSV Spreadsheet</span>
                      </div>
                    </button>
                    <button
                      className="download-action-btn"
                      onClick={handleDownloadAccuracyCsv}
                      disabled={loading}
                      title="Download confusion matrix, OA, Kappa, PA and UA in CSV format"
                    >
                      <span className="download-btn-icon">📈</span>
                      <div className="download-btn-text">
                        <span className="download-btn-label">Accuracy Assessment</span>
                        <span className="download-btn-sub">CSV Report & Matrix</span>
                      </div>
                    </button>
                  </div>
                </div>

                {/* Category 3: Ground-Truth Points & Vector Boundary */}
                <div className="download-category">
                  <span className="download-category-title">📍 Ground-Truth Samples & Vector Boundary</span>
                  <div className="download-grid">
                    <button
                      className="download-action-btn"
                      onClick={handleDownloadBoundary}
                      disabled={loading}
                      title="Download study area boundary polygon in GeoJSON format"
                    >
                      <span className="download-btn-icon">📐</span>
                      <div className="download-btn-text">
                        <span className="download-btn-label">Study Area Boundary</span>
                        <span className="download-btn-sub">GeoJSON Polygon</span>
                      </div>
                    </button>
                    <button
                      className="download-action-btn"
                      onClick={() => handleDownloadSamples('training', 'geojson')}
                      disabled={loading}
                      title="Download 70% training sample points in GeoJSON format"
                    >
                      <span className="download-btn-icon">🎯</span>
                      <div className="download-btn-text">
                        <span className="download-btn-label">Training Points</span>
                        <span className="download-btn-sub">70% Split (GeoJSON)</span>
                      </div>
                    </button>
                    <button
                      className="download-action-btn"
                      onClick={() => handleDownloadSamples('validation', 'geojson')}
                      disabled={loading}
                      title="Download 30% independent validation holdout points in GeoJSON format"
                    >
                      <span className="download-btn-icon">✅</span>
                      <div className="download-btn-text">
                        <span className="download-btn-label">Validation Holdouts</span>
                        <span className="download-btn-sub">30% Split (GeoJSON)</span>
                      </div>
                    </button>
                    <button
                      className="download-action-btn"
                      onClick={() => handleDownloadSamples('all', 'csv')}
                      disabled={loading}
                      title="Download all reference points in CSV format"
                    >
                      <span className="download-btn-icon">📑</span>
                      <div className="download-btn-text">
                        <span className="download-btn-label">All Ground Points</span>
                        <span className="download-btn-sub">CSV Table Format</span>
                      </div>
                    </button>
                  </div>
                </div>

                {/* Category 4: QGIS Symbology Files */}
                <div className="download-category">
                  <span className="download-category-title">🎨 QGIS Layer Styling (.qml)</span>
                  <div className="download-grid">
                    <button
                      className="download-action-btn"
                      onClick={() => handleDownloadQmlStyle('raster')}
                      disabled={loading}
                      title="Download QGIS paletted raster style file (.qml) to render GeoTIFF"
                    >
                      <span className="download-btn-icon">🎨</span>
                      <div className="download-btn-text">
                        <span className="download-btn-label">Raster Style (.qml)</span>
                        <span className="download-btn-sub">Palette for GeoTIFF</span>
                      </div>
                    </button>
                    <button
                      className="download-action-btn"
                      onClick={() => handleDownloadQmlStyle('vector')}
                      disabled={loading}
                      title="Download QGIS vector point style file (.qml) for reference samples"
                    >
                      <span className="download-btn-icon">📌</span>
                      <div className="download-btn-text">
                        <span className="download-btn-label">Point Style (.qml)</span>
                        <span className="download-btn-sub">Vector Symbology</span>
                      </div>
                    </button>
                  </div>
                </div>
              </div>
            </div>
          )}
        </aside>

        {/* Right Interactive Map */}
        <main className="map-view-panel">
          <MapViewer
            boundaryGeojson={boundaryGeojson}
            activeTileUrl={activeTileUrl}
            activeLayerName={activeLayerName}
            layerOpacity={layerOpacity}
            trainingPoints={trainingPoints}
            validationPoints={validationPoints}
            showSamples={showSamples}
            showBoundary={true}
            classes={activeLulcClasses}
            theme={theme}
          />

          {/* Dynamic LULC Legend Overlay - Rendered dynamically ONLY after samples are confirmed */}
          {areSamplesConfirmed && activeClassesList.length > 0 && (
            <div className="legend-overlay">
              <div className="legend-header">
                <span className="legend-title">LULC Classes</span>
                <span style={{ fontSize: 10, color: '#059669', fontWeight: 600 }}>Confirmed ✓</span>
              </div>
              {activeClassesList.map(([cid, cinfo]) => (
                <div key={cid} className="legend-item">
                  <span className="color-dot" style={{ background: cinfo.color }} />
                  <span>{cid}. {cinfo.name}</span>
                </div>
              ))}
            </div>
          )}
        </main>
      </div>

      {/* CREATE NEW PROJECT MODAL */}
      {showNewProjectModal && (
        <div className="modal-backdrop">
          <div className="modal-content">
            <h3 style={{ fontFamily: 'var(--font-heading)', fontSize: 18, color: 'var(--text-main)' }}>
              Create New Study Area Project
            </h3>
            <p style={{ fontSize: 13, color: 'var(--text-muted)' }}>
              Set up a separate project for your study area.
            </p>

            {backendStatus === 'offline' && (
              <div className="modal-offline-warning">
                <span style={{ fontSize: 20 }}>⚠️</span>
                <div style={{ flex: 1 }}>
                  <strong>Backend Server Offline</strong>
                  <div style={{ fontSize: 12, marginTop: 2 }}>
                    The backend API on port 8001 is not running. Open a terminal and run <code>npm run backend</code> (or <code>python backend/app.py</code>) to start the service.
                  </div>
                </div>
                <button
                  type="button"
                  className="btn-secondary"
                  style={{ fontSize: 11, padding: '4px 8px', whiteSpace: 'nowrap' }}
                  onClick={async () => {
                    const ok = await checkBackendHealth();
                    if (ok) loadProjectsList();
                  }}
                >
                  🔄 Retry
                </button>
              </div>
            )}

            <form onSubmit={handleCreateProject} style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
              <div className="form-group">
                <label className="form-label">Study Area / Taluk Name *</label>
                <input
                  className="form-input"
                  placeholder="e.g. Salem South Taluk, Pollachi Taluk, Dharmapuri"
                  value={newProjName}
                  onChange={(e) => setNewProjName(e.target.value)}
                  required
                />
              </div>

              {/* Improved District Selection Dropdown */}
              <div className="form-group">
                <label className="form-label">District / Region *</label>
                <select
                  className="form-select"
                  value={newProjDistrict}
                  onChange={(e) => setNewProjDistrict(e.target.value)}
                  style={{
                    backgroundColor: 'var(--input-bg)',
                    color: 'var(--input-text)',
                    borderColor: 'var(--input-border)',
                  }}
                >
                  {TN_DISTRICTS.map((dist) => (
                    <option
                      key={dist}
                      value={dist}
                      style={{
                        backgroundColor: 'var(--option-bg)',
                        color: 'var(--option-text)',
                      }}
                    >
                      {dist}
                    </option>
                  ))}
                </select>
              </div>

              <div className="form-group">
                <label className="form-label" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span>Target Study Year &amp; Satellite Dataset *</span>
                  <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>10m / 30m Multi-Sensor</span>
                </label>
                <select
                  className="form-select"
                  value={`${newProjYear}::${newProjDataset}`}
                  onChange={(e) => {
                    const [yStr, dStr] = e.target.value.split('::');
                    setNewProjYear(parseInt(yStr));
                    setNewProjDataset(dStr);
                  }}
                  style={{
                    backgroundColor: 'var(--input-bg)',
                    color: 'var(--input-text)',
                    borderColor: 'var(--input-border)',
                  }}
                >
                  <optgroup label="Recent High-Resolution Sentinel-2 &amp; Modern Landsat (2022 - 2025)">
                    <option value="2025::landsat_8_9">2025 (Landsat 8 &amp; 9 - 30m)</option>
                    <option value="2025::sentinel_2">2025 (Sentinel-2A &amp; 2B - 10m)</option>
                    <option value="2024::landsat_8_9">2024 (Landsat 8 &amp; 9 - 30m)</option>
                    <option value="2024::sentinel_2">2024 (Sentinel-2A &amp; 2B - 10m)</option>
                    <option value="2023::landsat_8_9">2023 (Landsat 8 &amp; 9 - 30m)</option>
                    <option value="2023::sentinel_2">2023 (Sentinel-2A &amp; 2B - 10m)</option>
                    <option value="2022::landsat_8_9">2022 (Landsat 8 &amp; 9 - 30m)</option>
                    <option value="2022::sentinel_2">2022 (Sentinel-2A &amp; 2B - 10m)</option>
                  </optgroup>
                  <optgroup label="Mid-Period Sentinel-2 &amp; Landsat 8 (2016 - 2021)">
                    <option value="2021::landsat_8">2021 (Landsat 8 - 30m)</option>
                    <option value="2021::sentinel_2">2021 (Sentinel-2A &amp; 2B - 10m)</option>
                    <option value="2020::landsat_8">2020 (Landsat 8 - 30m)</option>
                    <option value="2020::sentinel_2">2020 (Sentinel-2A &amp; 2B - 10m)</option>
                    <option value="2019::landsat_8">2019 (Landsat 8 - 30m)</option>
                    <option value="2019::sentinel_2">2019 (Sentinel-2A &amp; 2B - 10m)</option>
                    <option value="2018::landsat_8">2018 (Landsat 8 - 30m)</option>
                    <option value="2018::sentinel_2">2018 (Sentinel-2A &amp; 2B - 10m)</option>
                    <option value="2017::landsat_8">2017 (Landsat 8 - 30m)</option>
                    <option value="2017::sentinel_2">2017 (Sentinel-2A &amp; 2B - 10m)</option>
                    <option value="2016::landsat_8">2016 (Landsat 8 - 30m)</option>
                    <option value="2016::sentinel_2a">2016 (Sentinel-2A - 10m)</option>
                  </optgroup>
                  <optgroup label="Historic Decadal Landsat 5 &amp; 7 (1984 - 2012)">
                    <option value="2011::landsat_5_7">2011 (Landsat 5 &amp; 7 - 30m)</option>
                    <option value="2006::landsat_5_7">2006 (Landsat 5 &amp; 7 - 30m)</option>
                    <option value="2001::landsat_5_7">2001 (Landsat 5 &amp; 7 - 30m)</option>
                  </optgroup>
                </select>
                <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginTop: '4px' }}>
                  Supports Landsat 5, 7, 8, 9 (30m) &amp; Sentinel-2A / 2B (10m) Level-2A Surface Reflectance.
                </div>
              </div>

              <div className="form-group">
                <label className="form-label">Description (Optional)</label>
                <input
                  className="form-input"
                  placeholder="e.g. Agricultural and urban growth assessment"
                  value={newProjDesc}
                  onChange={(e) => setNewProjDesc(e.target.value)}
                />
              </div>

              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 10, marginTop: 8 }}>
                <button
                  type="button"
                  className="btn-secondary"
                  onClick={() => setShowNewProjectModal(false)}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="btn-primary"
                  disabled={loading}
                >
                  {loading ? <span className="spinner" /> : 'Create Project'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* CONFIGURE CLASSES & SAMPLING REQUIREMENTS MODAL */}
      {showClassesModal && (
        <div className="modal-backdrop">
          <div className="modal-content" style={{ maxWidth: '640px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <h3 style={{ fontFamily: 'var(--font-heading)', fontSize: 18, color: 'var(--text-main)' }}>
                ⚙️ Configure Study Area Classes & Sampling Requirements
              </h3>
              <button
                style={{ background: 'transparent', fontSize: 18, color: 'var(--text-muted)', cursor: 'pointer' }}
                onClick={() => setShowClassesModal(false)}
              >
                ✕
              </button>
            </div>
            <p style={{ fontSize: 12.5, color: 'var(--text-muted)', margin: 0 }}>
              Tailor land cover categories and minimum sample targets according to your study area landscape.
            </p>

            <div className="table-container" style={{ maxHeight: '340px' }}>
              <table className="custom-table">
                <thead>
                  <tr>
                    <th style={{ width: 45 }}>ID</th>
                    <th>Class Name</th>
                    <th style={{ width: 75 }}>Color</th>
                    <th style={{ width: 110 }}>Min Samples</th>
                    <th style={{ width: 45 }}>Action</th>
                  </tr>
                </thead>
                <tbody>
                  {Object.entries(editingClasses)
                    .sort((a, b) => Number(a[0]) - Number(b[0]))
                    .map(([cid, cinfo]) => (
                      <tr key={cid}>
                        <td style={{ fontWeight: 600 }}>{cid}</td>
                        <td>
                          <input
                            className="form-input"
                            style={{ padding: '4px 8px', fontSize: '12px' }}
                            value={cinfo.name || ''}
                            onChange={(e) => {
                              const val = e.target.value;
                              setEditingClasses((prev) => ({
                                ...prev,
                                [cid]: { ...prev[cid], name: val },
                              }));
                            }}
                          />
                        </td>
                        <td>
                          <input
                            type="color"
                            value={cinfo.color || '#10b981'}
                            onChange={(e) => {
                              const col = e.target.value;
                              setEditingClasses((prev) => ({
                                ...prev,
                                [cid]: { ...prev[cid], color: col },
                              }));
                            }}
                            style={{
                              width: 32,
                              height: 28,
                              border: 'none',
                              borderRadius: 4,
                              cursor: 'pointer',
                              background: 'transparent',
                            }}
                          />
                        </td>
                        <td>
                          <input
                            type="number"
                            min="5"
                            className="form-input"
                            style={{ padding: '4px 8px', fontSize: '12px', width: '70px' }}
                            value={cinfo.min_samples || 20}
                            onChange={(e) => {
                              const count = parseInt(e.target.value) || 20;
                              setEditingClasses((prev) => ({
                                ...prev,
                                [cid]: { ...prev[cid], min_samples: count },
                              }));
                            }}
                          />
                        </td>
                        <td>
                          <button
                            type="button"
                            onClick={() => handleRemoveClass(cid)}
                            title="Remove class"
                            style={{
                              background: 'transparent',
                              color: 'var(--accent-rose)',
                              fontSize: 14,
                              padding: '2px 6px',
                              borderRadius: 4,
                            }}
                          >
                            🗑️
                          </button>
                        </td>
                      </tr>
                    ))}
                </tbody>
              </table>
            </div>

            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <button
                type="button"
                className="btn-secondary"
                style={{ fontSize: 12, padding: '6px 12px' }}
                onClick={handleAddClass}
              >
                ➕ Add New Class
              </button>
              <button
                type="button"
                className="btn-secondary"
                style={{ fontSize: 12, padding: '6px 12px' }}
                onClick={handleResetToDefaultClasses}
              >
                ↺ Reset to TN 8-Class Defaults
              </button>
            </div>

            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 10, marginTop: 8 }}>
              <button
                type="button"
                className="btn-secondary"
                onClick={() => setShowClassesModal(false)}
              >
                Cancel
              </button>
              <button
                type="button"
                className="btn-primary"
                onClick={handleSaveClassesConfig}
                disabled={loading}
              >
                {loading ? <span className="spinner" /> : 'Save Class Scheme'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* 13. STUDY AREA PROJECT MANAGER & ARCHIVES MODAL */}
      {showProjectManagerModal && (
        <div
          className="modal-backdrop"
          onClick={(e) => {
            if (e.target === e.currentTarget) setShowProjectManagerModal(false);
          }}
        >
          <div className="pm-modal-content">
            {/* Header */}
            <div className="pm-header">
              <div className="pm-header-left">
                <div className="pm-header-icon">📁</div>
                <div>
                  <h3 className="pm-title">Study Area Project Manager</h3>
                  <p className="pm-subtitle">
                    Organize, archive, restore, and manage active GIS study area projects.
                  </p>
                </div>
              </div>
              <button
                className="btn-close"
                style={{ background: 'transparent', fontSize: 18, color: 'var(--text-muted)', cursor: 'pointer', border: 'none' }}
                onClick={() => setShowProjectManagerModal(false)}
              >
                ✕
              </button>
            </div>

            {/* Navigation Tabs & Filter Bar */}
            <div className="pm-tabs-bar">
              <div className="pm-tabs">
                <button
                  type="button"
                  className={`pm-tab-btn ${projectManagerTab === 'active' ? 'active' : ''}`}
                  onClick={() => setProjectManagerTab('active')}
                >
                  <span>Active Projects</span>
                  <span className="pm-tab-badge active-badge">{projects.length}</span>
                </button>
                <button
                  type="button"
                  className={`pm-tab-btn ${projectManagerTab === 'archived' ? 'active' : ''}`}
                  onClick={() => setProjectManagerTab('archived')}
                >
                  <span>Archived Projects</span>
                  <span className="pm-tab-badge archived-badge">{archivedProjects.length}</span>
                </button>
              </div>

              <input
                type="text"
                className="pm-search-input"
                placeholder="🔍 Search projects by name or district..."
                value={projectSearchTerm}
                onChange={(e) => setProjectSearchTerm(e.target.value)}
              />
            </div>

            {/* Projects List Container */}
            <div className="pm-projects-list">
              {projectManagerTab === 'active' ? (
                // ACTIVE PROJECTS TAB
                projects
                  .filter((p) => {
                    const q = projectSearchTerm.toLowerCase().trim();
                    if (!q) return true;
                    return (
                      p.name?.toLowerCase().includes(q) ||
                      p.district?.toLowerCase().includes(q) ||
                      String(p.target_year).includes(q)
                    );
                  })
                  .length === 0 ? (
                  <div className="pm-empty-state">
                    <span className="pm-empty-icon">🗂️</span>
                    <strong>No active projects found</strong>
                    <p style={{ margin: 0 }}>
                      {projectSearchTerm
                        ? 'No projects match your search query.'
                        : 'Create a new study area project or restore one from the archives.'}
                    </p>
                  </div>
                ) : (
                  projects
                    .filter((p) => {
                      const q = projectSearchTerm.toLowerCase().trim();
                      if (!q) return true;
                      return (
                        p.name?.toLowerCase().includes(q) ||
                        p.district?.toLowerCase().includes(q) ||
                        String(p.target_year).includes(q)
                      );
                    })
                    .map((p) => {
                      const isCurrent = currentProject?.id === p.id;
                      return (
                        <div
                          key={p.id}
                          className={`pm-project-card ${isCurrent ? 'is-current' : ''}`}
                        >
                          <div className="pm-proj-info">
                            <div className="pm-proj-title-row">
                              <span className="pm-proj-name">{p.name}</span>
                              <span className="pm-proj-badge-district">
                                🏛️ {p.district || 'General'}
                              </span>
                              {isCurrent && (
                                <span className="pm-active-tag">✓ Currently Active</span>
                              )}
                            </div>
                            <div className="pm-proj-meta-row">
                              <span className="pm-proj-meta-item">
                                📅 <b>{p.target_year}</b>
                              </span>
                              <span className="pm-proj-meta-item">
                                🛰️ {formatDatasetLabel(p.satellite_dataset)}
                              </span>
                              {p.area_ha && (
                                <span className="pm-proj-meta-item">
                                  📐 {Number(p.area_ha).toLocaleString()} ha
                                </span>
                              )}
                              <span
                                className={`pm-status-pill step-${p.has_classification ? 6 : p.has_samples ? 4 : p.has_boundary ? 2 : 1}`}
                              >
                                {p.has_classification
                                  ? '✅ Classified (Step 6/7)'
                                  : p.has_samples
                                  ? '🎯 Samples (Step 4)'
                                  : p.has_boundary
                                  ? '📐 Boundary (Step 2)'
                                  : '🆕 Setup (Step 1)'}
                              </span>
                            </div>
                          </div>

                          <div className="pm-actions">
                            {!isCurrent && (
                              <button
                                type="button"
                                className="pm-btn pm-btn-open"
                                onClick={() => {
                                  selectProject(p);
                                  setShowProjectManagerModal(false);
                                }}
                                title="Open this project in the workspace"
                              >
                                Open Project
                              </button>
                            )}
                            <button
                              type="button"
                              className="pm-btn pm-btn-archive"
                              onClick={() => handleArchiveProject(p)}
                              disabled={actionLoadingId === p.id}
                              title="Archive completed project to remove from active selector (all data preserved)"
                            >
                              📦 Archive
                            </button>
                            <button
                              type="button"
                              className="pm-btn pm-btn-delete"
                              onClick={() => {
                                setDeleteConfirmProject(p);
                                setDeleteConfirmInput('');
                              }}
                              disabled={actionLoadingId === p.id}
                              title="Permanently delete project and remove all files"
                            >
                              🗑️ Delete
                            </button>
                          </div>
                        </div>
                      );
                    })
                )
              ) : (
                // ARCHIVED PROJECTS TAB
                archivedProjects
                  .filter((p) => {
                    const q = projectSearchTerm.toLowerCase().trim();
                    if (!q) return true;
                    return (
                      p.name?.toLowerCase().includes(q) ||
                      p.district?.toLowerCase().includes(q) ||
                      String(p.target_year).includes(q)
                    );
                  })
                  .length === 0 ? (
                  <div className="pm-empty-state">
                    <span className="pm-empty-icon">📦</span>
                    <strong>No archived projects</strong>
                    <p style={{ margin: 0 }}>
                      {projectSearchTerm
                        ? 'No archived projects match your search query.'
                        : 'Completed projects you archive will be safely preserved here for future reference.'}
                    </p>
                  </div>
                ) : (
                  archivedProjects
                    .filter((p) => {
                      const q = projectSearchTerm.toLowerCase().trim();
                      if (!q) return true;
                      return (
                        p.name?.toLowerCase().includes(q) ||
                        p.district?.toLowerCase().includes(q) ||
                        String(p.target_year).includes(q)
                      );
                    })
                    .map((p) => (
                      <div key={p.id} className="pm-project-card">
                        <div className="pm-proj-info">
                          <div className="pm-proj-title-row">
                            <span className="pm-proj-name">{p.name}</span>
                            <span className="pm-proj-badge-district">
                              🏛️ {p.district || 'General'}
                            </span>
                            <span
                              style={{
                                fontSize: '10.5px',
                                fontWeight: 700,
                                padding: '2px 7px',
                                borderRadius: '4px',
                                background: 'rgba(245, 158, 11, 0.18)',
                                color: '#d97706',
                              }}
                            >
                              📦 Archived
                            </span>
                          </div>
                          <div className="pm-proj-meta-row">
                            <span className="pm-proj-meta-item">
                              📅 <b>{p.target_year}</b>
                            </span>
                            <span className="pm-proj-meta-item">
                              🛰️ {formatDatasetLabel(p.satellite_dataset)}
                            </span>
                            {p.area_ha && (
                              <span className="pm-proj-meta-item">
                                📐 {Number(p.area_ha).toLocaleString()} ha
                              </span>
                            )}
                            <span style={{ fontSize: '11px', color: 'var(--text-dim)' }}>
                              Archived: {p.archived_at ? new Date(p.archived_at).toLocaleDateString() : 'Yes'}
                            </span>
                          </div>
                        </div>

                        <div className="pm-actions">
                          <button
                            type="button"
                            className="pm-btn pm-btn-restore"
                            onClick={() => handleRestoreProject(p)}
                            disabled={actionLoadingId === p.id}
                            title="Restore project back to active selector"
                          >
                            ♻️ Restore to Active
                          </button>
                          <button
                            type="button"
                            className="pm-btn pm-btn-delete"
                            onClick={() => {
                              setDeleteConfirmProject(p);
                              setDeleteConfirmInput('');
                            }}
                            disabled={actionLoadingId === p.id}
                            title="Permanently delete project and remove all files"
                          >
                            🗑️ Delete Permanently
                          </button>
                        </div>
                      </div>
                    ))
                )
              )}
            </div>

            {/* Modal Footer */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderTop: '1px solid var(--border-subtle)', paddingTop: '12px' }}>
              <span style={{ fontSize: '11.5px', color: 'var(--text-muted)' }}>
                {projects.length} Active · {archivedProjects.length} Archived
              </span>
              <button
                type="button"
                className="btn-secondary"
                onClick={() => setShowProjectManagerModal(false)}
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}

      {/* 14. PERMANENT DELETE CONFIRMATION SAFEGUARD MODAL */}
      {deleteConfirmProject && (
        <div
          className="modal-backdrop"
          onClick={(e) => {
            if (e.target === e.currentTarget) setDeleteConfirmProject(null);
          }}
        >
          <div className="delete-confirm-modal">
            <div className="delete-confirm-header">
              <div className="delete-confirm-icon">⚠️</div>
              <div>
                <h3 className="delete-confirm-title">Confirm Permanent Project Deletion</h3>
                <p className="delete-confirm-desc">
                  Are you sure you want to permanently delete <strong>{deleteConfirmProject.name}</strong> ({deleteConfirmProject.district || 'General'}, {deleteConfirmProject.target_year})?
                </p>
              </div>
            </div>

            <div className="delete-warning-box">
              <strong>The following project data will be permanently erased:</strong>
              <ul>
                <li>Study area boundaries, uploaded shapefiles, and GeoJSON vectors</li>
                <li>Ground-truth training & validation reference samples</li>
                <li>Satellite composite configurations & Google Earth Engine tile cache</li>
                <li>Supervised classification models (RF & SVM) and accuracy confusion matrices</li>
                <li>All generated GeoTIFF rasters, high-res PNG map renders, CSV stats, and QGIS starter packages</li>
                <li>Project directory: <code>data/projects/{deleteConfirmProject.id}</code></li>
              </ul>
              <div style={{ marginTop: '8px', color: '#e11d48', fontWeight: 600 }}>
                ⚠️ This action is irreversible. All other study area projects will remain completely untouched.
              </div>
            </div>

            <div className="delete-input-group">
              <label className="delete-input-label">
                To confirm deletion, type <strong>DELETE</strong> or <strong>{deleteConfirmProject.name}</strong> below:
              </label>
              <input
                type="text"
                className="delete-confirm-input"
                placeholder="Type DELETE to confirm"
                value={deleteConfirmInput}
                onChange={(e) => setDeleteConfirmInput(e.target.value)}
                autoFocus
              />
            </div>

            <div className="delete-confirm-actions">
              <button
                type="button"
                className="btn-secondary"
                onClick={() => {
                  setDeleteConfirmProject(null);
                  setDeleteConfirmInput('');
                }}
              >
                Cancel
              </button>
              <button
                type="button"
                className="btn-danger-confirm"
                disabled={
                  deleteConfirmInput.trim().toUpperCase() !== 'DELETE' &&
                  deleteConfirmInput.trim() !== deleteConfirmProject.name
                }
                onClick={handleConfirmPermanentDelete}
              >
                {actionLoadingId === deleteConfirmProject.id ? (
                  <>
                    <span className="spinner" style={{ width: 12, height: 12 }} /> Deleting...
                  </>
                ) : (
                  '🗑️ Delete Project Permanently'
                )}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
