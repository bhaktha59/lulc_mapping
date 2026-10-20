"""
Shapefile Service for Tamil Nadu LULC Mapping Workflow.
Extracts zipped ESRI Shapefiles (.zip with .shp, .shx, .dbf, .prj), parses polygons,
handles CRS reprojection to WGS 84 (EPSG:4326), computes boundary metrics, and converts to GeoJSON.
"""

import os
import zipfile
import json
import math
import struct


def utm44n_to_wgs84(easting, northing):
    """
    Direct ellipsoidal projection from UTM Zone 44N (covers Tamil Nadu) to WGS 84 (lat, lon).
    WGS 84 ellipsoid parameters: a = 6378137.0, f = 1/298.257223563.
    """
    a = 6378137.0
    f = 1 / 298.257223563
    e2 = 2 * f - f * f
    e_prime_sq = e2 / (1 - e2)
    k0 = 0.9996
    lon0 = math.radians(81.0)  # UTM Zone 44 central meridian is 81° E

    x = easting - 500000.0
    y = northing

    m = y / k0
    mu = m / (a * (1 - e2 / 4 - 3 * e2 * e2 / 64 - 5 * e2 * e2 * e2 / 256))

    e1 = (1 - math.sqrt(1 - e2)) / (1 + math.sqrt(1 - e2))
    j1 = 3 * e1 / 2 - 27 * e1**3 / 32
    j2 = 21 * e1**2 / 16 - 55 * e1**4 / 32
    j3 = 151 * e1**3 / 96
    j4 = 1097 * e1**4 / 512

    fp = mu + j1 * math.sin(2 * mu) + j2 * math.sin(4 * mu) + j3 * math.sin(6 * mu) + j4 * math.sin(8 * mu)

    sin_fp = math.sin(fp)
    cos_fp = math.cos(fp)
    tan_fp = math.tan(fp)

    c1 = e_prime_sq * cos_fp * cos_fp
    t1 = tan_fp * tan_fp
    n1 = a / math.sqrt(1 - e2 * sin_fp * sin_fp)
    r1 = a * (1 - e2) / math.pow(1 - e2 * sin_fp * sin_fp, 1.5)
    d = x / (n1 * k0)

    lat = fp - (n1 * tan_fp / r1) * (
        d * d / 2
        - (5 + 3 * t1 + 10 * c1 - 4 * c1 * c1 - 9 * e_prime_sq) * math.pow(d, 4) / 24
        + (61 + 90 * t1 + 298 * c1 + 45 * t1 * t1 - 252 * e_prime_sq - 3 * c1 * c1) * math.pow(d, 6) / 720
    )

    lon = lon0 + (
        d
        - (1 + 2 * t1 + c1) * math.pow(d, 3) / 6
        + (5 - 2 * c1 + 28 * t1 - 3 * c1 * c1 + 8 * e_prime_sq + 24 * t1 * t1) * math.pow(d, 5) / 120
    ) / cos_fp

    return math.degrees(lon), math.degrees(lat)


def calculate_polygon_area_ha(coordinates):
    """
    Computes geodesic polygon area in hectares using spherical earth model.
    """
    radius = 6378137.0
    area = 0.0

    if not coordinates or len(coordinates) < 3:
        return 0.0

    ring = coordinates
    if ring[0] != ring[-1]:
        ring = ring + [ring[0]]

    for i in range(len(ring) - 1):
        p1 = ring[i]
        p2 = ring[i + 1]
        area += math.radians(p2[0] - p1[0]) * (2 + math.sin(math.radians(p1[1])) + math.sin(math.radians(p2[1])))

    area = abs(area * radius * radius / 2.0)
    return round(area / 10000.0, 2)  # Convert square meters to hectares


import shutil
import io


