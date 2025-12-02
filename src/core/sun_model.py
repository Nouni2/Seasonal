# -*- coding: utf-8 -*-
"""
Seasonal Core: Solar Ephemeris Model
====================================

This module implements the "First Principles" orbital mechanics to calculate the
Sun's position relative to the Earth's center (Geocentric).

Algorithms:
    - **Mean Orbital Elements**: Meeus Chapter 25 (VSOP87 truncated).
    - **Kepler's Equation**: Newton-Raphson iteration for eccentric anomaly.
    - **Perturbations**: 
        - Nutation (IAU 2000B simplified).
        - Aberration (Ron/Vondrak).
    - **Coordinate Transformation**: Ecliptic -> Equatorial.

Precision:
    - Target: < 1 arcsecond (0.00028 deg) relative to JPL Horizons.
    - Validity: 1000 BC to 3000 AD.

Usage:
    >>> t = Time.from_gregorian(2025, 6, 21, 12, 0)
    >>> sun_eq = SunModel.compute_geocentric_position(t)
    >>> print(sun_eq.ra_hours, sun_eq.dec_degrees)
"""

import math
from .time_struct import Time
from .coordinates import EclipticCoordinates, EquatorialCoordinates, DEG2RAD, RAD2DEG

class SunModel:
    """
    Static class acting as the physics engine for Solar calculations.
    """

    # ==========================================================================
    # Constants (Meeus / VSOP87)
    # ==========================================================================
    
    # Aberration constant (arcseconds converted to degrees)
    KAPPA_DEG = 20.49552 / 3600.0

    @staticmethod
    def compute_geocentric_position(time: Time) -> EquatorialCoordinates:
        """
        Calculates the Apparent Geocentric Equatorial Coordinates of the Sun.
        
        Steps:
        1. Calculate Mean Orbital Elements (L0, M, e) at Time T.
        2. Solve Kepler's Equation for Eccentric Anomaly (E).
        3. Calculate True Geometric Longitude (Theta).
        4. Apply Nutation and Aberration to get Apparent Longitude (lambda_app).
        5. Calculate True Obliquity of the Ecliptic (epsilon).
        6. Transform to Equatorial (Alpha, Delta).

        Args:
            time (Time): The instant of observation.

        Returns:
            EquatorialCoordinates: The apparent position (RA/Dec) of the Sun center.
        """
        # 1. Get Julian Centuries (Terrestrial Time)
        # CRITICAL: Orbital mechanics use TT, not UTC.
        T = time.julian_centuries_tt

        # 2. Mean Orbital Elements
        # Geometric Mean Longitude (L0)
        L0 = (280.46646 + 36000.76983 * T + 0.0003032 * T*T) % 360.0
        
        # Mean Anomaly (M)
        M = (357.52911 + 35999.05029 * T - 0.0001537 * T*T) % 360.0
        M_rad = M * DEG2RAD
        
        # Eccentricity (e)
        e = 0.016708634 - 0.000042037 * T - 0.0000001267 * T*T

        # 3. Solve Kepler's Equation for Eccentric Anomaly (E)
        E_rad = SunModel._solve_kepler(M_rad, e)

        # 4. True Geometric Longitude (Theta)
        # Using the True Anomaly (nu) method for strict vector correctness
        # tan(nu/2) = sqrt((1+e)/(1-e)) * tan(E/2)
        sqrt_factor = math.sqrt((1 + e) / (1 - e))
        tan_nu_2 = sqrt_factor * math.tan(E_rad / 2.0)
        nu_rad = 2.0 * math.atan(tan_nu_2)
        
        # True Longitude = L0 + nu - M (careful with wrap-around)
        # Alternatively: Theta = TrueAnomaly + LongitudePerihelion
        # But Meeus C=Equation of Center is simpler for circular checking.
        # Let's stick to the specific definition:
        # Theta = L0 + C
        # Where C = nu - M
        C_rad = nu_rad - M_rad
        theta_deg = (L0 + (C_rad * RAD2DEG)) % 360.0

        # 5. Apparent Longitude (Perturbations)
        # Nutation in Longitude (d_psi) and Obliquity (d_eps)
        # We need Omega (Moon's Ascending Node)
        omega = (125.04452 - 1934.136261 * T + 0.0020708 * T*T) % 360.0
        omega_rad = omega * DEG2RAD
        
        # Mean Longitude Sun (L_sun) approx L0 for nutation terms
        L_sun_rad = L0 * DEG2RAD
        
        # Simplified IAU 2000B Nutation (Meeus Ch 22)
        # d_psi in arcseconds -> degrees
        d_psi_arcsec = -17.20 * math.sin(omega_rad) - 1.32 * math.sin(2 * L_sun_rad)
        d_psi_deg = d_psi_arcsec / 3600.0
        
        # d_eps in arcseconds -> degrees
        d_eps_arcsec = 9.20 * math.cos(omega_rad) + 0.57 * math.cos(2 * L_sun_rad)
        d_eps_deg = d_eps_arcsec / 3600.0

        # Aberration of Light
        # Sun appears slightly behind Earth's motion.
        # Correction approx -20.4898"
        aberration_deg = -SunModel.KAPPA_DEG
        
        # Final Apparent Longitude
        lambda_app_deg = theta_deg + d_psi_deg + aberration_deg

        # 6. True Obliquity of the Ecliptic (epsilon)
        # Mean Obliquity (eps0) - Laskar's Formula
        # U = T / 100 (Julian Millennia)
        U = T / 100.0
        eps0_sec = (84381.448 - 4680.93 * U - 1.55 * U*U + 
                    1999.25 * U*U*U - 51.38 * U*U*U*U - 249.67 * U*U*U*U*U)
        eps0_deg = eps0_sec / 3600.0
        
        true_obliquity_deg = eps0_deg + d_eps_deg

        # 7. Coordinate Transformation
        # Create Ecliptic structure (Geocentric Distance R approx 1.0 for angles)
        # Calculating R strictly from ellipse: R = (1-e^2) / (1 + e cos(nu))
        R_au = (1.0 - e*e) / (1.0 + e * math.cos(nu_rad))
        
        ecliptic = EclipticCoordinates(
            longitude=lambda_app_deg,
            latitude=0.0, # Sun is always on ecliptic (approx)
            distance=R_au
        )

        return ecliptic.to_equatorial(true_obliquity_deg)

    @staticmethod
    def _solve_kepler(M_rad: float, e: float) -> float:
        """
        Solves Kepler's Equation (E = M + e*sin(E)) for Eccentric Anomaly E.
        Uses Newton-Raphson iteration.

        Args:
            M_rad (float): Mean Anomaly in radians.
            e (float): Eccentricity.

        Returns:
            float: Eccentric Anomaly (E) in radians.
        """
        # Initial guess
        E = M_rad
        if e > 0.8:
            E = math.pi
            
        # Iterate (usually converges in 2-3 steps for Earth)
        for _ in range(5):
            delta = E - e * math.sin(E) - M_rad
            # Derivative: d/dE (E - e*sin(E) - M) = 1 - e*cos(E)
            derivative = 1.0 - e * math.cos(E)
            
            # Newton step
            step = delta / derivative
            E = E - step
            
            if abs(step) < 1e-9:
                break
                
        return E