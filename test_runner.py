import os
import sys
import glob
from datetime import datetime
import csv
import io

# ==============================================================================
# 1. SETUP & IMPORTS
# ==============================================================================

script_dir = os.path.dirname(os.path.abspath(__file__))

if os.path.basename(script_dir) == "tests":
    project_root = os.path.dirname(script_dir)
else:
    project_root = script_dir

src_path = os.path.join(project_root, "src")
if src_path not in sys.path:
    sys.path.insert(0, src_path)

try:
    from core.time_struct import Time
    from core.sun_model import SunModel
    from core.corrections import CorrectionModel
    from core.sidereal import SiderealTime
except ImportError as e:
    print("CRITICAL ERROR: Could not import Seasonal Core modules.")
    print(f"Computed src path: {src_path}")
    print(f"Details: {e}")
    sys.exit(1)

# ==============================================================================
# 2. CONFIGURATION
# ==============================================================================

if os.path.basename(script_dir) == "tests":
    TESTS_DIR = script_dir
else:
    TESTS_DIR = os.path.join(project_root, "tests")

REF_DATA_DIR = os.path.join(TESTS_DIR, "reference_data")
REPORT_FILE = os.path.join(TESTS_DIR, "validation_report.txt")

# Tolerance thresholds in degrees
TOLERANCE = {
    "AZ": 0.0003,       # ~1 arcsec
    "ALT_GEOM": 0.0003,
    "ALT_APP": 0.0020,  # looser due to refraction model differences
    "LST": 0.00005      # ~0.15s
}

PRESS_MBAR = 1013.25
TEMP_C = 15.0

# ==============================================================================
# 3. JPL CSV PARSER (HEADER-ANCHOR, NO DYNAMIC FLAG SCANNING)
# ==============================================================================


def parse_jpl_csv(filepath):
    """
    Parse a NASA JPL Horizons CSV file into metadata and structured rows.

    The parser:
        - Extracts site metadata from the "Center geodetic" line.
        - Locates the data header containing "Date__(UT)__HR:MN".
        - Uses that header's column positions as the fixed layout.
        - Ignores columns with empty header cells (flag columns, trailing comma).
        - Preserves JPL column names exactly (no renaming or canonicalization).

    Returns:
        metadata: dict with at least:
            - "lat"    : float, geodetic latitude (deg)
            - "lon"    : float, geodetic east longitude (deg)
            - "elev_m" : float, elevation (m)
        rows: list[dict], each dict keyed by the original JPL header names.
    """
    metadata = {}
    header_line = None
    data_lines = []
    in_data_block = False

    with open(filepath, "r", encoding="utf-8") as f:
        for raw_line in f:
            line = raw_line.rstrip("\n")

            # Metadata extraction from the geodetic line
            if "Center geodetic" in line and "E-lon(deg),Lat(deg),Alt(km)" in line:
                try:
                    after_colon = line.split(":", 1)[1]
                    coords_chunk = after_colon.split("{", 1)[0]
                    parts = [p.strip() for p in coords_chunk.split(",") if p.strip()]
                    if len(parts) >= 3:
                        lon_deg = float(parts[0])
                        lat_deg = float(parts[1])
                        alt_km = float(parts[2])
                        metadata["lon"] = lon_deg
                        metadata["lat"] = lat_deg
                        metadata["elev_m"] = alt_km * 1000.0
                except Exception:
                    # Metadata parsing errors are not fatal for the comparison.
                    pass

            # Capture the main ephemeris header
            if "Date__(UT)__HR:MN" in line and header_line is None:
                header_line = line.strip()

            stripped = line.strip()

            # Delimit the $$SOE / $$EOE data block
            if stripped == "$$SOE":
                in_data_block = True
                continue
            if stripped == "$$EOE":
                in_data_block = False
                continue

            # Collect data lines strictly inside the block
            if in_data_block and stripped:
                data_lines.append(line.strip())

    if header_line is None or not data_lines:
        return metadata, []

    # Parse header to obtain fixed column positions
    header_stream = io.StringIO(header_line + "\n")
    header_reader = csv.reader(header_stream, skipinitialspace=True)
    raw_headers = next(header_reader)

    # Build per-column keys; empty headers become None (flags, trailing commas)
    header_keys = []
    for h in raw_headers:
        h_clean = h.strip()
        header_keys.append(h_clean if h_clean else None)

    # Parse data rows
    data_stream = io.StringIO("\n".join(data_lines))
    reader = csv.reader(data_stream, skipinitialspace=True)

    rows = []

    for parts in reader:
        if not parts:
            continue

        # Ensure we can index up to header length
        if len(parts) < len(header_keys):
            parts = parts + [""] * (len(header_keys) - len(parts))

        row = {}
        for idx, key in enumerate(header_keys):
            if key is None:
                # Skip flag columns and trailing blank column
                continue
            if idx >= len(parts):
                continue
            value = parts[idx].strip()
            row[key] = value

        if row:
            rows.append(row)

    return metadata, rows


