# -*- coding: utf-8 -*-
"""
Seasonal Core: Sidereal Time (Earth Rotation)
=============================================

This module implements the calculation of Sidereal Time, which represents the 
orientation of the Earth relative to the fixed stars. This is essential for 
transforming Celestial coordinates (Equatorial) to Local coordinates (Horizontal).

Algorithms:
    - GMST (Greenwich Mean Sidereal Time): IAU 1982 / Meeus Formula 12.4.
    - GAST (Greenwich Apparent Sidereal Time): GMST + Equation of the Equinoxes.
    - LST (Local Sidereal Time): GAST + local longitude.

Precision:
    - Uses high-precision polynomial coefficients for T (Julian Centuries).
    - Accuracy: sub-arcsecond for sidereal angle when used with a high-quality ΔT.
"""

import math
from .time_struct import Time


class SiderealTime:
    """
    Static class for Earth rotation angle and sidereal time calculations.
    """

    # GMST coefficients (Meeus 12.4, in degrees)
    # Theta_GMST = A + B*D + C*T^2 + D*T^3
    # D: days since J2000.0 (UT1-based)
    # T: Julian centuries since J2000.0 (UT1-based)
    COEFF_A = 280.46061837
    COEFF_B = 360.98564736629
    COEFF_C = 0.000387933
    COEFF_D = -1.0 / 38710000.0

    @staticmethod
    def _nutation_and_obliquity(time: Time) -> tuple[float, float]:
        """
        Computes nutation in longitude and true obliquity of the ecliptic.

        Returns:
            tuple[float, float]:
                - Nutation in longitude Δψ in degrees.
                - True obliquity ε in degrees.
        """
        # Nutation and obliquity depend on Terrestrial Time
        T = time.julian_centuries_tt

        # Geometric mean longitude of the Sun (L0), degrees
        L0 = (280.46646 + 36000.76983 * T + 0.0003032 * T * T) % 360.0

        # Longitude of the ascending node of the Moon (Ω), degrees
        omega = 125.04452 - 1934.136261 * T + 0.0020708 * T * T

        omega_rad = math.radians(omega)
        L_sun_rad = math.radians(L0)

        # Nutation in longitude and obliquity, arcseconds (truncated IAU 2000B-style model)
        d_psi_arcsec = -17.20 * math.sin(omega_rad) - 1.32 * math.sin(2.0 * L_sun_rad)
        d_eps_arcsec = 9.20 * math.cos(omega_rad) + 0.57 * math.cos(2.0 * L_sun_rad)

        arcsec_to_deg = 1.0 / 3600.0
        d_psi_deg = d_psi_arcsec * arcsec_to_deg
        d_eps_deg = d_eps_arcsec * arcsec_to_deg

        # Mean obliquity of the ecliptic (Laskar), arcseconds
        eps0_arcsec = (
            84381.448
            - 46.8150 * T
            - 0.00059 * T * T
            + 0.001813 * T * T * T
        )
        eps0_deg = eps0_arcsec * arcsec_to_deg

        # True obliquity ε = ε0 + Δε, degrees
        eps_true_deg = eps0_deg + d_eps_deg

        return d_psi_deg, eps_true_deg

    @staticmethod
    def mean_greenwich(time: Time) -> float:
        """
        Calculates Greenwich Mean Sidereal Time (GMST) in degrees.

        Implements Meeus Formula 12.4. Uses the UTC-based Julian Date from Time
        as an approximation to UT1 for sidereal purposes.

        Args:
            time (Time): Time object providing UTC-based Julian Date.

        Returns:
            float: GMST in degrees in the range [0, 360).
        """
        # UTC-based Julian Date split; used as an approximation to UT1
        jd_day, jd_frac = time.jd_utc

        # Days and centuries since J2000.0
        D = (jd_day - 2451545.0) + jd_frac
        T = D / 36525.0

        # GMST polynomial (degrees)
        theta = (
            SiderealTime.COEFF_A
            + SiderealTime.COEFF_B * D
            + SiderealTime.COEFF_C * T * T
            + SiderealTime.COEFF_D * T * T * T
        )

        # Normalize to [0, 360)
        theta %= 360.0
        if theta < 0.0:
            theta += 360.0

        return theta

    @staticmethod
    def apparent_local(
        time: Time,
        longitude: float,
        nutation_lon: float = 0.0,
        true_obliquity: float = 0.0,
    ) -> float:
        """
        Calculates Local Apparent Sidereal Time (LST) in degrees.

        LST is defined as:
            LST = GAST + longitude
            GAST = GMST + Δψ cos(ε)

        where:
            - GMST is Greenwich Mean Sidereal Time.
            - Δψ is nutation in longitude.
            - ε is the true obliquity of the ecliptic.
            - longitude is east-positive, in degrees.

        If both nutation_lon and true_obliquity are zero, nutation and obliquity
        are computed internally from the time argument.

        Args:
            time (Time): Instant of calculation.
            longitude (float): Observer longitude in degrees, east-positive.
            nutation_lon (float): Nutation in longitude Δψ in degrees.
            true_obliquity (float): True obliquity ε in degrees.

        Returns:
            float: Local apparent sidereal time in degrees in the range [0, 360).
        """
        gmst = SiderealTime.mean_greenwich(time)

        # Equation of the equinoxes in degrees: Δψ cos(ε)
        if nutation_lon == 0.0 and true_obliquity == 0.0:
            d_psi_deg, eps_true_deg = SiderealTime._nutation_and_obliquity(time)
            eq_equinox = d_psi_deg * math.cos(math.radians(eps_true_deg))
        else:
            eq_equinox = nutation_lon * math.cos(math.radians(true_obliquity))

        # Local apparent sidereal time in degrees, east-positive longitude
        lst = gmst + longitude + eq_equinox

        # Normalize to [0, 360)
        lst %= 360.0
        if lst < 0.0:
            lst += 360.0

        return lst
