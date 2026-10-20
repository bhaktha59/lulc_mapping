import React, { useEffect, useRef, useState } from 'react';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';

// Fix default Leaflet icon paths
delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png',
  iconUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png',
  shadowUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png',
});

// Default regional map center
const DEFAULT_CENTER = [11.1271, 78.6569];
const DEFAULT_ZOOM = 8;

export default function MapViewer({
  boundaryGeojson = null,
  activeTileUrl = null,
  activeLayerName = 'Classified LULC Map',
  layerOpacity = 0.9,
  trainingPoints = [],
  validationPoints = [],
  showSamples = true,
  showBoundary = true,
  classes = {},
  theme = 'light',
}) {
  const mapContainerRef = useRef(null);
  const mapRef = useRef(null);
  const boundaryLayerRef = useRef(null);
  const tileLayerRef = useRef(null);
  const samplesLayerRef = useRef(null);
  const [cursorCoords, setCursorCoords] = useState({ lat: 11.1271, lng: 78.6569 });
  const [basemapType, setBasemapType] = useState('satellite'); // 'satellite' | 'osm'

  const basemapLayersRef = useRef({});

  // 1. Initialize Map
  useEffect(() => {
    if (!mapContainerRef.current || mapRef.current) return;

    const map = L.map(mapContainerRef.current, {
      center: DEFAULT_CENTER,
      zoom: DEFAULT_ZOOM,
      zoomControl: false,
      attributionControl: false,
    });
    mapRef.current = map;

    // Basemaps: Free, licensed data sources (ESRI World Imagery & OpenStreetMap)
    const satellite = L.tileLayer(
      'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
      {
        maxZoom: 19,
        attribution: 'Tiles &copy; <a href="https://www.esri.com/" target="_blank" rel="noopener noreferrer">Esri</a> &mdash; Source: Esri, i-cubed, USDA, USGS, AEX, GeoEye, Getmapping, Aerogrid, IGN, IGP, UPR-EGP, and the GIS User Community',
      }
    );

    const osm = L.tileLayer(
      'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',
      {
        maxZoom: 19,
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener noreferrer">OpenStreetMap</a> contributors',
      }
    );

    basemapLayersRef.current = { satellite, osm };
    satellite.addTo(map);

    L.control.zoom({ position: 'topright' }).addTo(map);
    L.control.attribution({ position: 'bottomleft', prefix: '<a href="https://leafletjs.com" target="_blank" rel="noopener noreferrer">Leaflet</a>' }).addTo(map);

    map.on('mousemove', (e) => {
      setCursorCoords({
        lat: Number(e.latlng.lat.toFixed(4)),
        lng: Number(e.latlng.lng.toFixed(4)),
      });
    });

    setTimeout(() => {
      if (mapRef.current) mapRef.current.invalidateSize();
    }, 200);

    return () => {
      if (mapRef.current) {
        mapRef.current.remove();
        mapRef.current = null;
      }
    };
  }, []);

  // 2. Basemap switcher
  useEffect(() => {
    if (!mapRef.current || !basemapLayersRef.current.satellite) return;
    const map = mapRef.current;
    const { satellite, osm } = basemapLayersRef.current;

    [satellite, osm].forEach((l) => {
      if (map.hasLayer(l)) map.removeLayer(l);
    });

    if (basemapType === 'satellite') satellite.addTo(map);
    else if (basemapType === 'osm') osm.addTo(map);
  }, [basemapType]);

  // 3. Update Study Area Boundary GeoJSON
  useEffect(() => {
    if (!mapRef.current) return;
    const map = mapRef.current;

    if (boundaryLayerRef.current) {
      map.removeLayer(boundaryLayerRef.current);
      boundaryLayerRef.current = null;
    }

    if (boundaryGeojson && showBoundary) {
      try {
        const geoLayer = L.geoJSON(boundaryGeojson, {
          style: {
            color: '#059669',
            weight: 3.5,
            opacity: 1,
            fillColor: '#10b981',
            fillOpacity: 0.08,
            dashArray: '6, 6',
          },
          onEachFeature: (feature, layer) => {
            const props = feature.properties || {};
            layer.bindPopup(`
              <div style="font-family: sans-serif; font-size: 13px; color: #111; line-height: 1.6; padding: 4px;">
                <strong style="color: #059669; font-size: 14px;">🗺️ Study Area Boundary</strong><br/>
                <b>Area:</b> ${(props.area_ha || 0).toLocaleString()} ha (~${props.area_sqkm || 0} km²)<br/>
                <b>Vertices:</b> ${props.vertex_count || 'N/A'}<br/>
                <b>CRS:</b> EPSG:4326 (WGS 84)
              </div>
            `);
          },
        }).addTo(map);

        boundaryLayerRef.current = geoLayer;
        const bounds = geoLayer.getBounds();
        if (bounds.isValid()) {
          map.fitBounds(bounds, { padding: [40, 40], maxZoom: 14 });
        }
      } catch (err) {
        console.error('Error rendering boundary GeoJSON:', err);
      }
    }
  }, [boundaryGeojson, showBoundary]);

  // 4. Update GEE Raster Tile Layer
  useEffect(() => {
    if (!mapRef.current) return;
    const map = mapRef.current;

    if (tileLayerRef.current) {
      map.removeLayer(tileLayerRef.current);
      tileLayerRef.current = null;
    }

    if (activeTileUrl) {
      const tile = L.tileLayer(activeTileUrl, {
        opacity: layerOpacity,
        maxZoom: 18,
      }).addTo(map);
      tileLayerRef.current = tile;
    }
  }, [activeTileUrl, layerOpacity]);

  // 5. Update Sample Points Markers with Dynamic Class Colors
  useEffect(() => {
    if (!mapRef.current) return;
    const map = mapRef.current;

    if (samplesLayerRef.current) {
      map.removeLayer(samplesLayerRef.current);
      samplesLayerRef.current = null;
    }

    if (!showSamples) return;

    const group = L.layerGroup();

    const getClassColor = (cid) => {
      const info = classes[cid] || classes[String(cid)];
      return info?.color || '#10b981';
    };

    const getClassName = (cid) => {
      const info = classes[cid] || classes[String(cid)];
      return info?.name || `Class ${cid}`;
    };

    // Training points (Solid circle)
    trainingPoints.forEach((pt) => {
      const color = getClassColor(pt.class_id);
      const name = getClassName(pt.class_id);
      const circle = L.circleMarker([pt.lat, pt.lon], {
        radius: 5,
        fillColor: color,
        color: '#ffffff',
        weight: 1.5,
        opacity: 1,
        fillOpacity: 0.95,
      }).bindTooltip(`<b>Training Sample:</b> ${name} (ID: ${pt.class_id})`);
      group.addLayer(circle);
    });

    // Validation points (Ring circle with white center)
    validationPoints.forEach((pt) => {
      const color = getClassColor(pt.class_id);
      const name = getClassName(pt.class_id);
      const circle = L.circleMarker([pt.lat, pt.lon], {
        radius: 6,
        fillColor: '#ffffff',
        color: color,
        weight: 3,
        opacity: 1,
        fillOpacity: 0.85,
      }).bindTooltip(`<b>Validation Holdout:</b> ${name} (ID: ${pt.class_id})`);
      group.addLayer(circle);
    });

    if (trainingPoints.length > 0 || validationPoints.length > 0) {
      group.addTo(map);
      samplesLayerRef.current = group;
    }
  }, [trainingPoints, validationPoints, showSamples, classes]);

  const isLight = theme === 'light';

  return (
    <div style={{ position: 'relative', width: '100%', height: '100%', overflow: 'hidden' }}>
      <div ref={mapContainerRef} style={{ width: '100%', height: '100%', background: isLight ? '#e2e8f0' : '#0a0e17' }} />

      {/* Floating Map Controls Toolbar (Non-overlapping responsive container) */}
      <div
        style={{
          position: 'absolute',
          top: 14,
          left: 14,
          zIndex: 1000,
          display: 'flex',
          alignItems: 'center',
          gap: 10,
          flexWrap: 'wrap',
          maxWidth: 'calc(100% - 120px)',
        }}
      >
        {/* Basemap Options: Satellite & Street Only (Free, compliant data sources) */}
        <div
          style={{
            background: isLight ? 'rgba(255, 255, 255, 0.94)' : 'rgba(15, 23, 42, 0.90)',
            backdropFilter: 'blur(8px)',
            border: isLight ? '1px solid #cbd5e1' : '1px solid rgba(255, 255, 255, 0.12)',
            borderRadius: 8,
            padding: '3px',
            display: 'flex',
            gap: 4,
            boxShadow: isLight ? '0 2px 8px rgba(0, 0, 0, 0.08)' : '0 4px 12px rgba(0, 0, 0, 0.4)',
          }}
        >
          <button
            onClick={() => setBasemapType('satellite')}
            style={{
              padding: '6px 13px',
              fontSize: '12px',
              fontWeight: 600,
              borderRadius: 6,
              border: 'none',
              cursor: 'pointer',
              background: basemapType === 'satellite' ? '#10b981' : 'transparent',
              color: basemapType === 'satellite' ? '#ffffff' : (isLight ? '#475569' : '#94a3b8'),
              transition: 'all 0.15s ease',
              display: 'flex',
              alignItems: 'center',
              gap: 5,
            }}
            title="Esri World Imagery (Satellite) — Free global satellite imagery (Esri, USGS, USDA, GIS User Community)"
          >
            🛰️ Satellite
          </button>
          <button
            onClick={() => setBasemapType('osm')}
            style={{
              padding: '6px 13px',
              fontSize: '12px',
              fontWeight: 600,
              borderRadius: 6,
              border: 'none',
              cursor: 'pointer',
              background: basemapType === 'osm' ? '#10b981' : 'transparent',
              color: basemapType === 'osm' ? '#ffffff' : (isLight ? '#475569' : '#94a3b8'),
              transition: 'all 0.15s ease',
              display: 'flex',
              alignItems: 'center',
              gap: 5,
            }}
            title="OpenStreetMap (Street) — Free collaborative street map (© OpenStreetMap contributors, ODbL)"
          >
            🗺️ Street
          </button>
        </div>

        {/* Active Layer Badge */}
        {activeTileUrl && (
          <div
            style={{
              background: isLight ? 'rgba(255, 255, 255, 0.94)' : 'rgba(15, 23, 42, 0.90)',
              backdropFilter: 'blur(8px)',
              border: '1px solid rgba(16, 185, 129, 0.35)',
              borderRadius: 8,
              padding: '6px 12px',
              display: 'flex',
              alignItems: 'center',
              gap: 8,
              fontSize: '12px',
              color: isLight ? '#059669' : '#34d399',
              fontWeight: 600,
              boxShadow: isLight ? '0 2px 8px rgba(0, 0, 0, 0.08)' : '0 4px 12px rgba(0, 0, 0, 0.3)',
            }}
          >
            <span style={{ width: 8, height: 8, borderRadius: '50%', background: '#10b981', display: 'inline-block' }} />
            <span>Active: <b>{activeLayerName}</b> ({Math.round(layerOpacity * 100)}% Opacity)</span>
          </div>
        )}
      </div>

      {/* Coordinate & Status Bar */}
      <div
        style={{
          position: 'absolute',
          bottom: 12,
          right: 12,
          zIndex: 1000,
          background: isLight ? 'rgba(255, 255, 255, 0.92)' : 'rgba(15, 23, 42, 0.88)',
          backdropFilter: 'blur(8px)',
          border: isLight ? '1px solid #cbd5e1' : '1px solid rgba(255, 255, 255, 0.08)',
          borderRadius: 6,
          padding: '4px 10px',
          fontSize: '11px',
          color: isLight ? '#475569' : '#94a3b8',
          fontFamily: 'JetBrains Mono, monospace',
          boxShadow: isLight ? '0 1px 4px rgba(0, 0, 0, 0.05)' : 'none',
        }}
      >
        Lat: {cursorCoords.lat.toFixed(4)}° N | Lon: {cursorCoords.lng.toFixed(4)}° E | EPSG:4326
      </div>
    </div>
  );
}
