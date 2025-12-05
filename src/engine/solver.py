# -*- coding: utf-8 -*-
"""
Seasonal Engine: Solar Event Solver
===================================

This module implements the root-finding algorithms required to determine
discrete solar events (Sunrise, Sunset, Transit) and the total length of day.

It uses an iterative "Oracle" approach:
1. Find Local Solar Transit (Noon) for a given date.
2. Sample the "Day State" (Polar Day, Polar Night, or Normal).
3. If Normal, use the Secant Method to find the exact moments where
   Apparent Altitude == 0 (Horizon).

Usage:
    >>> from datetime import date
    >>> solver = SolarEventSolver()
    >>> result = solver.solve_for_date(date(2025, 6, 21), lat=66.5, lon=0.0)
    >>> print(result.day_type, result.duration_hours)
"""

import math
from datetime import date, timedelta
from dataclasses import dataclass
from typing import Optional

# Import Core Physics
try:
    from ..core.time_struct import Time
    from ..core.sun_model import SunModel
    from ..core.corrections import CorrectionModel
    from ..core.sidereal import SiderealTime
    from ..core.coordinates import HorizontalCoordinates
except ImportError:
    # Fallback for flat structure testing
    from core.time_struct import Time
    from core.sun_model import SunModel
    from core.corrections import CorrectionModel
    from core.sidereal import SiderealTime
    from core.coordinates import HorizontalCoordinates

# ==============================================================================
# Data Structures
# ==============================================================================

@dataclass
class SolarDayResult:
    """
    Structured result for a day-length calculation.
    """
    date_query: date
    day_type: str  # 'NORMAL', 'POLAR_DAY', 'POLAR_NIGHT'
    
    # All Times are UTC high-precision Time objects
    transit_time: Optional[Time] = None
    sunrise_time: Optional[Time] = None
    sunset_time: Optional[Time] = None
    
    # Duration in hours
    duration_hours: float = 0.0

    def __repr__(self):
        dur = f"{self.duration_hours:.2f}h"
        rise = f"{self.sunrise_time.jd_fraction * 24:.2f} UTC" if self.sunrise_time else "-"
        set_ = f"{self.sunset_time.jd_fraction * 24:.2f} UTC" if self.sunset_time else "-"
        return f"<SolarDay {self.day_type} | Dur: {dur} | Rise: {rise} | Set: {set_}>"


