#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import argparse
from datetime import date

# ==============================================================================
# Path Configuration & Imports
# ==============================================================================

current_file_path = os.path.abspath(__file__)
examples_dir = os.path.dirname(current_file_path)
project_root = os.path.dirname(examples_dir)

if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.engine.solver import SolarEventSolver  # uses SolarEventSolver.solve_for_date :contentReference[oaicite:0]{index=0}


# ==============================================================================
# Utility Functions
# ==============================================================================

def time_to_hms(time_obj):
    """
    Converts a Time instance into an (hour, minute, second) tuple in UTC.
    The Time object stores JD as (day, fraction) with fraction=0.0 at noon,
    so the civil time-of-day fraction is (jd_fraction + 0.5) modulo 1.0.
    """
    civil_fraction = (time_obj.jd_fraction + 0.5) % 1.0
    total_seconds = civil_fraction * 86400.0
    total_seconds = int(round(total_seconds))

    hours = total_seconds // 3600
    remaining = total_seconds % 3600
    minutes = remaining // 60
    seconds = remaining % 60

    return hours, minutes, seconds


def format_hms(time_obj):
    """
    Formats a Time instance into an hh:mm:ss string in UTC.
    """
    h, m, s = time_to_hms(time_obj)
    return f"{h:02d}:{m:02d}:{s:02d}"


# ==============================================================================
# Argument Parsing
# ==============================================================================

def parse_args():
    """
    Parses command-line arguments for location and date.
    """
    parser = argparse.ArgumentParser(
        description="Compute sunrise and sunset times (UTC) for a given date and location."
    )
    parser.add_argument(
        "--lat",
        type=float,
        required=True,
        help="Geodetic latitude in degrees (positive North).",
    )
    parser.add_argument(
        "--lon",
        type=float,
        required=True,
        help="Geodetic longitude in degrees (positive East).",
    )
    parser.add_argument(
        "--elev",
        type=float,
        default=0.0,
        help="Elevation above sea level in meters (default: 0).",
    )
    parser.add_argument(
        "--date",
        type=str,
        required=True,
        help="Calendar date in ISO format YYYY-MM-DD (UTC).",
    )
    return parser.parse_args()


# ==============================================================================
# Main Entry Point
# ==============================================================================

def main():
    """
    Entry point: reads arguments, runs the solar event solver, prints sunrise and sunset.
    """
    args = parse_args()

    year_str, month_str, day_str = args.date.split("-")
    query_date = date(int(year_str), int(month_str), int(day_str))

    solver = SolarEventSolver()
    result = solver.solve_for_date(
        query_date=query_date,
        lat=args.lat,
        lon=args.lon,
        elev_m=args.elev,
    )

    print(f"Date (UTC): {query_date.isoformat()}")
    print(f"Location: lat={args.lat:.6f}°, lon={args.lon:.6f}°, elev={args.elev:.1f} m")
    print(f"Day type: {result.day_type}")

    if result.sunrise_time is not None:
        print(f"Sunrise (UTC): {format_hms(result.sunrise_time)}")
    else:
        print("Sunrise (UTC): none")

    if result.sunset_time is not None:
        print(f"Sunset (UTC): {format_hms(result.sunset_time)}")
    else:
        print("Sunset (UTC): none")


if __name__ == "__main__":
    main()
