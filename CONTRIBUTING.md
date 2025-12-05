# Contributing to Seasonal

Thank you for your interest in improving Seasonal! This project is licensed under **GPLv3**, so any contributions must be compatible with GPLv3 requirements and you should be comfortable releasing your changes under that license.

If you use Seasonal in research or teaching, please also see **[`CITATION.cff`](./CITATION.cff)** for a machine-readable citation entry.

---

## 1. Code of Conduct

There is no formal code-of-conduct file yet, but the expectations are simple:

- Be respectful and constructive in issues, reviews, and discussions.
- Assume good faith and focus on the technical content.
- Disagreement is fine; personal attacks are not.

This will likely be formalized later as the project grows.

---

## 2. Project Layout (Quick Recap)

Useful when proposing changes:

- **Core physics**: `src/core/`
- **Engine / solvers**: `src/engine/`
- **Web API + frontend glue**: `src/web/`
- **Docs**: `docs/` (including mathematical details in `docs/math.md`)
- **Entry point**: `main.py` (launching the FastAPI server)

Try to keep new code aligned with this separation of concerns.

---

## 3. How to Contribute

### 3.1. Reporting Bugs

When opening a bug report on GitHub Issues, include:

- **Environment**: OS, Python version, how you installed dependencies.
- **Exact input**: location, date/time, and any parameters you used.
- **Expected vs actual behavior**: numbers, plots, or screenshots if relevant.
- **Reproduction steps**: minimal script or API call sequence.

If the bug concerns numerical accuracy, please include:

- The reference ephemeris or tool you compared against.
- The time span and the observed maximum deviation (arcseconds, degrees, etc.).

### 3.2. Requesting Features

For feature requests, explain:

- The **use case** (e.g., PV plant simulation, daylighting analysis, teaching).
- The **level of accuracy** you need (order-of-magnitude is fine).
- Whether this is mainly **backend/physics** or **web UI / visualization**.

This helps decide where it belongs in the architecture and how to scope it.

---

## 4. Development Workflow

### 4.1. Fork and Branch

1. Fork the repository on GitHub.
2. Create a feature branch from the main development branch, for example:
```bash
git checkout -b feature/better-refraction
```

3. Keep your branch focused on one logical change: a bugfix, a refactor, or a new feature.

### 4.2. Commit Style

* Use **clear, concise commit messages**, e.g.:

  * `Fix ΔT polynomial edge case near 1900`
  * `Add endpoint for batch ephemeris queries`
* Group mechanical formatting changes separately from functional changes where possible.

---

## 5. Code Style and Formatting

### 5.1. Python

* Target **Python 3.10+**.
* Use **tabs** for indentation.
* Prefer **type hints** for all public functions and classes.
* Use **docstrings** (triple-quoted, first line as a summary) for:

  * Public functions and methods
  * Public classes
  * Modules with nontrivial behavior

Suggested conventions (even if not yet enforced by tooling):

* General layout compatible with tools like **black**:

  * Max line length around 88–100 characters.
  * Imports grouped as: stdlib, third-party, local.
* Avoid unnecessary dependencies: core numerical code should remain standard-library only.

### 5.2. JavaScript / Frontend

* Prefer **modern ES modules** and `const` / `let` over `var`.
* Keep logic separated by role:

  * Map / 2D logic
  * Globe / 3D logic
  * UI / HUD widgets
* Try to keep each file focused and avoid mixing unrelated responsibilities.

### 5.3. Comments and Documentation

* Comments should explain **why** something is done, or describe non-obvious math/astronomy.
* Mathematical formulas should reference the relevant source where possible (e.g. “Meeus, chapter X”, or an IAU resolution) when the derivation is non-trivial.
* Avoid redundant comments that just restate the code.

---

## 6. Testing and Verification

Even if a full test suite is still evolving, please:

1. **Add or update tests** in a `tests/` directory when touching core or engine logic.

   * Prefer **pytest-style** tests.
   * Focus on:

     * Regression tests for previously failing conditions.
     * Accuracy tests for known dates/locations against a trusted ephemeris (e.g. JPL Horizons, PyEphem, etc. – described in comments, not shipped data).

2. **Run tests locally** before opening a PR:

   ```bash
   pytest
   ```

3. For numerical changes, describe in the PR:

   * The comparison reference (tool or dataset).
   * The time span and locations tested.
   * The observed typical and worst-case errors (e.g. in arcseconds of altitude/azimuth).

If you cannot provide a full reference comparison, at least add sanity checks that ensure the changes do not obviously break existing behavior (e.g., continuity, day/night classification consistency).

---

## 7. Style for Physics / Math Code

For `src/core` and `src/engine` especially:

* Keep functions **pure** whenever reasonable (no I/O, no global state).
* Use **small, well-named helpers** for individual steps:

  * e.g. `compute_nutation()`, `apparent_sun_ra_dec()`, `local_apparent_sidereal_time()`.
* Avoid mixing units:

  * Explicitly document whether functions take **radians vs degrees**, seconds vs days, etc.
  * Consider using clear suffixes in variable names like `_rad`, `_deg`, `_sec`, `_days`.

---

## 8. Web API and UI Changes

When changing the FastAPI app or the frontend:

* Keep API endpoints **backward compatible** where possible.
* If you must change an endpoint:

  * Update the corresponding frontend code.
  * Update any relevant docs in `README.md` or `docs/`.
* For new endpoints, document:

  * Path and method (e.g. `GET /api/ephemeris`).
  * Expected parameters and units.
  * Example of a JSON response.

UI changes should not degrade the readability of the main 2D/3D views or the clarity of key numerical outputs (alt/az, sunrise/sunset times, etc.).

---

## 9. Licensing and Attribution

* Seasonal is distributed under **GPLv3**.
* By contributing, you agree that your contributions will be licensed under **GPLv3** as well.
* Do not submit code that you do not have the right to license under GPLv3.
* If you add third-party data or code, clearly document its origin and license, and make sure it is compatible.

For citation formats and metadata (useful in research contexts and for services like Zenodo), see **[`CITATION.cff`](./CITATION.cff)**.

---

## 10. Opening a Pull Request

When your changes are ready:

1. Push your branch to your fork.
2. Open a **Pull Request** against the repository’s main development branch.
3. In the PR description, include:

   * A short summary of the change.
   * Any relevant screenshots (for UI changes).
   * Notes on testing and accuracy validation.
   * Any potential follow-up work or limitations.

Reviews will focus on correctness (especially numerics), clarity, and consistency with the project’s architecture.
