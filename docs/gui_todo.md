This is the **Technical Roadmap** for building the "Day/Night Explorer" GUI. This plan prioritizes the architecture of the **Python $\leftrightarrow$ JavaScript Bridge**, which is the most critical technical challenge in hybrid apps.

### Phase 1: The "Map Engine" Foundation
*Goal: Get a Leaflet map running inside Python with Day/Night shading.*

* [ ] **Dependency Check:** Ensure `PyQt6-WebEngine` is installed (it is often separate from `PyQt6`).
* [ ] **Create `src/gui/resources/map.html`:**
    * This will be the "frontend" of the map.
    * **Include:** Leaflet.js (CSS/JS) and a `leaflet-terminator.js` plugin (for the night shadow).
    * **Logic:** Initialize a full-screen map, disable default zoom controls (for a cleaner look), and initialize the `L.terminator()` object.
* [ ] **Create `src/gui/map_view.py`:**
    * **Class:** `MapWidget(QWebEngineView)`
    * **Init:** Load the local `map.html` file.
    * **Bridge:** Initialize `QWebChannel` to allow Python to call JS functions (e.g., `updateTime()`) and JS to call Python functions (e.g., `onMapClicked()`).

### Phase 2: The Time Controller (The "State")
*Goal: Connect the visual slider to the mathematical engine.*

* [ ] **Create `src/gui/widgets/time_bar.py`:**
    * **Layout:** A custom widget with a `QSlider` (range 0–1440 for minutes in a day) and a central `QLabel` for the timestamp.
    * **Logic:** When the slider moves, emit a `timeChanged(Time)` signal.
* [ ] **Wire the "Heartbeat":**
    * In `main_window.py`, connect the Slider signal to the Map.
    * **Action:** When slider moves $\to$ Python calculates new Greenwich Mean Sidereal Time (GMST) $\to$ Python calls JS `setTerminator(gmst)` $\to$ JS redraws the shadow instantly.

### Phase 3: The "Probe" Interaction (The Bridge)
*Goal: Clicking the map queries the Python Math Engine.*

* [ ] **JavaScript Side (In `map.html`):**
    * Add a click listener: `map.on('click', function(e) { pyBridge.handleMapClick(e.latlng.lat, e.latlng.lng); })`
* [ ] **Python Side (In `main_window.py`):**
    * Implement the slot `handleMapClick(lat, lon)`.
    * **Math:** Call `SunModel.compute(...)` and `CorrectionModel.apply(...)` for the *current slider time*.
    * **Feedback:** Call JS back: `showPopup(lat, lon, "Alt: 45°", "Az: 180°")`.
    * *Note:* The popup in JS must contain an HTML button: `<button id="btn-plot">Detailed Plot</button>`.

### Phase 4: The Analysis Window (The Plotter)
*Goal: The floating window configuration and rendering.*

* [ ] **Create `src/gui/dialogs/plot_config.py`:**
    * A modal `QDialog`.
    * **Inputs:** DateRangePicker, Checkbox for "Refraction", Radio buttons for "Variable" (Height/Azimuth).
* [ ] **Create `src/gui/windows/graph_window.py`:**
    * A separate, non-modal `QMainWindow` (so it can float/drag to another screen).
    * **Component:** An embedded `Matplotlib` canvas (`FigureCanvasQTAgg`).
* [ ] **The Data Pipeline:**
    * On "Generate":
        1.  Spawn a `QThread` (Worker).
        2.  Worker runs `streamer.generate_yearly_series(...)` (using the logic we verified).
        3.  On finish: Pass vectors (X, Y) to the `GraphWindow` to plot.

### Phase 5: Polish & "Juice"
*Goal: Make it feel like a scientific instrument.*

* [ ] **Debouncing:** Ensure the map update only fires every ~30ms during slider drag to prevent lagging the UI thread.
* [ ] **Sync Marker:** When the Graph Window is open, moving the Time Slider in the main window should draw a vertical line on the graph showing the current time position.

---

### Immediate Next Step
We need to build **Phase 1 (The Map Engine)**.
This involves creating the HTML file and the Python wrapper.

**Shall we start by creating the `map.html` file to ensure we can render a basic map with a day/night terminator?**