# Seasonal: Validation & Verification Protocol

## 1. Objective

To certify that the Seasonal engine achieves arcsecond-level precision ($\pm 0.00028^\circ$) by comparing its output against the NASA Jet Propulsion Laboratory (JPL) Horizons On-Line Ephemeris System.

## 2. The Gold Standard (Source of Truth)

We will not use other Python libraries (like pyswisseph or astropy) as benchmarks, as they are implementations, not primary sources. We will compare directly against the numerical integration provided by JPL.

### 2.1 JPL Horizons Configuration

For all test vectors, the Horizons query must use the following strictly defined parameters to match our physics model:

Ephemeris Type: Observer Quantities

Target Body: Sun [Sol]

Observer Location: Geodetic Coordinates (Matches our Topocentric model)

Refraction Model: NONE (We test Geometric Altitude first) and Standard Atmosphere (We test Refraction separately).

Time System: UT1/UTC (To test our $\Delta T$ implementation).

Output Quantities:

4. Apparent Azimuth & Elevation (Az, El)

5. Visual Magnitude & Surf Brightness (Optional check)

6. Sidereal Time (To verify LST calculations)

7. Obs-ecliptic lon. & lat. (To verify Geocentric stages)

## 3. Test Vectors (Stress Cases)

The engine must pass the following 5 distinct scenarios.

Scenario A: The "Standard" Day (Baseline)

Date: 2025-06-21 (Summer Solstice)

Location: Greenwich, UK ($51.4934^\circ N, 0.0^\circ E, 0m$)

Objective: Verify basic alignment with the Prime Meridian and standard atmosphere.

---

Scenario B: The "High Latitude" Stress Test

Date: 2024-12-21 (Winter Solstice)

Location: Longyearbyen, Svalbard ($78.2232^\circ N, 15.6267^\circ E, 0m$)

Objective: At high latitudes, the math for Azimuth becomes unstable near the Zenith/Nadir. This tests the robustness of the atan2 implementation and Refraction at extremely low altitudes.

---

Scenario C: The "Delta T" Deep Past

Date: 1500-01-01 (Julian Calendar transition era)

Location: Cairo, Egypt ($30.0444^\circ N, 31.2357^\circ E$)

Objective: Verify that the Historical $\Delta T$ lookup tables are functioning. If $\Delta T$ is ignored here, the sun will be offset by degrees.

---

Scenario D: The "Far Future" Extrapolation

Date: 3000-01-01

Location: Quito, Ecuador ($0.1807^\circ S, 78.4678^\circ W$ - Equator)

Objective: Verify the polynomial stability of the VSOP87 truncation and Future $\Delta T$ predictions.

---

Scenario E: The "Topocentric" Check (Elevation)

Date: 2025-03-20 (Equinox)

Location: Mauna Kea, Hawaii ($19.8206^\circ N, 155.4681^\circ W, 4205m$)

Objective: Verify the Parallax correction. At 4000m altitude, the horizon dip and parallax shift are significant.

## 4. Acceptance Criteria

For each test vector, the Seasonal engine output must be compared to the JPL CSV Data.

| Parameter       | Metric    | Max Tolerance  | Notes                                                            |
| --------------- | --------- | -------------- | ---------------------------------------------------------------- |
| Julian Date     | Abs(Diff) | $10^{-6}$ days | $\approx 0.08$ seconds precision required.                       |
| LST             | Abs(Diff) | $0.1$ seconds  | Checks Longitude and GMST polynomials.                           |
| Azimuth         | Abs(Diff) | $1.0$ arcsec   | $0.00027^\circ$. Large error here usually means $\Delta T$ fail. |
| Altitude (Geom) | Abs(Diff) | $1.0$ arcsec   | Checks basic orbital geometry and parallax.                      |
| Altitude (App)  | Abs(Diff) | $5.0$ arcsec   | Refraction models vary slightly; 5" is acceptable.               |

## 5. Automated Verification Pipeline

To ensure "Non-Destructive" testing:

Download: We will manually download the CSVs for Scenarios A-E from JPL Horizons.

Storage: Save them in tests/reference_data/.

Runner: The Python test runner (pytest) will load these CSVs, run the Engine for the same timestamps, and assert that the difference is within Tolerance.
