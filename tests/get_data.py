import requests
import time
import os
from datetime import datetime, timedelta

# ==============================================================================
# 1. PATH CONFIGURATION (Fixed Location)
# ==============================================================================
# Get the directory where this script is located
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# Define the absolute path for downloads
OUTPUT_DIR = os.path.join(SCRIPT_DIR, "tests", "reference_data")

BASE_URL = "https://ssd.jpl.nasa.gov/api/horizons.api"

# Scenarios from validation.md
SCENARIOS = [
    {
        "id": "A_Greenwich_Solstice",
        "start": "2025-06-21",
        "lat": 51.4934,
        "lon": 0.0,
        "elev": 0.0,
        "desc": "Standard Day"
    },
    {
        "id": "B_Svalbard_Winter",
        "start": "2024-12-21",
        "lat": 78.2232,
        "lon": 15.6267,
        "elev": 0.0,
        "desc": "High Latitude Stress"
    },
    {
        "id": "C_Cairo_Historical",
        "start": "1500-01-01",
        "lat": 30.0444,
        "lon": 31.2357,
        "elev": 0.0,
        "desc": "Delta T Past"
    },
    {
        "id": "D_Quito_Future",
        "start": "3000-01-01",
        "lat": -0.1807,
        "lon": -78.4678,
        "elev": 0.0,
        "desc": "Far Future"
    },
    {
        "id": "E_MaunaKea_Topo",
        "start": "2025-03-20",
        "lat": 19.8206,
        "lon": -155.4681, # West is negative
        "elev": 4.205,    # km
        "desc": "Topocentric Height"
    }
]

def fetch_scenario(scenario, use_refraction=False):
    """
    Fetches one day of minute-by-minute data for a scenario.
    """
    
    # 1. Date Calculation
    try:
        dt_start = datetime.strptime(scenario["start"], "%Y-%m-%d")
        dt_stop = dt_start + timedelta(days=1)
        stop_str = dt_stop.strftime("%Y-%m-%d")
    except ValueError:
        year = int(scenario["start"][:4])
        stop_str = f"{year}-01-02"

    # 2. Refraction Settings
    apparent_val = "REFRACTED" if use_refraction else "AIRLESS"
    file_suffix = "APP" if use_refraction else "GEOM"

    # Construct Coordinate String: "lon,lat,elev"
    site_coord = f"{scenario['lon']},{scenario['lat']},{scenario['elev']}"

    # 3. Build Query Parameters
    params = {
        'format': 'text',
        'COMMAND': "'10'",          
        'OBJ_DATA': "'NO'",         
        'MAKE_EPHEM': "'YES'",
        'EPHEM_TYPE': "'OBSERVER'", 
        'CENTER': "'coord@399'",    
        'COORD_TYPE': "'GEODETIC'",
        'SITE_COORD': f"'{site_coord}'",
        'START_TIME': f"'{scenario['start']}'",
        'STOP_TIME': f"'{stop_str}'",
        'STEP_SIZE': "'1m'",        
        'QUANTITIES': "'4,9,7,31'", 
        'APPARENT': f"'{apparent_val}'",
        'CSV_FORMAT': "'YES'"
    }

    print(f"Downloading {scenario['id']} [{file_suffix}]...")
    
    response = requests.get(BASE_URL, params=params)
    
    if response.status_code == 200:
        filename = f"{scenario['id']}_{file_suffix}.csv"
        filepath = os.path.join(OUTPUT_DIR, filename)
        
        # FIX: Check for $$SOE (Start of Ephemeris) which is standard for data blocks
        # $$SOF is not always present in API text responses
        if "API Error" in response.text or "$$SOE" not in response.text:
             print(f"  -> API RETURNED ERROR (No Data Block Found):")
             print(f"     {response.text[:300]}...") # Print first 300 chars to debug
        else:
            with open(filepath, "w") as f:
                f.write(response.text)
            print(f"  -> Saved to {filepath}")
    else:
        print(f"  -> HTTP ERROR: {response.status_code}")
        print(f"  -> JPL MESSAGE: {response.text}")

def main():
    # Ensure the absolute path exists
    if not os.path.exists(OUTPUT_DIR):
        print(f"Creating directory: {OUTPUT_DIR}")
        os.makedirs(OUTPUT_DIR)
    else:
        print(f"Target directory exists: {OUTPUT_DIR}")

    print("--- Starting JPL Horizons Bulk Download ---")
    print("Policy: Sleeping 1.5s between requests to respect API limits.\n")

    for sc in SCENARIOS:
        fetch_scenario(sc, use_refraction=False)
        time.sleep(1.5) 
        
        fetch_scenario(sc, use_refraction=True)
        time.sleep(1.5)

    print("\n--- Download Complete ---")
    print(f"All files are located in: {OUTPUT_DIR}")

if __name__ == "__main__":
    main()