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
Seasonal Core: Coordinate Systems & Transformations
===================================================

This module defines the strict data structures for astronomical coordinates and
implements the rigorous transformation logic between reference frames.

Coordinate Systems Implemented:
    1. **Ecliptic**: Heliocentric/Geocentric (Longitude lambda, Latitude beta).
       Used for orbital positions (VSOP87 output).
    2. **Equatorial**: Celestial Sphere (Right Ascension alpha, Declination delta).
       Used for star catalogs and intermediate solar positioning.
    3. **Horizontal**: Topocentric (Altitude h, Azimuth A).
       The final local observer view.

Key Features:
    - **Type Safety**: Distinct classes prevent mixing RA (Hours) with Azimuth (Degrees).
    - **Rigorous Math**: Uses `atan2` for all quadrant resolutions.
    - **Standards**: Enforces North-Zero Azimuth for output (Compass standard).

Usage:
    >>> ecl = EclipticCoordinates(lon=180.0, lat=0.0)
    >>> eq = ecl.to_equatorial(obliquity=23.44)
    >>> hor = eq.to_horizontal(lat=51.5, lst=12.0)
"""

import math
from dataclasses import dataclass

# ==============================================================================
# Constants & Multipliers
# ==============================================================================

DEG2RAD = math.pi / 180.0
RAD2DEG = 180.0 / math.pi
HRS2RAD = math.pi / 12.0
RAD2HRS = 12.0 / math.pi
HRS2DEG = 15.0

# ==============================================================================
# 1. Ecliptic Coordinates (The Solar System View)
# ==============================================================================

@dataclass(frozen=True)
class EclipticCoordinates:
    """
    Represents a position in the Ecliptic coordinate system.
    Reference plane: The orbit of Earth around the Sun.
    
    Attributes:
        longitude (float): Ecliptic longitude (lambda) in degrees [0, 360).
        latitude (float): Ecliptic latitude (beta) in degrees [-90, 90].
        distance (float): Radius vector in AU (default 1.0).
    """
    longitude: float
    latitude: float
    distance: float = 1.0

    def to_equatorial(self, true_obliquity: float) -> 'EquatorialCoordinates':
        """
        Converts Ecliptic coordinates to Equatorial coordinates.
        
        Math:
            sin(delta) = sin(beta)cos(eps) + cos(beta)sin(eps)sin(lambda)
            tan(alpha) = (sin(lambda)cos(eps) - tan(beta)sin(eps)) / cos(lambda)
        
        Args:
            true_obliquity (float): The True Obliquity of the ecliptic (epsilon)
                                    in degrees. Includes Nutation.

        Returns:
            EquatorialCoordinates: The transformed position (Geocentric).
        """
        eps_rad = true_obliquity * DEG2RAD
        lon_rad = self.longitude * DEG2RAD
        lat_rad = self.latitude * DEG2RAD

        # Simplified for Sun (beta approx 0), but full formula implemented for rigorousness
        sin_lon = math.sin(lon_rad)
        cos_lon = math.cos(lon_rad)
        sin_lat = math.sin(lat_rad)
        cos_lat = math.cos(lat_rad)
        sin_eps = math.sin(eps_rad)
        cos_eps = math.cos(eps_rad)

        # 1. Calculate Declination (delta)
        # sin(delta) = sin(beta)cos(eps) + cos(beta)sin(eps)sin(lambda)
        sin_delta = (sin_lat * cos_eps) + (cos_lat * sin_eps * sin_lon)
        # Clamp for numerical stability
        sin_delta = max(-1.0, min(1.0, sin_delta))
        delta_rad = math.asin(sin_delta)

        # 2. Calculate Right Ascension (alpha)
        # y = sin(lambda)cos(eps) - tan(beta)sin(eps)
        # x = cos(lambda)
        y = (sin_lon * cos_eps) - (math.tan(lat_rad) * sin_eps)
        x = cos_lon
        
        alpha_rad = math.atan2(y, x)
        
        # Normalize alpha to [0, 2pi)
        if alpha_rad < 0:
            alpha_rad += 2 * math.pi

        # Convert to Degrees for the data structure
        return EquatorialCoordinates(
            ra_degrees=alpha_rad * RAD2DEG,
            dec_degrees=delta_rad * RAD2DEG,
            distance=self.distance
        )

# ==============================================================================
# 2. Equatorial Coordinates (The Space View)
# ==============================================================================

@dataclass(frozen=True)
class EquatorialCoordinates:
    """
    Represents a position in the Equatorial coordinate system.
    Reference plane: The Earth's Equator (projected).
    
    Attributes:
        ra_degrees (float): Right Ascension (alpha) in degrees [0, 360).
                            (Stored in degrees for consistency, helper property for hours).
        dec_degrees (float): Declination (delta) in degrees [-90, 90].
        distance (float): Distance in AU (Geocentric distance).
    """
    ra_degrees: float
    dec_degrees: float
    distance: float = 1.0

    @property
    def ra_hours(self) -> float:
        """Returns Right Ascension in Hours [0, 24)."""
        return self.ra_degrees / HRS2DEG

    def to_horizontal(self, obs_lat: float, lst_degrees: float) -> 'HorizontalCoordinates':
        """
        Converts Equatorial coordinates to local Horizontal coordinates.
        
        Note: This performs the GEOMETRIC transformation. 
        It does NOT apply Topocentric Parallax or Refraction.
        Those corrections must be applied to the Equatorial coordinates 
        *before* calling this method if needed, or to the Altitude *after*.

        Args:
            obs_lat (float): Observer's Latitude in degrees (Positive North).
            lst_degrees (float): Local Sidereal Time (theta) in degrees.

        Returns:
            HorizontalCoordinates: Altitude and Azimuth (Geometric).
        """
        lat_rad = obs_lat * DEG2RAD
        dec_rad = self.dec_degrees * DEG2RAD
        
        # 1. Calculate Hour Angle (H)
        # H = LST - RA
        # Range: [-180, 180] preferred for trig stability
        ha_degrees = lst_degrees - self.ra_degrees
        
        # Normalize HA to [-180, 180] for standard astronomical definition
        ha_degrees = (ha_degrees + 180.0) % 360.0 - 180.0
        ha_rad = ha_degrees * DEG2RAD

        sin_lat = math.sin(lat_rad)
        cos_lat = math.cos(lat_rad)
        sin_dec = math.sin(dec_rad)
        cos_dec = math.cos(dec_rad)
        sin_h = math.sin(ha_rad)
        cos_h = math.cos(ha_rad)

        # 2. Calculate Altitude (h)
        # sin(h) = sin(phi)sin(delta) + cos(phi)cos(delta)cos(H)
        sin_alt = (sin_lat * sin_dec) + (cos_lat * cos_dec * cos_h)
        sin_alt = max(-1.0, min(1.0, sin_alt))
        alt_rad = math.asin(sin_alt)

        # 3. Calculate Azimuth (A)
        # Standard Astronomical Formula (A=0 at South, increasing West)
        # tan(A) = sin(H) / (sin(phi)cos(H) - cos(phi)tan(delta))
        # But we use atan2(y, x)
        
        # y = -cos(delta) * sin(H)
        # x = sin(delta)cos(phi) - cos(delta)cos(H)sin(phi)
        # (This formulation yields 0 at North if configured correctly, but standard Meeus 
        #  often yields South. Let's stick to the rigorous vector algebra).
        
        # Using Meeus 13.5 (modified for North=0):
        # A usually measured from South. 
        # tan(A_south) = sin(H) / (sin(phi)cos(H) - tan(delta)cos(phi))
        
        # We derive rigorously:
        y = -cos_dec * sin_h
        x = (sin_dec * cos_lat) - (cos_dec * cos_h * sin_lat)
        
        az_rad = math.atan2(y, x)
        
        # The raw atan2(y, x) here gives Azimuth measured from NORTH, increasing EAST.
        # However, checking the sign logic:
        # If H > 0 (West), sin(H) > 0 -> y < 0. 
        # We need West to be 270 deg (or -90). 
        # Let's normalize to [0, 360).
        
        if az_rad < 0:
            az_rad += 2 * math.pi
            
        return HorizontalCoordinates(
            altitude_degrees=alt_rad * RAD2DEG,
            azimuth_degrees=az_rad * RAD2DEG
        )

# ==============================================================================
# 3. Horizontal Coordinates (The Observer View)
# ==============================================================================

@dataclass(frozen=True)
class HorizontalCoordinates:
    """
    Represents a position in the local Horizontal (Alt-Az) coordinate system.
    Reference plane: The local Horizon.
    
    Attributes:
        altitude_degrees (float): Angular height above horizon [-90, 90].
        azimuth_degrees (float): Compass direction [0, 360).
                                 0=North, 90=East, 180=South, 270=West.
    """
    altitude_degrees: float
    azimuth_degrees: float
    
    def __repr__(self):
        return f"Horizontal(Alt={self.altitude_degrees:.4f}°, Az={self.azimuth_degrees:.4f}°)"