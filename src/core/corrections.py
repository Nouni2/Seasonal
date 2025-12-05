# -*- coding: utf-8 -*-
"""
Seasonal Core: Physical Corrections
===================================

This module implements the topocentric and atmospheric corrections required to
transform Geocentric coordinates into the final Apparent Horizon coordinates
observed by a human or sensor.

Algorithms:
    - **Topocentric Parallax**: Strict vector shift using WGS84 ellipsoid.
    - **Atmospheric Refraction**: Saemundsson formula with T/P scaling.

Reference:
    - Meeus, Astronomical Algorithms, Ch 40 (Parallax), Ch 16 (Refraction).
    - Explanatory Supplement to the Astronomical Almanac.

Usage:
    >>> # Apply Parallax
    >>> sun_topo = CorrectionModel.apply_parallax(sun_geo, lat=51.5, elev=0, lst=12.0)
    >>> # Apply Refraction (Optional)
    >>> alt_apparent = CorrectionModel.apply_refraction(sun_topo.altitude, press=1010, temp=10, enabled=True)
"""

import math
from .coordinates import EquatorialCoordinates, DEG2RAD, RAD2DEG

class CorrectionModel:
    """
    Static class acting as the correction engine for observer-specific physics.
    """

    # ==========================================================================
    # Constants
    # ==========================================================================
    
    # Earth Constants (WGS84)
    EARTH_RADIUS_M = 6378137.0
    FLATTENING = 1.0 / 298.257223563
    
    # Solar Parallax at 1 AU (arcseconds)
    SOLAR_PARALLAX_ARCSEC = 8.794

    @staticmethod
    def apply_parallax(geocentric: EquatorialCoordinates, 
                       observer_lat: float, 
                       observer_elev: float, 
                       lst_degrees: float) -> EquatorialCoordinates:
        """
        Converts Geocentric Equatorial Coordinates to Topocentric Equatorial Coordinates.
        
        This shifts the origin from the center of the Earth to the observer's location
        on the surface, accounting for the Earth's ellipsoidal shape (WGS84).

        Args:
            geocentric (EquatorialCoordinates): The Sun's position from Earth center.
            observer_lat (float): Geodetic Latitude of observer in degrees.
            observer_elev (float): Elevation above sea level in meters.
            lst_degrees (float): Local Sidereal Time in degrees.

        Returns:
            EquatorialCoordinates: The Topocentric (Observer-centric) RA/Dec.
        """
        # 1. Observer's Geocentric Position (Rho * sin/cos phi')
        # Compute distance from Earth axis and Equatorial plane.
        # See Math Reference 5.2
        
        lat_rad = observer_lat * DEG2RAD
        sin_lat = math.sin(lat_rad)
        cos_lat = math.cos(lat_rad)
        
        # Auxiliary angle u (reduced latitude)
        # tan(u) = (b/a) * tan(phi) = (1-f) * tan(phi)
        u = math.atan((1.0 - CorrectionModel.FLATTENING) * math.tan(lat_rad))
        sin_u = math.sin(u)
        cos_u = math.cos(u)
        
        # Elevation ratio (H / a_e)
        h_ratio = observer_elev / CorrectionModel.EARTH_RADIUS_M
        
        # Rho * Sin(Phi') - Distance from Equatorial Plane (normalized)
        # rho_sin_phi = (1-f)*sin(u) + (h/a)*sin(phi)
        rho_sin_phi = (1.0 - CorrectionModel.FLATTENING) * sin_u + h_ratio * sin_lat
        
        # Rho * Cos(Phi') - Distance from Earth Axis (normalized)
        # rho_cos_phi = cos(u) + (h/a)*cos(phi)
        rho_cos_phi = cos_u + h_ratio * cos_lat
        
        # 2. Solar Parallax (pi)
        # The parallax angle depends on distance: pi = 8.794 / Distance(AU)
        pi_arcsec = CorrectionModel.SOLAR_PARALLAX_ARCSEC / geocentric.distance
        pi_rad = (pi_arcsec / 3600.0) * DEG2RAD
        sin_pi = math.sin(pi_rad)
        
        # 3. Local Hour Angle (H)
        # H = LST - RA
        ra_rad = geocentric.ra_degrees * DEG2RAD
        lst_rad = lst_degrees * DEG2RAD
        h_rad = lst_rad - ra_rad
        
        sin_h = math.sin(h_rad)
        cos_h = math.cos(h_rad)
        
        # 4. Compute Parallax Shift (Delta Alpha)
        # tan(d_alpha) = (-rho*cos_phi' * sin_pi * sin_H) / (cos_delta - rho*cos_phi' * sin_pi * cos_H)
        dec_rad = geocentric.dec_degrees * DEG2RAD
        cos_dec = math.cos(dec_rad)
        sin_dec = math.sin(dec_rad)
        
        numerator = -rho_cos_phi * sin_pi * sin_h
        denominator = cos_dec - (rho_cos_phi * sin_pi * cos_h)
        
        # Use atan2 to preserve quadrant information
        delta_alpha_rad = math.atan2(numerator, denominator)
        
        # 5. Compute New Declination (Delta')
        # tan(delta') = ((sin_delta - rho*sin_phi'*sin_pi) * cos(d_alpha)) / (cos_delta - rho*cos_phi'*sin_pi*cos_H)
        # The denominator is identical to the RA calculation denominator.
        
        # Calculate cos(delta_alpha) needed for the numerator
        cos_delta_alpha = math.cos(delta_alpha_rad)
        
        num_dec = (sin_dec - rho_sin_phi * sin_pi) * cos_delta_alpha
        den_dec = denominator 
        
        delta_prime_rad = math.atan2(num_dec, den_dec)
        
        # 6. Apply Shifts
        new_ra_rad = ra_rad + delta_alpha_rad
        
        # Normalize RA to [0, 2pi) range
        if new_ra_rad < 0:
            new_ra_rad += 2 * math.pi
        elif new_ra_rad >= 2 * math.pi:
            new_ra_rad -= 2 * math.pi
            
        return EquatorialCoordinates(
            ra_degrees=new_ra_rad * RAD2DEG,
            dec_degrees=delta_prime_rad * RAD2DEG,
            distance=geocentric.distance 
        )

    @staticmethod
    def apply_refraction(
        geometric_altitude_deg: float,
        pressure_mbar: float = 1010.0,
        temp_celsius: float = 10.0,
        enable_refraction: bool = True,
    ) -> float:
        """
        Calculates the apparent altitude by applying atmospheric refraction.

        Uses Saemundsson's formula (Meeus 16.4) evaluated at the apparent
        altitude, solved iteratively starting from the geometric altitude.
        Includes Bennett-style scaling for pressure and temperature.

        Args:
            geometric_altitude_deg (float): Topocentric geometric altitude in degrees.
            pressure_mbar (float): Surface pressure in millibars/hPa.
            temp_celsius (float): Surface temperature in Celsius.
            enable_refraction (bool): If False, returns geometric altitude.

        Returns:
            float: Apparent altitude in degrees.
        """
        if not enable_refraction:
            return geometric_altitude_deg

        h_geo = geometric_altitude_deg

        # Refraction formulae (Saemundsson) diverge or are undefined below the horizon.
        # We allow the formula to compute slightly below the horizon (-2.0 deg)
        # to ensure continuity at the exact moment of sunset (approx -0.83 deg).
        # A hard cutoff at -0.57 causes a step-function error of ~0.8 deg at sunrise.
        if h_geo < -2.0:
            return h_geo

        # Pressure and temperature scaling factor applied to the standard refraction.
        kelvin = 273.0 + temp_celsius
        scaling = (pressure_mbar / 1010.0) * (283.0 / kelvin)

        # Iterative solution for apparent altitude h_app such that:
        #   h_app = h_geo + R(h_app)
        # where R(h_app) is Saemundsson refraction in degrees.
        h_app = h_geo
        for _ in range(3):
            # Clamp the argument to -1.0 to ensure numerical stability during iteration
            # for values near the cutoff threshold.
            h_used = max(h_app, -1.0)

            # Saemundsson refraction R0 in arcminutes:
            #   R0 = 1.02 / tan(h + 10.3 / (h + 5.11))
            # with h in degrees and result in arcminutes.
            div_inner = h_used + 5.11
            if div_inner == 0.0:
                break

            tan_arg_deg = h_used + 10.3 / div_inner
            tan_arg_rad = tan_arg_deg * DEG2RAD

            # Avoid division by zero if tan argument approaches 90 degrees (zenith)
            if abs(math.cos(tan_arg_rad)) < 1e-9:
                break

            r0_arcmin = 1.02 / math.tan(tan_arg_rad)
            r_arcmin = r0_arcmin * scaling
            r_deg = r_arcmin / 60.0

            h_new = h_geo + r_deg
            
            # Check for convergence
            if abs(h_new - h_app) < 1e-6:
                h_app = h_new
                break

            h_app = h_new

        return h_app