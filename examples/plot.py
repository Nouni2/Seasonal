# -*- coding: utf-8 -*-
"""
Seasonal Example: Solar Height vs Time (Paris 2025)
===================================================

This script calculates the raw Solar Altitude (Height) for every hour 
of the year 2025 in Paris, France.

It generates a continuous time-series plot:
- X-Axis: Time (Day of Year 0-365)
- Y-Axis: Solar Altitude (Degrees)

Requirements:
    pip install matplotlib

Usage:
    python examples/plot_paris.py
"""

import os
import sys
import matplotlib.pyplot as plt

# ------------------------------------------------------------------------------
# Path Fix: Add Project Root to sys.path
# ------------------------------------------------------------------------------
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.core.time_struct import Time
from src.core.sun_model import SunModel
from src.core.sidereal import SiderealTime
from src.core.corrections import CorrectionModel

# ==============================================================================
# Configuration: Paris, France
# ==============================================================================
PARIS_LAT = 15.8566
PARIS_LON = 2.3522
PARIS_ELEV = 35.0

def get_solar_altitude(year, month, day, hour, minute):
    """
    Calculates just the Topocentric Apparent Altitude for a specific time.
    """
    t = Time.from_gregorian(year, month, day, hour, minute, 0.0)
    
    # 1. Geocentric Position
    sun_geo = SunModel.compute_geocentric_position(t)
    
    # 2. Local Sidereal Time
    lst = SiderealTime.apparent_local(t, PARIS_LON)
    
    # 3. Parallax Correction
    sun_topo = CorrectionModel.apply_parallax(sun_geo, PARIS_LAT, PARIS_ELEV, lst)
    
    # 4. Horizontal Coordinates (Geometric)
    hor = sun_topo.to_horizontal(PARIS_LAT, lst)
    
    # 5. Refraction (Apparent Altitude)
    alt_app = CorrectionModel.apply_refraction(
        hor.altitude_degrees, 
        pressure_mbar=1013.25, 
        temp_celsius=15.0, 
        enable_refraction=True
    )
    
    return alt_app

def generate_yearly_series(year, step_minutes=30):
    """
    Generates a continuous time series of solar altitude.
    
    Args:
        year (int): The year to simulate.
        step_minutes (int): Resolution of the data (default 30 mins).
        
    Returns:
        times (list): Day of year (float).
        heights (list): Altitude in degrees.
    """
    times = []
    heights = []
    
    # Standard days in months (Simple year 2025 is not leap)
    days_in_months = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    
    # Leap year check if you change the year
    if year % 4 == 0 and (year % 100 != 0 or year % 400 == 0):
        days_in_months[1] = 29

    print(f"Generating height data for {year} (Resolution: {step_minutes} min)...")
    
    current_day_of_year = 0
    total_steps = sum(days_in_months) * 24 * (60 // step_minutes)
    count = 0

    for month_idx, days in enumerate(days_in_months):
        month = month_idx + 1
        for day in range(1, days + 1):
            for hour in range(0, 24):
                for minute in range(0, 60, step_minutes):
                    
                    # Calculate Altitude
                    alt = get_solar_altitude(year, month, day, hour, minute)
                    
                    # X-Axis: Fractional Day of Year
                    time_x = current_day_of_year + (hour + minute/60.0) / 24.0
                    
                    times.append(time_x)
                    heights.append(alt)
                    
                    count += 1
                    if count % 2000 == 0:
                        sys.stdout.write(f"\rProgress: {int(count/total_steps*100)}%")
                        sys.stdout.flush()
            
            current_day_of_year += 1
            
    print("\nCalculation complete.")
    return times, heights

# ==============================================================================
# Main Execution
# ==============================================================================
if __name__ == "__main__":
    # 1. Generate Data
    times, heights = generate_yearly_series(2025, step_minutes=15) # High res

    # 2. Plotting
    plt.figure(figsize=(12, 6))
    
    plt.plot(times, heights, color='orange', linewidth=0.5, alpha=0.8, label='Solar Altitude')
    
    # 3. Formatting
    plt.title(f"Solar Height vs Time - Paris 2025\nLat: {PARIS_LAT}, Lon: {PARIS_LON}")
    plt.xlabel("Day of Year (0 - 365)")
    plt.ylabel("Solar Altitude (Degrees)")
    
    plt.axhline(0, color='black', linewidth=1.5, label='Horizon') # Horizon line
    plt.grid(True, which='both', linestyle=':', alpha=0.5)
    plt.legend(loc='upper right')
    
    plt.xlim(0, 365)
    plt.ylim(-60, 70) # Sun goes down to ~-60 at night and up to ~65 in summer
    
    print("Displaying plot...")
    plt.show()