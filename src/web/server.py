# -*- coding: utf-8 -*-
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

"""
Seasonal Web: API Server
========================

This is the FastAPI backend that exposes the rigorous astronomical engine 
to the web frontend.

It handles:
1. Real-time Sun Position (Azimuth/Altitude) for specific locations.
2. Subsolar Point calculations (for the Terminator/Day-Night map layer).
3. Solar Event solving (Sunrise/Sunset/Transit).
4. Time-series analysis for graphing.

Usage:
    Run from project root:
    $ uvicorn src.web.server:app --reload
"""

import sys
import os
import math
from datetime import date, datetime, timedelta, timezone
from typing import List, Optional

from fastapi import FastAPI, HTTPException, Body
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# ------------------------------------------------------------------------------
# Path Setup (Ensure Core Engine is importable)
# ------------------------------------------------------------------------------
# We add the project root to sys.path to allow imports like 'src.core...'
current_dir = os.path.dirname(os.path.abspath(__file__)) # /src/web
src_dir = os.path.dirname(current_dir)                   # /src
project_root = os.path.dirname(src_dir)                  # /Seasonal

if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Import The Engine
try:
    from src.core.time_struct import Time
    from src.core.sun_model import SunModel
    from src.core.sidereal import SiderealTime
    from src.core.corrections import CorrectionModel
    from src.engine.solver import SolarEventSolver
except ImportError as e:
    print(f"CRITICAL ERROR: Could not import Seasonal Core.\n{e}")
    sys.exit(1)

# ------------------------------------------------------------------------------
# API Models (Pydantic)
# ------------------------------------------------------------------------------

class LocationReq(BaseModel):
    lat: float
    lon: float
    elevation: float = 0.0

class EphemerisReq(LocationReq):
    # ISO Format datetime string (e.g., "2025-06-21T12:00:00")
    datetime_str: str 

class AnalyzeReq(LocationReq):
    start_date: str  # YYYY-MM-DD
    end_date: str    # YYYY-MM-DD

class SubsolarResponse(BaseModel):
    lat: float
    lon: float
    gst: float       # Greenwich Sidereal Time
    declination: float

class EphemerisResponse(BaseModel):
    altitude: float
    azimuth: float
    distance_au: float
    is_daylight: bool

class EventResponse(BaseModel):
    day_type: str    # NORMAL, POLAR_DAY, POLAR_NIGHT
    duration_hours: float
    sunrise_utc: Optional[str]
    sunset_utc: Optional[str]
    transit_utc: Optional[str]

# ------------------------------------------------------------------------------
# Application Initialization
# ------------------------------------------------------------------------------

app = FastAPI(title="Seasonal API", version="1.0.0")

# Allow CORS for development (if frontend is on different port)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount Static Files (Frontend)
# Files in src/web/static will be available at /static
# Files in src/web/templates will be served at root (logic below)
static_path = os.path.join(current_dir, "static")
if not os.path.exists(static_path):
    os.makedirs(static_path)
    os.makedirs(os.path.join(static_path, "css"), exist_ok=True)
    os.makedirs(os.path.join(static_path, "js"), exist_ok=True)

app.mount("/static", StaticFiles(directory=static_path), name="static")

# ------------------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------------------

def parse_time(dt_str: str) -> Time:
    """Converts ISO string to Seasonal Time object."""
    try:
        dt = datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
        # Convert to UTC naive for Time struct
        # (Assuming input is UTC or converting it)
        if dt.tzinfo:
            dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
        
        return Time.from_gregorian(dt.year, dt.month, dt.day, dt.hour, dt.minute, dt.second + dt.microsecond/1e6)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid timestamp: {e}")

# ------------------------------------------------------------------------------
# API Endpoints
# ------------------------------------------------------------------------------

