# -*- coding: utf-8 -*-
"""
Seasonal Example: Annual Day Length Plot (Interactive)
======================================================

This script calculates the length of the day for every day of the year 2025
at a specific location (Paris, France) and renders an interactive HTML plot.

It utilizes the 'Seasonal' engine to compute high-precision topocentric 
sunrise and sunset times, accounting for atmospheric refraction.

Requirements:
    pip install plotly
"""

import sys
import os
from datetime import date, timedelta

# ------------------------------------------------------------------------------
# Dependency Check: Plotly
# ------------------------------------------------------------------------------
try:
    import plotly.graph_objects as go
    import plotly.io as pio
except ImportError:
    print("Error: This example requires 'plotly'.")
    print("Please install it via: pip install plotly")
    sys.exit(1)

# ------------------------------------------------------------------------------
# Path Setup
# ------------------------------------------------------------------------------
# Add the parent directory 'src' to the Python path so we can import the engine.
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
src_path = os.path.join(parent_dir, 'src')

if src_path not in sys.path:
    sys.path.append(parent_dir)

try:
    from src.engine.solver import SolarEventSolver
except ImportError:
    try:
        from src.engine.solver import SolarEventSolver
    except ImportError:
        print("Error: Could not import 'src.engine.solver'.")
        sys.exit(1)

# ------------------------------------------------------------------------------
# Configuration (Paris, France)
# ------------------------------------------------------------------------------
LOCATION_NAME = "Paris, France"
LATITUDE = 48.8566   # Degrees North
LONGITUDE = 2.3522   # Degrees East
ELEVATION = 35.0     # Meters
YEAR = 2025

# ------------------------------------------------------------------------------
# Helper: Time Formatting
# ------------------------------------------------------------------------------
def format_decimal_hour(h: float) -> str:
    """Converts 12.50 to '12:30'."""
    hours = int(h)
    minutes = int((h - hours) * 60)
    return f"{hours:02d}:{minutes:02d}"

def get_utc_time_str(time_obj) -> str:
    """Extracts HH:MM string from a Seasonal Time object."""
    if not time_obj: 
        return "N/A"
    # Time object stores fraction of day (0.0 to 1.0)
    # We multiply by 24 to get hours
    frac = time_obj.jd_fraction
    # Handle wrap-around for display safety
    if frac < 0: frac += 1.0
    if frac >= 1.0: frac -= 1.0
    return format_decimal_hour(frac * 24.0)

# ------------------------------------------------------------------------------
# Main Execution
# ------------------------------------------------------------------------------
def main():
    print(f"Initializing Solar Solver for {LOCATION_NAME} ({LATITUDE}, {LONGITUDE})...")
    
    # Initialize Solver with standard atmosphere
    solver = SolarEventSolver(temp_c=15.0, pressure_mbar=1013.25)
    
    dates = []
    durations = []
    hover_texts = []
    
    # Iterate through every day of the year
    start_date = date(YEAR, 1, 1)
    end_date = date(YEAR, 12, 31)
    delta_day = timedelta(days=1)
    
    current_date = start_date
    print("Computing high-precision ephemeris...", end="", flush=True)
    
    while current_date <= end_date:
        if current_date.day == 1:
            print(f".", end="", flush=True)
            
        # --- CORE CALCULATION ---
        result = solver.solve_for_date(current_date, LATITUDE, LONGITUDE, ELEVATION)
        # ------------------------
        
        dates.append(current_date)
        durations.append(result.duration_hours)
        
        # Prepare rich tooltip data
        rise_str = get_utc_time_str(result.sunrise_time)
        set_str = get_utc_time_str(result.sunset_time)
        
        txt = (
            f"<b>{current_date.strftime('%B %d, %Y')}</b><br>"
            f"Day Length: {result.duration_hours:.4f} hrs<br>"
            f"Sunrise: {rise_str} UTC<br>"
            f"Sunset: {set_str} UTC<br>"
            f"Type: {result.day_type}"
        )
        hover_texts.append(txt)
        
        current_date += delta_day

    print(" Done!")
    print("Generating Interactive Plot...")

    # --------------------------------------------------------------------------
    # Plotly Visualization
    # --------------------------------------------------------------------------
    fig = go.Figure()

    # Main Day Length Curve
    fig.add_trace(go.Scatter(
        x=dates, 
        y=durations,
        mode='lines',
        name='Day Length',
        line=dict(color='#ff7f0e', width=3),
        text=hover_texts,
        hoverinfo='text'
    ))

    # Add Solstice/Equinox Markers
    special_dates = [
        (date(YEAR, 3, 20), "Vernal Equinox"),
        (date(YEAR, 6, 21), "Summer Solstice"),
        (date(YEAR, 9, 22), "Autumnal Equinox"),
        (date(YEAR, 12, 21), "Winter Solstice")
    ]

    for d, label in special_dates:
        res = solver.solve_for_date(d, LATITUDE, LONGITUDE, ELEVATION)
        y_val = res.duration_hours
        
        fig.add_trace(go.Scatter(
            x=[d],
            y=[y_val],
            mode='markers',
            name=label,
            marker=dict(size=10, color='red', symbol='circle-open-dot'),
            hoverinfo='skip'
        ))
        
        # Add annotation text
        fig.add_annotation(
            x=d,
            y=y_val,
            text=f"{label}<br>{y_val:.2f}h",
            showarrow=True,
            arrowhead=1,
            yshift=10 if y_val < 12 else -10,
            ay=-40 if y_val < 12 else 40
        )

    # Styling
    fig.update_layout(
        title=dict(
            text=f"Solar Day Length 2025: {LOCATION_NAME}",
            font=dict(size=24)
        ),
        xaxis_title="Date",
        yaxis_title="Hours of Daylight",
        template="plotly_white",
        hovermode="x unified",
        yaxis=dict(
            range=[7, 17], # Tighten view for Paris latitude
            tickmode='linear',
            dtick=1
        ),
        showlegend=False
    )

    # Add a subtle reference line for 12 hours (Equinox theoretical)
    fig.add_hline(y=12.0, line_dash="dot", line_color="gray", opacity=0.5, annotation_text="12h")

    # Show
    fig.show()

if __name__ == "__main__":
    main()