def extract_clean_zip_bytes(raw_bytes: bytes) -> bytes:
    """
    Ensures raw bytes represent clean ZIP file bytes, stripping any extraneous
    multipart boundaries or HTTP wrapper headers if present.
    """
    if not raw_bytes:
        return b""
    if raw_bytes.startswith(b"PK\x03\x04"):
        return raw_bytes
    idx = raw_bytes.find(b"PK\x03\x04")
    if idx != -1:
        eocd_pos = raw_bytes.rfind(b"PK\x05\x06")
        if eocd_pos != -1 and eocd_pos >= idx:
            if len(raw_bytes) >= eocd_pos + 22:
                comment_len = int.from_bytes(raw_bytes[eocd_pos + 20 : eocd_pos + 22], "little")
                end_pos = eocd_pos + 22 + comment_len
                if end_pos <= len(raw_bytes):
                    return raw_bytes[idx:end_pos]
            return raw_bytes[idx:]
        return raw_bytes[idx:]
    return raw_bytes


def parse_shp_file_pure_python(shp_path):
    """
    Pure Python parser for ESRI Shapefile (.shp).
    Reads polygon records (Shape Type 5 = Polygon, 15 = PolygonZ, 25 = PolygonM)
    and converts to GeoJSON geometry dictionary.
    """
    with open(shp_path, "rb") as f:
        # 100-byte main file header
        header = f.read(100)
        if len(header) < 100:
            raise ValueError("Invalid ESRI Shapefile header: file is too small.")
        file_code, _, _, _, _, _, file_length = struct.unpack(">7i", header[:28])
        version, shape_type = struct.unpack("<2i", header[28:36])

        features = []
        while True:
            rec_head = f.read(8)
            if len(rec_head) < 8:
                break
            rec_num, content_len = struct.unpack(">2i", rec_head)
            rec_data = f.read(content_len * 2)
            if len(rec_data) < 4:
                break

            rec_shape_type = struct.unpack("<i", rec_data[:4])[0]

            # Shape Type 5 = Polygon, 15 = PolygonZ, 25 = PolygonM
            if rec_shape_type in (5, 15, 25):
                num_parts, num_points = struct.unpack("<2i", rec_data[36:44])
                parts = struct.unpack(f"<{num_parts}i", rec_data[44 : 44 + 4 * num_parts])
                points_offset = 44 + 4 * num_parts

                points = []
                for pt_idx in range(num_points):
                    px, py = struct.unpack("<2d", rec_data[points_offset + pt_idx * 16 : points_offset + (pt_idx + 1) * 16])
                    points.append((px, py))

                # Split rings by part indices
                parts_indices = list(parts) + [num_points]
                rings = []
                for p_i in range(len(parts_indices) - 1):
                    ring_pts = points[parts_indices[p_i] : parts_indices[p_i + 1]]
                    if ring_pts:
                        rings.append(ring_pts)

                if rings:
                    features.append(rings)

        if not features:
            raise ValueError(f"No polygon features found in Shapefile (Shape Type: {shape_type}). Only polygon boundaries are supported.")

        # Determine if coordinates are UTM or WGS 84
        sample_x, sample_y = features[0][0][0]
        is_utm = sample_x > 1000.0 or sample_y > 1000.0

        geojson_polygons = []
        for poly_rings in features:
            converted_rings = []
            for ring in poly_rings:
                converted_ring = []
                for pt_x, pt_y in ring:
                    if is_utm:
                        c_lon, c_lat = utm44n_to_wgs84(pt_x, pt_y)
                    else:
                        c_lon, c_lat = pt_x, pt_y
                    converted_ring.append([round(c_lon, 6), round(c_lat, 6)])
                converted_rings.append(converted_ring)
            geojson_polygons.append(converted_rings)

        if len(geojson_polygons) == 1:
            geometry = {
                "type": "Polygon",
                "coordinates": geojson_polygons[0],
            }
        else:
            geometry = {
                "type": "MultiPolygon",
                "coordinates": geojson_polygons,
            }

        return geometry, is_utm