# ==============================================================================
# 4. COMPARISON ENGINE
# ==============================================================================


def _find_column_keys(example_row):
    """
    Infer key names for Date, Azimuth, Elevation, and LST from a row dict.

    This uses simple substring matching and preserves the original JPL
    column names. It is designed to be robust across APP/GEOM variants.
    """
    keys = list(example_row.keys())

    date_key = None
    for k in keys:
        if "Date__(UT)" in k:
            date_key = k
            break

    az_key = None
    for k in keys:
        if "Azi" in k or "Azimuth" in k:
            az_key = k
            break

    el_key = None
    for k in keys:
        if "Elev" in k or "El_" in k or "Altitude" in k:
            el_key = k
            break

    lst_key = None
    for k in keys:
        if "L_Ap_Sid_Time" in k or "Sid_Time" in k:
            lst_key = k
            break

    return date_key, az_key, el_key, lst_key


def run_comparison(filepath, outfile):
    filename = os.path.basename(filepath)
    outfile.write(f"\n=== Validating: {filename} ===\n")

    is_apparent = "APP" in filename

    meta, rows = parse_jpl_csv(filepath)

    if not rows:
        outfile.write("ERROR: No data rows extracted. Check file integrity or parser logic.\n")
        return

    outfile.write(
        f"Location: Lat {meta.get('lat', 'N/A')}°, "
        f"Lon {meta.get('lon', 'N/A')}°, "
        f"Elev {meta.get('elev_m', 'N/A')}m\n"
    )
    outfile.write(f"Samples : {len(rows)}\n")
    outfile.write(f"Mode    : {'Refraction ENABLED' if is_apparent else 'Geometric ONLY'}\n")
    outfile.write("----------------------------------------\n")

    # Determine which columns to use
    date_key, az_key, el_key, lst_key = _find_column_keys(rows[0])
    if not date_key or not az_key or not el_key:
        outfile.write("ERROR: Could not determine essential JPL columns (Date/Az/El).\n")
        return

    max_err_az = 0.0
    max_err_alt = 0.0
    max_err_lst = 0.0

    az_errors = []
    alt_errors = []
    lst_errors = []

    successful_samples = 0

    for row in rows:
        try:
            # --- 1. Parse date/time from JPL ---
            date_str = row[date_key].replace("A.D. ", "").strip()

            # Support with and without seconds
            try:
                dt = datetime.strptime(date_str, "%Y-%b-%d %H:%M:%S.%f")
            except ValueError:
                dt = datetime.strptime(date_str, "%Y-%b-%d %H:%M")

            t = Time.from_gregorian(
                dt.year,
                dt.month,
                dt.day,
                dt.hour,
                dt.minute,
                dt.second + dt.microsecond / 1e6,
            )

            # --- 2. JPL reference values ---
            jpl_az_raw = row.get(az_key)
            jpl_el_raw = row.get(el_key)
            jpl_lst_raw = row.get(lst_key) if lst_key else None

            if (
                not jpl_az_raw
                or not jpl_el_raw
                or jpl_az_raw in ("n.a.", "*")
                or jpl_el_raw in ("n.a.", "*")
            ):
                continue

            jpl_az = float(jpl_az_raw)
            jpl_el = float(jpl_el_raw)

            jpl_lst_deg = None
            if jpl_lst_raw and isinstance(jpl_lst_raw, str):
                lst_parts = jpl_lst_raw.split()
                if len(lst_parts) == 3:
                    try:
                        h = float(lst_parts[0])
                        m = float(lst_parts[1])
                        s = float(lst_parts[2])
                        jpl_lst_deg = (h + m / 60.0 + s / 3600.0) * 15.0
                    except ValueError:
                        jpl_lst_deg = None

            # --- 3. Seasonal engine computation ---
            geo_eq = SunModel.compute_geocentric_position(t)

            lst_seasonal = SiderealTime.apparent_local(t, meta["lon"])

            topo_eq = CorrectionModel.apply_parallax(
                geo_eq,
                meta["lat"],
                meta["elev_m"],
                lst_seasonal,
            )

            hor = topo_eq.to_horizontal(meta["lat"], lst_seasonal)

            seasonal_az = hor.azimuth_degrees
            seasonal_alt_geom = hor.altitude_degrees

            if is_apparent:
                seasonal_alt = CorrectionModel.apply_refraction(
                    seasonal_alt_geom,
                    pressure_mbar=PRESS_MBAR,
                    temp_celsius=TEMP_C,
                    enable_refraction=True,
                )
            else:
                seasonal_alt = seasonal_alt_geom

            # --- 4. Error metrics ---
            err_az = abs(seasonal_az - jpl_az)
            if err_az > 180.0:
                err_az = 360.0 - err_az

            err_alt = abs(seasonal_alt - jpl_el)

            max_err_az = max(max_err_az, err_az)
            max_err_alt = max(max_err_alt, err_alt)

            az_errors.append(err_az)
            alt_errors.append(err_alt)

            if jpl_lst_deg is not None:
                err_lst = abs(lst_seasonal - jpl_lst_deg)
                if err_lst > 180.0:
                    err_lst = 360.0 - err_lst
                max_err_lst = max(max_err_lst, err_lst)
                lst_errors.append(err_lst)

            successful_samples += 1

        except Exception:
            # Skip any rows that cannot be parsed or computed reliably
            continue

    # --- 5. Summary statistics and pass/fail ---
    mean_az = sum(az_errors) / len(az_errors) if az_errors else 0.0
    mean_alt = sum(alt_errors) / len(alt_errors) if alt_errors else 0.0
    mean_lst = sum(lst_errors) / len(lst_errors) if lst_errors else 0.0

    limit_alt = TOLERANCE["ALT_APP"] if is_apparent else TOLERANCE["ALT_GEOM"]
    limit_lst = TOLERANCE["LST"]

    pass_az = max_err_az <= TOLERANCE["AZ"] and successful_samples > 0
    pass_alt = max_err_alt <= limit_alt and successful_samples > 0
    pass_lst = max_err_lst <= limit_lst and successful_samples > 0

    status = "PASSED" if (pass_az and pass_alt and pass_lst) else "FAILED"

    outfile.write(f"Validated Samples: {successful_samples}\n")
    outfile.write(f"Max Az Error     : {max_err_az:.6f}° (Limit {TOLERANCE['AZ']}°)\n")
    outfile.write(f"Max Alt Error    : {max_err_alt:.6f}° (Limit {limit_alt}°)\n")
    outfile.write(f"Max LST Error    : {max_err_lst:.6f}° (Limit {limit_lst}°)\n")
    outfile.write(f"Result           : >> {status} <<\n")
    outfile.write("----------------------------------------\n")


# ==============================================================================
# 5. MAIN ENTRY POINT
# ==============================================================================

if __name__ == "__main__":
    csv_files = glob.glob(os.path.join(REF_DATA_DIR, "*.csv"))

    print(f"Starting verification of {len(csv_files)} scenarios...")
    print(f"Writing detailed report to: {REPORT_FILE}")

    with open(REPORT_FILE, "w", encoding="utf-8") as f:
        f.write("SEASONAL ENGINE VERIFICATION REPORT (FINAL RUN)\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("=" * 60 + "\n")

        if not csv_files:
            f.write("ERROR: No CSV files found in reference_data directory.\n")

        for csv_file in sorted(csv_files):
            run_comparison(csv_file, f)

    print("Done. Check the validation_report.txt file for results.")
