# -*- coding: utf-8 -*-
"""
Seasonal Core: Sidereal Time (Earth Rotation)
=============================================

This module implements the calculation of Sidereal Time, which represents the 
orientation of the Earth relative to the fixed stars. This is essential for 
transforming Celestial coordinates (Equatorial) to Local coordinates (Horizontal).

Algorithms:
    - **GMST (Greenwich Mean Sidereal Time)**: IAU 1982 / Meeus Formula 12.4.
      Linked to Earth's rotation angle.
    - **LST (Local Sidereal Time)**: GMST + Longitude offset.

Precision:
    - Uses high-precision polynomial coefficients for T (Julian Centuries).
    - Accuracy: ~0.1 seconds of time.

Usage:
    >>> t = Time.from_gregorian(2025, 6, 21, 12, 0)
    >>> gmst = SiderealTime.mean_greenwich(t)
    >>> lst = SiderealTime.apparent_local(t, lon=0.0)
"""

import math
from .time_struct import Time

class SiderealTime:
    """
    Static class for Earth Rotation calculations.
    """

    # Coefficients for GMST (IAU 1982 standard)
    # Theta = A + B*T + C*T^2 + D*T^3
    # T is Julian Centuries from J2000.0 (UT1-based, we use UTC approx)
    COEFF_A = 280.46061837
    COEFF_B = 360.98564736629
    COEFF_C = 0.000387933
    COEFF_D = -1.0 / 38710000.0

    @staticmethod
    def mean_greenwich(time: Time) -> float:
        """
        Calculates Greenwich Mean Sidereal Time (GMST) in degrees.
        
        Formula: Meeus 12.4 (IAU 1982).
        The result is normalized to [0, 360).
        
        Args:
            time (Time): Time object (uses UTC/Civil time).
        
        Returns:
            float: GMST in degrees.
        """
        # GMST depends on UT1 (Earth Rotation Time).
        # We assume UTC approx UT1 (within 0.9s) which is sufficient for 
        # arcsecond precision in Azimuth unless dUT1 is provided.
        # We use the separate JD_day and JD_frac from Time to preserve precision.
        
        jd_day, jd_frac = time.jd_utc
        
        # Calculate T (Julian Centuries since J2000.0)
        # T = (JD - 2451545.0) / 36525.0
        T = (jd_day - 2451545.0 + jd_frac) / 36525.0
        
        # Calculate GMST in degrees
        # Note: The linear term (360.985...) is very large over centuries.
        # We can implement it smartly to avoid floating point blowup, 
        # but the standard polynomial is usually robust enough for double precision.
        
        # To strictly follow Meeus 12.4:
        # GMST = 6h 41m 50.54841s + 8640184.812866s * T + 0.093104s * T^2 - 6.2e-6s * T^3
        # But we use the degree version directly:
        
        # We split the linear term: 360.98564736629 * D
        # D = JD - 2451545.0
        D = (jd_day - 2451545.0) + jd_frac
        
        # Calculate polynomial
        theta = (SiderealTime.COEFF_A +
                 (SiderealTime.COEFF_B * D) + 
                 (SiderealTime.COEFF_C * T * T) + 
                 (SiderealTime.COEFF_D * T * T * T))
        
        # Normalize to 0-360
        theta %= 360.0
        if theta < 0:
            theta += 360.0
            
        return theta

    @staticmethod
    def apparent_local(time: Time, longitude: float, nutation_lon: float = 0.0, true_obliquity: float = 0.0) -> float:
        """
        Calculates Local Sidereal Time (LST) in degrees.
        
        LST = GMST + Longitude + Equation of the Equinoxes (optional)
        
        Args:
            time (Time): The instant of calculation.
            longitude (float): Observer's longitude in degrees (Positive EAST).
            nutation_lon (float): Nutation in longitude in degrees (optional).
            true_obliquity (float): True obliquity in degrees (optional).
            
        Returns:
            float: LST in degrees [0, 360).
        """
        gmst = SiderealTime.mean_greenwich(time)
        
        # Equation of the Equinoxes (Difference between Mean and Apparent Sidereal Time)
        # eq_equinox = dPsi * cos(epsilon)
        # This corrects for the nutation "wobble" affecting the reference point (Aries).
        eq_equinox = 0.0
        if nutation_lon != 0.0:
            import math
            eq_equinox = nutation_lon * math.cos(math.radians(true_obliquity))
            
        # LST = GMST + Longitude + Eq
        lst = gmst + longitude + eq_equinox
        
        # Normalize
        lst %= 360.0
        if lst < 0:
            lst += 360.0
            
        return lst