def process_shapefile_zip(zip_file_bytes, target_dir):
    """
    Extracts uploaded zip file, identifies .shp and related components (.shx, .dbf, .prj),
    validates file completeness, supports nested directories, handles projection,
    computes boundary metrics, and saves clean boundary.geojson.
    """
    clean_bytes = extract_clean_zip_bytes(zip_file_bytes)
    if not clean_bytes:
        raise ValueError("The uploaded file is empty. Please provide a valid ESRI Shapefile ZIP archive.")

    os.makedirs(target_dir, exist_ok=True)
    temp_extract = os.path.join(target_dir, "extracted_shp")
    if os.path.exists(temp_extract):
        shutil.rmtree(temp_extract, ignore_errors=True)
    os.makedirs(temp_extract, exist_ok=True)

    zip_path = os.path.join(target_dir, "uploaded_boundary.zip")
    with open(zip_path, "wb") as f:
        f.write(clean_bytes)

    try:
        with zipfile.ZipFile(zip_path, "r") as zf:
            zf.extractall(temp_extract)
    except zipfile.BadZipFile as bz:
        raise ValueError("The uploaded file is not a valid ZIP archive or is corrupted. Please upload a standard .zip archive.")

    # Locate all .shp files across root or any nested subdirectories
    # Ignore macOS metadata, hidden files, and temporary files
    shp_candidates = []
    for root, _, files in os.walk(temp_extract):
        if "__MACOSX" in root:
            continue
        for fl in files:
            if fl.startswith(".") or fl.startswith("._"):
                continue
            if fl.lower().endswith(".shp"):
                base_name = os.path.splitext(fl)[0]
                shp_candidates.append((root, base_name, os.path.join(root, fl)))

    if not shp_candidates:
        raise ValueError(
            "Study area shapefile missing: No ESRI '.shp' file was found in the uploaded ZIP archive. "
            "Please ensure your ZIP file contains the study area boundary (.shp, .shx, .dbf, .prj)."
        )

    # For each candidate, check companion components (.shx, .dbf, .prj)
    selected_candidate = None
    missing_by_candidate = {}

    for root, base_name, full_shp in shp_candidates:
        dir_files = [f for f in os.listdir(root) if not f.startswith(".") and not f.startswith("._")]

        found_shx = None
        found_dbf = None
        found_prj = None

        for f in dir_files:
            f_base, f_ext = os.path.splitext(f)
            if f_base.lower() == base_name.lower():
                ext_lower = f_ext.lower()
                if ext_lower == ".shx":
                    found_shx = os.path.join(root, f)
                elif ext_lower == ".dbf":
                    found_dbf = os.path.join(root, f)
                elif ext_lower == ".prj":
                    found_prj = os.path.join(root, f)

        missing = []
        if not found_shx:
            missing.append(".shx (shape index file)")
        if not found_dbf:
            missing.append(".dbf (attribute table)")

        if not missing:
            selected_candidate = {
                "root": root,
                "base_name": base_name,
                "shp": full_shp,
                "shx": found_shx,
                "dbf": found_dbf,
                "prj": found_prj,
            }
            break
        else:
            missing_by_candidate[base_name] = missing

    if not selected_candidate:
        first_base = list(missing_by_candidate.keys())[0]
        missing_list = ", ".join(missing_by_candidate[first_base])
        raise ValueError(
            f"Shapefile '{first_base}' is incomplete. Missing required component(s): {missing_list}. "
            "A valid ESRI shapefile requires at least .shp, .shx, and .dbf files."
        )

    # Copy to a normalized folder with uniform lowercase names to prevent case sensitivity issues
    norm_dir = os.path.join(target_dir, "normalized_shp")
    if os.path.exists(norm_dir):
        shutil.rmtree(norm_dir, ignore_errors=True)
    os.makedirs(norm_dir, exist_ok=True)

    norm_shp = os.path.join(norm_dir, "study_area.shp")
    norm_shx = os.path.join(norm_dir, "study_area.shx")
    norm_dbf = os.path.join(norm_dir, "study_area.dbf")

    shutil.copy2(selected_candidate["shp"], norm_shp)
    shutil.copy2(selected_candidate["shx"], norm_shx)
    shutil.copy2(selected_candidate["dbf"], norm_dbf)

    norm_prj = None
    if selected_candidate["prj"] and os.path.exists(selected_candidate["prj"]):
        norm_prj = os.path.join(norm_dir, "study_area.prj")
        shutil.copy2(selected_candidate["prj"], norm_prj)

    # Check projection from PRJ if present
    is_utm = False
    if norm_prj and os.path.exists(norm_prj):
        try:
            with open(norm_prj, "r", encoding="utf-8", errors="ignore") as pf:
                prj_text = pf.read().upper()
                if "44N" in prj_text or "UTM" in prj_text or "32644" in prj_text:
                    is_utm = True
                elif "WGS_1984" in prj_text or "4326" in prj_text:
                    is_utm = False
        except Exception:
            pass

    # Read geometry (Try pyshp first, fallback to pure Python parser)
    geometry = None

    try:
        import shapefile

        sf = shapefile.Reader(norm_shp)
        geojson_dict = sf.__geo_interface__
        if geojson_dict.get("features"):
            geometry = geojson_dict["features"][0]["geometry"]
            sample_pt = geometry["coordinates"][0][0]
            # Check coordinate magnitude
            if sample_pt[0] > 1000.0 or sample_pt[1] > 1000.0:
                is_utm = True
                if geometry["type"] == "Polygon":
                    new_coords = []
                    for ring in geometry["coordinates"]:
                        new_coords.append([list(utm44n_to_wgs84(p[0], p[1])) for p in ring])
                    geometry["coordinates"] = new_coords
                elif geometry["type"] == "MultiPolygon":
                    new_multipoly = []
                    for poly in geometry["coordinates"]:
                        new_poly = []
                        for ring in poly:
                            new_poly.append([list(utm44n_to_wgs84(p[0], p[1])) for p in ring])
                        new_multipoly.append(new_poly)
                    geometry["coordinates"] = new_multipoly
    except Exception:
        geometry, is_utm = parse_shp_file_pure_python(norm_shp)

    if not geometry:
        geometry, is_utm = parse_shp_file_pure_python(norm_shp)

    # Calculate bounding box & area
    coords_list = []
    if geometry["type"] == "Polygon":
        coords_list = geometry["coordinates"][0]
    elif geometry["type"] == "MultiPolygon":
        coords_list = geometry["coordinates"][0][0]

    min_lon = min(pt[0] for pt in coords_list)
    max_lon = max(pt[0] for pt in coords_list)
    min_lat = min(pt[1] for pt in coords_list)
    max_lat = max(pt[1] for pt in coords_list)

    center_lon = round((min_lon + max_lon) / 2.0, 6)
    center_lat = round((min_lat + max_lat) / 2.0, 6)

    area_ha = calculate_polygon_area_ha(coords_list)
    area_sqkm = round(area_ha / 100.0, 2)

    # Prepare standard GeoJSON FeatureCollection
    geojson_fc = {
        "type": "FeatureCollection",
        "crs": {
            "type": "name",
            "properties": {"name": "urn:ogc:def:crs:OGC:1.3:CRS84"},
        },
        "features": [
            {
                "type": "Feature",
                "properties": {
                    "source_name": selected_candidate["base_name"],
                    "area_ha": area_ha,
                    "area_sqkm": area_sqkm,
                    "original_crs": "UTM Zone 44N" if is_utm else "WGS 84 (EPSG:4326)",
                    "target_crs": "EPSG:4326",
                    "vertex_count": len(coords_list),
                    "has_prj": norm_prj is not None,
                },
                "geometry": geometry,
            }
        ],
    }

    out_geojson_path = os.path.join(target_dir, "boundary.geojson")
    with open(out_geojson_path, "w", encoding="utf-8") as f:
        json.dump(geojson_fc, f, indent=2)

    return {
        "status": "success",
        "message": f"Shapefile '{selected_candidate['base_name']}' successfully extracted and boundary established.",
        "shapefile_name": selected_candidate["base_name"],
        "geometry": geometry,
        "geojson_path": out_geojson_path,
        "area_ha": area_ha,
        "area_sqkm": area_sqkm,
        "bounds": [
            [round(min_lat, 6), round(min_lon, 6)],
            [round(max_lat, 6), round(max_lon, 6)],
        ],
        "center": [center_lat, center_lon],
        "vertex_count": len(coords_list),
        "crs": "EPSG:4326",
        "has_prj": norm_prj is not None,
    }