@app.get("/")
async def serve_spa():
    """Serves the main Single Page Application."""
    from fastapi.responses import FileResponse
    index_path = os.path.join(current_dir, "templates", "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"message": "Seasonal Engine Running. Frontend index.html not found."}

@app.post("/api/ephemeris", response_model=EphemerisResponse)
async def get_position(req: EphemerisReq):
    """
    Calculates the exact Topocentric Altitude/Azimuth for a specific moment.
    Used by the 'Little Clock' widget.
    """
    t = parse_time(req.datetime_str)
    
    # 1. Physics Pipeline
    geo = SunModel.compute_geocentric_position(t)
    lst = SiderealTime.apparent_local(t, req.lon)
    topo = CorrectionModel.apply_parallax(geo, req.lat, req.elevation, lst)
    hor = topo.to_horizontal(req.lat, lst)
    
    # 2. Refraction
    # We apply refraction for the display value
    alt_app = CorrectionModel.apply_refraction(hor.altitude_degrees, enable_refraction=True)
    
    return EphemerisResponse(
        altitude=alt_app,
        azimuth=hor.azimuth_degrees,
        distance_au=geo.distance,
        is_daylight=alt_app > -0.833 # Geometric rise approx
    )

@app.post("/api/subsolar", response_model=SubsolarResponse)
async def get_subsolar(req: dict = Body(...)):
    """
    Calculates the Subsolar Point (Lat/Lon where sun is zenith).
    Used to center the Day/Night shade map.
    Input: {"datetime_str": "..."}
    """
    dt_str = req.get("datetime_str")
    t = parse_time(dt_str)
    
    # 1. Get Sun Position (Geocentric)
    # Subsolar Lat ~= Declination
    # Subsolar Lon ~= -(GHA) = -(GMST - RA)
    
    sun_geo = SunModel.compute_geocentric_position(t)
    gmst = SiderealTime.mean_greenwich(t)
    
    ra = sun_geo.ra_degrees
    dec = sun_geo.dec_degrees
    
    # GHA (Greenwich Hour Angle) = GMST - RA
    gha = (gmst - ra + 360.0) % 360.0
    
    # Longitude is East positive, GHA measures time West of Greenwich.
    # Subsolar Longitude = -GHA (normalized to -180..180)
    sub_lon = -gha
    if sub_lon < -180: sub_lon += 360
    if sub_lon > 180: sub_lon -= 360
    
    return SubsolarResponse(
        lat=dec,
        lon=sub_lon,
        gst=gmst,
        declination=dec
    )

@app.post("/api/day-events", response_model=EventResponse)
async def get_day_events(req: EphemerisReq):
    """
    Solves for Sunrise, Sunset, and Day Type.
    Used by the '24h Bar' widget.
    """
    # Parse just the date part
    dt = datetime.fromisoformat(req.datetime_str)
    d = date(dt.year, dt.month, dt.day)
    
    solver = SolarEventSolver()
    res = solver.solve_for_date(d, req.lat, req.lon, req.elevation)
    
    def fmt(t_obj):
        """Formats a Time object (JD) to HH:MM:SS UTC (Civil)."""
        if not t_obj: return None
        
        # 1. Get Julian Fraction (0.0 = Noon, 0.5 = Midnight)
        jd_frac = t_obj.jd_fraction
        
        # 2. Convert to Civil Fraction (0.0 = Midnight, 0.5 = Noon)
        # We shift by +0.5 days
        civil_frac = jd_frac + 0.5
        
        # Normalize to [0, 1)
        civil_frac = civil_frac - math.floor(civil_frac)
        
        # 3. Convert to HMS
        total_sec = civil_frac * 86400.0
        h = int(total_sec // 3600)
        m = int((total_sec % 3600) // 60)
        s = int(total_sec % 60)
        
        return f"{h:02d}:{m:02d}:{s:02d}"

    return EventResponse(
        day_type=res.day_type,
        duration_hours=res.duration_hours,
        sunrise_utc=fmt(res.sunrise_time),
        sunset_utc=fmt(res.sunset_time),
        transit_utc=fmt(res.transit_time)
    )

@app.post("/api/analyze")
async def analyze_range(req: AnalyzeReq):
    """
    Generates a time-series of solar height for the graph.
    """
    start = date.fromisoformat(req.start_date)
    end = date.fromisoformat(req.end_date)
    
    solver = SolarEventSolver()
    
    results = []
    curr = start
    while curr <= end:
        res = solver.solve_for_date(curr, req.lat, req.lon, req.elevation)
        results.append({
            "date": curr.isoformat(),
            "hours": res.duration_hours,
            "type": res.day_type
        })
        curr += timedelta(days=1)
        
    return results

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("src.web.server:app", host="0.0.0.0", port=8000, reload=True)