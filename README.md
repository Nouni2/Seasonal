# Seasonal: High-Precision Solar Tracking Engine

Seasonal is a high-precision solar position engine with a web-based UI.  
It computes the Sun’s apparent position (altitude/azimuth) using a full physical model (VSOP87D Earth ephemeris, nutation, aberration, topocentric parallax, atmospheric refraction) and exposes it via a FastAPI backend and browser front-end (2D map + 3D globe).

The goal is **arcsecond-level accuracy** suitable for scientific, architectural, and solar engineering use, not just “good enough for visuals” game-style sun tracking.

For the full mathematical specification and derivations, see **[`docs/math.md`](docs/math.md)**.

---

## Citing Seasonal / Academic Use

If you use Seasonal in research, teaching, or publications, please cite it.

Machine-readable citation metadata is provided in **[`CITATION.cff`](./CITATION.cff)**, which GitHub and tools like Zenodo can parse directly.

A typical citation would be:

> Youssoufi, M. (2025). *Seasonal: High-Precision Solar Tracking Engine* (Version 1.0.0) \[Computer software\]. GPL-3.0. Available at https://github.com/Nouni2/Seasonal

For exact fields and alternate formats (BibTeX, etc.), use the contents of `CITATION.cff` or the “Cite this repository” button on GitHub.

---

## 1. Features

- **High-precision ephemeris**
  - VSOP87D-based Earth heliocentric model for the Sun’s apparent motion.
  - Full time system handling (UTC vs TT, ΔT polynomials).
  - Nutation, true obliquity, and annual aberration corrections.

- **Observer-centric physics**
  - Topocentric parallax on an ellipsoidal Earth (WGS84).
  - Atmospheric refraction using Saemundsson’s formula with pressure/temperature scaling.
  - Output in standard horizontal coordinates (altitude, azimuth; 0° azimuth = North, 90° = East).

- **Daylight and events**
  - Sunrise, sunset, transit (local solar noon) and day length classification:
    - NORMAL
    - POLAR_DAY
    - POLAR_NIGHT

- **Web UI**
  - FastAPI backend serving:
    - Real-time ephemeris (alt/az).
    - Subsolar point (for terminator / day–night map).
    - Day events and day length per date.
    - Time-series analysis of day length over a range.
  - Frontend:
    - **2D map** (Leaflet) with live day–night terminator overlay.
    - **3D globe** (Three.js) with:
      - Day/night textures
      - Night lights
      - Cloud layer and atmosphere glow
      - Click-to-select location using raycasting.
    - HUD with:
      - UTC clock + approximate local mean solar time.
      - Live altitude/azimuth readout at chosen location.
      - 24h day/night bar with sunrise/sunset and duration.
      - Analysis modal with Plotly charts of day length vs date.

---

## 2. Architecture Overview

Seasonal is structured into three main layers:

1. **Core Physics (`src/core`)**  
   Pure math and physics:
   - Time representation and ΔT
   - VSOP87D Earth model
   - Ecliptic/Equatorial/Horizontal coordinate transformations
   - Sidereal time
   - Topocentric parallax
   - Atmospheric refraction

2. **Engine / Solver (`src/engine`)**  
   High-level logic built on the core physics:
   - `SolarEventSolver` for sunrise, sunset, transit, and day-length classification.
   - Numerical methods (transit refinement, secant solver for altitude=0).

3. **Web Layer (`src/web`)**  
   API and user interface:
   - FastAPI app (`server.py`) exposing endpoints:
     - `/api/ephemeris` – Sun’s apparent position for a given instant.
     - `/api/subsolar` – Subsolar point (lat/lon) at a given instant.
     - `/api/day-events` – Sunrise, sunset, transit and day type for a date.
     - `/api/analyze` – Day-length time series for a date range.
   - Static assets:
     - `static/css` – HUD and layout styling.
     - `static/js` – Map controller, globe controller, widgets/controller logic.
     - `static/assets/textures` – Earth textures for the 3D globe.
   - HTML template:
     - `templates/index.html` – Main single-page interface.

---

## 3. Mathematical Model (Short Version)

The high-level pipeline to get from a civil timestamp and location to altitude/azimuth is:

1. **Time handling**
   - Input: calendar date/time in UTC.
   - Convert to Julian Date (JD) with a split representation:
     - `jd_day` (integer day)
     - `jd_fraction` (fraction of day)
   - Compute ΔT = TT − UTC using Espenak/Meeus polynomials.
   - Obtain TT-based JD and Julian centuries `T` for orbital work.

2. **Heliocentric → Geocentric**
   - Use VSOP87D Earth series to get the Earth’s heliocentric ecliptic coordinates (L, B, R).
   - Invert the vector to get Sun’s geocentric ecliptic position.
   - Apply nutation and annual aberration corrections.
   - Compute true obliquity of the ecliptic.

3. **Ecliptic → Equatorial**
   - Transform apparent ecliptic longitude/latitude to geocentric equatorial coordinates (RA, Dec).

4. **Earth rotation**
   - Compute Greenwich Mean Sidereal Time (GMST) from JD.
   - Apply equation of the equinoxes for apparent sidereal time.
   - Add observer longitude for Local Apparent Sidereal Time (LST).

5. **Topocentric corrections**
   - Model observer’s position on WGS84 ellipsoid using latitude, elevation and flattening.
   - Apply solar parallax to shift from geocentric to topocentric RA/Dec.

6. **Equatorial → Horizontal**
   - Use LST and topocentric RA/Dec to compute:
     - Hour angle
     - Geometric altitude and azimuth (compass convention: 0° = North).

7. **Atmospheric refraction**
   - If the geometric altitude is near the horizon, apply Saemundsson’s refraction formula.
   - Scale refraction by pressure and temperature.
   - Return apparent altitude.

For step-by-step formulas and more detailed derivations, see **[`docs/math.md`](docs/math.md)**.

---

## 4. Running Seasonal Locally

### Requirements

- **Python**: 3.10+
- **Backend Python packages** (typical):
  - `fastapi`
  - `uvicorn`
  - `pydantic`
- Core math uses only the standard library (`math`, `dataclasses`, etc.), no heavy scientific stack is required for the current code.

The frontend uses:

- Leaflet (via CDN)
- Three.js (via CDN)
- Plotly (via CDN)
- Font Awesome + Google Fonts (via CDN)

---

## 5. Contributing

Contributions, bug reports, and improvements are welcome.

For contribution guidelines (code style, testing expectations, and workflow), see **[`CONTRIBUTING.md`](./CONTRIBUTING.md)**. By contributing, you agree that your changes are released under the same license as the project (GPLv3).

---

## 6. License

This project is distributed under the **GNU General Public License v3.0 (GPLv3)**. You are free to use, study, modify, and redistribute the code, but any distributed modified or extended versions must also be released under GPLv3.

For the full legal text, see the [`LICENSE`](LICENSE) file.
