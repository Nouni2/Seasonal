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
Seasonal Core: Solar Ephemeris Model
====================================

This module computes the apparent geocentric equatorial coordinates of the Sun
using a high-precision heliocentric Earth model (VSOP87D).

Algorithms:
    - Earth heliocentric ecliptic coordinates from VSOP87D (L, B, R).
    - Vector inversion to obtain Sun geocentric ecliptic coordinates.
    - Nutation in longitude and obliquity (simplified IAU 2000B style).
    - Annual aberration correction on ecliptic longitude.
    - Obliquity of the ecliptic (Laskar formula for mean obliquity).
    - Ecliptic to equatorial transformation.

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
from .vsop87_earth import earth_heliocentric_ecliptic


class SunModel:
    """
    Physics engine for apparent solar position based on heliocentric Earth motion.
    """

    # Aberration constant (arcseconds converted to degrees).
    # Represents the mean annual aberration at 1 AU.
    KAPPA_DEG = 20.49552 / 3600.0

    @staticmethod
    def compute_geocentric_position(time: Time) -> EquatorialCoordinates:
        """
        Calculates the apparent geocentric equatorial coordinates of the Sun.

        Steps:
            1. Compute Earth's heliocentric ecliptic coordinates (L, B, R) in TT.
            2. Convert to rectangular coordinates and invert to Sun geocentric.
            3. Convert Sun vector back to ecliptic spherical (geometric).
            4. Compute nutation in longitude and obliquity for the given epoch.
            5. Apply nutation and annual aberration to obtain apparent longitude.
            6. Compute true obliquity and transform ecliptic to equatorial.

        Args:
            time (Time): Instant of observation in civil time with TT support.

        Returns:
            EquatorialCoordinates: Apparent RA/Dec of the solar center.
        """
        # 1. Heliocentric Earth position from VSOP87D (ecliptic, TT-based).
        L_E_deg, B_E_deg, R_E_au = earth_heliocentric_ecliptic(time)
        L_E_rad = L_E_deg * DEG2RAD
        B_E_rad = B_E_deg * DEG2RAD

        # 2. Earth heliocentric rectangular coordinates (ecliptic frame).
        X_E = R_E_au * math.cos(B_E_rad) * math.cos(L_E_rad)
        Y_E = R_E_au * math.cos(B_E_rad) * math.sin(L_E_rad)
        Z_E = R_E_au * math.sin(B_E_rad)

        # 3. Sun geocentric rectangular coordinates (ecliptic frame).
        X_S = -X_E
        Y_S = -Y_E
        Z_S = -Z_E

        R_S_au = math.sqrt(X_S * X_S + Y_S * Y_S + Z_S * Z_S)

        # Geometric ecliptic longitude and latitude of the Sun.
        lambda_geom_rad = math.atan2(Y_S, X_S)
        beta_geom_rad = math.atan2(Z_S, math.hypot(X_S, Y_S))

        if lambda_geom_rad < 0.0:
            lambda_geom_rad += 2.0 * math.pi

        lambda_geom_deg = lambda_geom_rad * RAD2DEG
        beta_geom_deg = beta_geom_rad * RAD2DEG

        # 4. Nutation in longitude and obliquity from simplified IAU 2000B-style model.
        # Time in Julian centuries of TT from J2000.0.
        T = time.julian_centuries_tt

        # Longitude of ascending node of the Moon's orbit (degrees).
        omega_deg = 125.04452 - 1934.136261 * T + 0.0020708 * T * T
        omega_rad = omega_deg * DEG2RAD

        # Use geometric solar longitude as the argument for nutation terms.
        L_sun_rad = lambda_geom_deg * DEG2RAD

        # Nutation in longitude Δψ and nutation in obliquity Δε in arcseconds.
        d_psi_arcsec = -17.20 * math.sin(omega_rad) - 1.32 * math.sin(2.0 * L_sun_rad)
        d_eps_arcsec = 9.20 * math.cos(omega_rad) + 0.57 * math.cos(2.0 * L_sun_rad)

        d_psi_deg = d_psi_arcsec / 3600.0
        d_eps_deg = d_eps_arcsec / 3600.0

        # 5. Annual aberration and apparent ecliptic longitude.
        # Nutation is applied to longitude, then annual aberration is subtracted.
        lambda_nut_deg = lambda_geom_deg + d_psi_deg
        lambda_app_deg = lambda_nut_deg - SunModel.KAPPA_DEG

        # Apparent ecliptic latitude is approximated by the geometric latitude.
        beta_app_deg = beta_geom_deg

        # Normalize apparent longitude to [0, 360).
        lambda_app_deg = lambda_app_deg % 360.0
        if lambda_app_deg < 0.0:
            lambda_app_deg += 360.0

        # 6. True obliquity of the ecliptic (Laskar mean obliquity + Δε).
        U = T / 100.0
        eps0_arcsec = (
            84381.448
            - 4680.93 * U
            - 1.55 * U * U
            + 1999.25 * U * U * U
            - 51.38 * U * U * U * U
            - 249.67 * U * U * U * U * U
        )
        eps0_deg = eps0_arcsec / 3600.0
        true_obliquity_deg = eps0_deg + d_eps_deg

        # 7. Ecliptic to equatorial transformation using true obliquity.
        ecliptic = EclipticCoordinates(
            longitude=lambda_app_deg,
            latitude=beta_app_deg,
            distance=R_S_au,
        )

        return ecliptic.to_equatorial(true_obliquity_deg)