class SolarEventSolver:
    """
    The numerical solver engine.
    State: Holds configuration for atmosphere (Temp/Press) but logic is functional.
    """

    def __init__(self, temp_c: float = 10.0, pressure_mbar: float = 1010.0):
        self.temp_c = temp_c
        self.pressure_mbar = pressure_mbar
        
        # Convergence threshold for altitude (degrees)
        # 0.001 degrees is approx 3.6 arcseconds (very high precision for rise/set)
        self.EPSILON_DEG = 0.001 
        
        # Max iterations for Secant method
        self.MAX_ITER = 10

    def solve_for_date(self, query_date: date, lat: float, lon: float, elev_m: float = 0.0) -> SolarDayResult:
        """
        Calculates the solar events for a specific calendar date and location.
        
        Args:
            query_date (date): Python date object (year, month, day).
            lat (float): Latitude (-90 to 90).
            lon (float): Longitude (Positive East).
            elev_m (float): Elevation in meters.

        Returns:
            SolarDayResult: The classified day type and event times.
        """
        # 1. Find Local Solar Transit (Noon)
        # We start by estimating noon as 12:00 UTC - (Lon / 15)
        
        approx_noon_utc_hour = 12.0 - (lon / 15.0)
        
        # Handle JD Conversion:
        # JD starts at Noon. 0.0 = 12:00 UTC.
        # So JD_Fraction = (Hour_UTC / 24.0) - 0.5
        
        t_base = Time.from_gregorian(query_date.year, query_date.month, query_date.day, 0, 0, 0)
        jd_noon_base = t_base.jd_day
        
        # Correctly calculate fraction relative to JD epoch (Noon)
        jd_noon_frac = (approx_noon_utc_hour / 24.0) - 0.5
        
        # Refine Transit Time (Find exact moment H = 0)
        # We iterate a few times to center perfectly on the meridian.
        t_transit = self._find_transit(jd_noon_base, jd_noon_frac, lat, lon)
        
        # 2. Determine Arctic State (Day Type)
        # Calculate Altitude at Transit (Max) and Transit +/- 12h (Min/Midnight)
        
        alt_noon = self._get_altitude(t_transit, lat, lon, elev_m)
        
        # Check Midnight (Transit + 12h)
        # We use +12h (0.5 days) to check the "following" midnight
        t_midnight = Time(t_transit.jd_day, t_transit.jd_fraction + 0.5)
        alt_midnight = self._get_altitude(t_midnight, lat, lon, elev_m)
        
        # Horizon check (usually 0 if using apparent altitude, or -0.833 geometric)
        HORIZON = 0.0
        
        # Case A: Polar Night (Max altitude is below horizon)
        if alt_noon < HORIZON:
            return SolarDayResult(
                date_query=query_date,
                day_type="POLAR_NIGHT",
                transit_time=t_transit,
                duration_hours=0.0
            )
            
        # Case B: Polar Day (Min altitude is above horizon)
        if alt_midnight > HORIZON:
             return SolarDayResult(
                date_query=query_date,
                day_type="POLAR_DAY",
                transit_time=t_transit,
                duration_hours=24.0
            )
            
        # Case C: Normal Day (Rise and Set exist)
        # We search backwards from Transit for Rise, forwards for Set.
        
        t_rise = self._solve_event_secant(t_transit, lat, lon, elev_m, direction=-1)
        t_set = self._solve_event_secant(t_transit, lat, lon, elev_m, direction=1)
        
        duration = 0.0
        if t_rise and t_set:
            # Calculate duration in days then convert to hours
            # (Day + Frac) - (Day + Frac)
            d_days = (t_set.jd_day - t_rise.jd_day) + (t_set.jd_fraction - t_rise.jd_fraction)
            duration = d_days * 24.0
            
        return SolarDayResult(
            date_query=query_date,
            day_type="NORMAL",
            transit_time=t_transit,
            sunrise_time=t_rise,
            sunset_time=t_set,
            duration_hours=duration
        )

    # ==========================================================================
    # Internal Algorithms
    # ==========================================================================

    def _get_altitude(self, t: Time, lat: float, lon: float, elev: float) -> float:
        """
        Runs the full physics pipeline to get Apparent Altitude.
        Input: Time -> Output: Altitude (Refracted)
        """
        # 1. VSOP87 Orbit
        geo_eq = SunModel.compute_geocentric_position(t)
        
        # 2. Sidereal Time
        lst = SiderealTime.apparent_local(t, lon)
        
        # 3. Topocentric Parallax
        topo_eq = CorrectionModel.apply_parallax(geo_eq, lat, elev, lst)
        
        # 4. Horizontal Coordinates (Geometric)
        hor = topo_eq.to_horizontal(lat, lst)
        
        # 5. Atmospheric Refraction
        alt_app = CorrectionModel.apply_refraction(
            hor.altitude_degrees, 
            self.pressure_mbar, 
            self.temp_c, 
            enable_refraction=True
        )
        
        return alt_app

    def _find_transit(self, base_day: int, start_frac: float, lat: float, lon: float) -> Time:
        """
        Refines the time of Solar Transit (when Sun is due South/North).
        Minimizes the Hour Angle (H).
        """
        current_frac = start_frac
        
        # Iteratively correct
        # Error in time = - HourAngle / EarthRotationRate
        # Rate approx 360 deg / 24 hrs = 15 deg/hr
        
        for _ in range(3):
            t = Time(base_day, current_frac)
            
            # Get Sun RA
            sun_geo = SunModel.compute_geocentric_position(t)
            ra = sun_geo.ra_degrees
            
            # Get LST
            lst = SiderealTime.apparent_local(t, lon)
            
            # Hour Angle (H) = LST - RA
            # Normalized to [-180, 180]
            H = (lst - ra + 180.0) % 360.0 - 180.0
            
            # If H is very small, we are at transit
            if abs(H) < 0.001:
                break
                
            # Adjustment in hours = H / 15.0
            # Adjustment in days = (H / 15.0) / 24.0 = H / 360.0
            
            shift_days = H / 360.0
            current_frac -= shift_days # Subtract because positive H means West (past transit)
            
        return Time(base_day, current_frac)

    def _solve_event_secant(self, t_start: Time, lat: float, lon: float, elev: float, direction: int) -> Time:
        """
        Finds the root (Altitude = 0) using the Secant Method.
        
        Args:
            t_start: Time of Transit (Noon).
            direction: -1 for Sunrise (Search Backwards), +1 for Sunset (Search Forwards).
        """
        # 1. Initial Bracket Guess
        # Center the bracket 6 hours from noon and sample +/- 2 hours
        offset_days = (6.0 / 24.0) * direction
        center_frac = t_start.jd_fraction + offset_days

        # Point A: 2 hours before the center (4 hours from transit)
        t1_frac = center_frac - (2.0 / 24.0)
        t1 = Time(t_start.jd_day, t1_frac)
        h1 = self._get_altitude(t1, lat, lon, elev)

        # Point B: 2 hours after the center (8 hours from transit)
        t2_frac = center_frac + (2.0 / 24.0)
        t2 = Time(t_start.jd_day, t2_frac)
        h2 = self._get_altitude(t2, lat, lon, elev)
        
        # Robust Iteration
        for i in range(self.MAX_ITER):
            
            # Check convergence
            if abs(h2) < self.EPSILON_DEG:
                return t2
                
            # Avoid division by zero
            if abs(h2 - h1) < 1e-9:
                return t2 # Stalled
                
            # Secant Step
            # x_new = x2 - f(x2) * (x2 - x1) / (f(x2) - f(x1))
            # Here x is time (fractional days), f(x) is altitude
            
            # Time difference in days
            dt = (t2.jd_day - t1.jd_day) + (t2.jd_fraction - t1.jd_fraction)
            
            # Rate of change
            slope = (h2 - h1) / dt
            
            # Delta to root (assuming linear)
            # 0 = h2 + slope * delta_t  =>  delta_t = -h2 / slope
            delta_t = -h2 / slope
            
            # Limit step size to avoid flying off to infinity (max step 3 hours)
            max_step = 0.125 # 3 hours
            delta_t = max(-max_step, min(max_step, delta_t))
            
            # Update points
            t_next_frac = t2.jd_fraction + delta_t
            t_next = Time(t2.jd_day, t_next_frac)
            h_next = self._get_altitude(t_next, lat, lon, elev)
            
            # Shift state
            t1, h1 = t2, h2
            t2, h2 = t_next, h_next
            
        return t2