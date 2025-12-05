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
VSOP87 Earth (Version D, Heliocentric Ecliptic Coordinates)
===========================================================

This module evaluates the VSOP87D series for the Earth to obtain the
heliocentric ecliptic longitude, latitude, and radius vector as a function
of Terrestrial Time (TT).

Data source:
    - VSOP87D.ear (Earth, Version D4, spherical coordinates L/B/R)
      Heliocentric dynamical ecliptic and equinox of the date.

Interface:
    - earth_heliocentric_ecliptic(time: Time) -> (L_deg, B_deg, R_au)

Where:
    - L_deg : heliocentric ecliptic longitude in degrees [0, 360).
    - B_deg : heliocentric ecliptic latitude in degrees.
    - R_au  : heliocentric distance in astronomical units.

The VSOP time variable is:
    t = (JD_TT - 2451545.0) / 365250.0 = T / 10
where T is Julian centuries in TT from J2000.0.
"""

from __future__ import annotations

import math
import os
from typing import List, Tuple

from .time_struct import Time

# VSOP87D Earth data file is stored relative to this module.
# The path is resolved at runtime so the module can be imported from any cwd.
_VSOP_FILE_REL_PATH = os.path.join("VSOP87D_data", "VSOP87D.ear")

# Internal containers for VSOP terms.
# Each element is a list of (A, B, C) tuples for the corresponding power of t.
# Index 0..5 corresponds to the *T**0 .. *T**5 blocks.
_L_TERMS: List[List[Tuple[float, float, float]]] = [[] for _ in range(6)]
_B_TERMS: List[List[Tuple[float, float, float]]] = [[] for _ in range(6)]
_R_TERMS: List[List[Tuple[float, float, float]]] = [[] for _ in range(6)]

# Load guard flag to ensure the VSOP file is parsed only once.
_VSOP_LOADED: bool = False


def _get_vsop_file_path() -> str:
    """
    Resolves the absolute path to the VSOP87D.ear data file.

    Returns:
        str: Absolute filesystem path to the VSOP87D.ear file.
    """
    module_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(module_dir, _VSOP_FILE_REL_PATH)


def _parse_header_line(header_line: str) -> Tuple[int, int, int]:
    """
    Parses a VSOP87 header line for variable index, power, and term count.

    The header has the form:
        VSOP87 VERSION D4    EARTH     VARIABLE k (LBR)       *T**n    N TERMS ...

    Args:
        header_line (str): Raw header line from the VSOP87D.ear file.

    Returns:
        Tuple[int, int, int]:
            - variable_index: 1 for L, 2 for B, 3 for R.
            - power_n: polynomial power n for T**n, in [0, 5].
            - num_terms: number of following data lines for this block.
    """
    tokens = header_line.strip().split()

    # Extract variable index after the token "VARIABLE".
    # Example segment: "VARIABLE 1 (LBR)"
    var_idx = None
    for i, tok in enumerate(tokens):
        if tok.upper() == "VARIABLE" and i + 1 < len(tokens):
            var_idx = int(tokens[i + 1])
            break
    if var_idx is None:
        raise ValueError(f"Could not parse VARIABLE index from header: {header_line!r}")

    # Extract polynomial power from token like "*T**0".
    power_n = None
    for tok in tokens:
        if tok.startswith("*T**"):
            power_n = int(tok[4:])
            break
    if power_n is None:
        raise ValueError(f"Could not parse power from header: {header_line!r}")

    # Extract number of terms from the integer immediately preceding "TERMS".
    num_terms = None
    for i, tok in enumerate(tokens):
        if tok.upper() == "TERMS" and i > 0:
            num_terms = int(tokens[i - 1])
            break
    if num_terms is None:
        raise ValueError(f"Could not parse term count from header: {header_line!r}")

    return var_idx, power_n, num_terms


def _load_vsop87_earth_if_needed() -> None:
    """
    Lazily loads and parses the VSOP87D.ear file for Earth into memory.

    The file is organized in blocks, each starting with a header line:
        VSOP87 VERSION D4    EARTH     VARIABLE k (LBR)       *T**n    N TERMS ...

    followed by N data lines with the format:
        iv  k  ...  (14 integer fields total)  S  K  A  B  C

    This loader extracts only the final three columns (A, B, C), which are the
    reduced VSOP coefficients for terms of the form:
        A * cos(B + C * t)

    The terms are grouped by (variable k, power n) into L/B/R arrays.
    """
    global _VSOP_LOADED

    if _VSOP_LOADED:
        return

    file_path = _get_vsop_file_path()
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"VSOP87 Earth data file not found: {file_path}")

    # Local references for faster attribute access inside the loop.
    L_terms = _L_TERMS
    B_terms = _B_TERMS
    R_terms = _R_TERMS

    with open(file_path, "r", encoding="utf-8") as f:
        while True:
            header_line = f.readline()
            if not header_line:
                break  # End of file

            stripped = header_line.strip()
            if not stripped:
                # Skip empty lines.
                continue

            if not stripped.startswith("VSOP87 VERSION"):
                # Non-header content is ignored and scanning continues.
                continue

            # Parse header into variable index, power, and term count.
            variable_index, power_n, num_terms = _parse_header_line(header_line)

            # Select the appropriate term container based on variable index.
            if variable_index == 1:
                target_array = L_terms
            elif variable_index == 2:
                target_array = B_terms
            elif variable_index == 3:
                target_array = R_terms
            else:
                # Unsupported variable index; skip the associated terms.
                for _ in range(num_terms):
                    skip_line = f.readline()
                    if not skip_line:
                        break
                continue

            if not (0 <= power_n <= 5):
                # Power outside the expected range; skip the block.
                for _ in range(num_terms):
                    skip_line = f.readline()
                    if not skip_line:
                        break
                continue

            # Ensure the list for this power exists and is empty if reused.
            if target_array[power_n] is None:
                target_array[power_n] = []
            else:
                # Terms may be appended if file contains multiple blocks
                # for the same power, though for VSOP87D.ear this is not expected.
                pass

            # Read num_terms data lines and extract (A, B, C).
            for _ in range(num_terms):
                term_line = f.readline()
                if not term_line:
                    break

                tokens = term_line.strip().split()
                if len(tokens) < 5:
                    # A malformed data line is skipped.
                    continue

                # Last five tokens are: S, K, A, B, C.
                # The VSOP reduced form uses A, B, C in terms:
                #   A * cos(B + C * t)
                # S and K encode the underlying sine/cosine decomposition
                # and are not required for evaluation.
                try:
                    A = float(tokens[-3])
                    B = float(tokens[-2])
                    C = float(tokens[-1])
                except ValueError:
                    # Non-numeric data is skipped.
                    continue

                target_array[power_n].append((A, B, C))

    _VSOP_LOADED = True


def _evaluate_series(terms_by_power: List[List[Tuple[float, float, float]]], t: float) -> float:
    """
    Evaluates a VSOP series (L, B, or R) for a given time argument t.

    The series has the structure:
        X(t) = Σ_{n=0..5} ( Σ_j A_{n,j} cos(B_{n,j} + C_{n,j} * t) ) * t^n

    Args:
        terms_by_power (List[List[Tuple[float, float, float]]]):
            List indexed by n = 0..5, each entry containing the list of
            (A, B, C) terms for that power of t.
        t (float):
            VSOP time argument:
                t = (JD_TT - 2451545.0) / 365250.0

    Returns:
        float: Series value X(t); for L and B this is in radians,
               for R this is in astronomical units.
    """
    value = 0.0
    t_power = 1.0

    for power_n in range(6):
        terms = terms_by_power[power_n]
        if not terms:
            t_power *= t
            continue

        inner_sum = 0.0
        for A, B, C in terms:
            inner_sum += A * math.cos(B + C * t)

        value += inner_sum * t_power
        t_power *= t

    return value


def earth_heliocentric_ecliptic(time: Time) -> Tuple[float, float, float]:
    """
    Computes Earth's heliocentric ecliptic longitude, latitude, and radius vector.

    Uses the VSOP87D series for the Earth (Version D4, spherical coordinates).

    Args:
        time (Time):
            Time instance representing the instant of interest. The calculation
            uses the Terrestrial Time (TT) scale derived from this object.

    Returns:
        Tuple[float, float, float]:
            - L_deg: heliocentric ecliptic longitude in degrees [0, 360).
            - B_deg: heliocentric ecliptic latitude in degrees.
            - R_au : heliocentric radius vector in astronomical units.
    """
    _load_vsop87_earth_if_needed()

    # VSOP time variable t is related to Julian centuries T via t = T / 10.
    # T is in Julian centuries of TT from J2000.0.
    T_tt = time.julian_centuries_tt
    t = T_tt / 10.0

    # Evaluate the series for longitude, latitude, and radius.
    L_rad = _evaluate_series(_L_TERMS, t)
    B_rad = _evaluate_series(_B_TERMS, t)
    R_au = _evaluate_series(_R_TERMS, t)

    # Convert angles to degrees.
    L_deg = math.degrees(L_rad)
    B_deg = math.degrees(B_rad)

    # Normalize longitude to [0, 360).
    L_deg = math.fmod(L_deg, 360.0)
    if L_deg < 0.0:
        L_deg += 360.0

    return L_deg, B_deg, R_au
