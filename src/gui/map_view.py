# -*- coding: utf-8 -*-
"""
Seasonal GUI: Map View Component
================================

This module provides the interactive Map Widget. It embeds a Chromium browser
(via QWebEngineView) to render the Leaflet.js map defined in `resources/map.html`.

It establishes a bi-directional bridge (QWebChannel) allowing:
1. Python -> JS: Update Terminator, Sun Icon, or trigger visual events.
2. JS -> Python: Handle map clicks and analysis requests.
"""

import os
import json
import pandas as pd # Used for robust JD -> ISO String conversion
from PyQt6.QtWidgets import QWidget, QVBoxLayout
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import QWebEngineSettings # Import Settings
from PyQt6.QtWebChannel import QWebChannel
from PyQt6.QtCore import QUrl, QObject, pyqtSlot, pyqtSignal, QFile, QIODevice, Qt

from src.core.time_struct import Time
from src.core.sun_model import SunModel
from src.core.corrections import CorrectionModel
from src.core.sidereal import SiderealTime

# ==============================================================================
# The Bridge Object (Python <-> JS)
# ==============================================================================

class PyBridge(QObject):
    """
    Object exposed to JavaScript. 
    Functions decorated with @pyqtSlot can be called from JS.
    """
    
    # Signals to notify the Main Window when JS triggers an event
    analysisRequested = pyqtSignal(float, float) # lat, lon

    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_time: Time = None

    def set_current_time(self, t: Time):
        self._current_time = t

    @pyqtSlot(float, float)
    def onMapClicked(self, lat, lon):
        """
        Called by JS when the user clicks the map.
        We calculate instantaneous solar data and send it back to JS for the popup.
        """
        if not self._current_time:
            return

        print(f"[Map] Clicked at {lat:.4f}, {lon:.4f}")

        # 1. Run the Math
        t = self._current_time
        
        # Geocentric Position
        sun_geo = SunModel.compute_geocentric_position(t)
        
        # Local Sidereal Time
        lst = SiderealTime.apparent_local(t, lon)
        
        # Topocentric Parallax
        # Assume sea level (0m) for map probing unless we use a DEM API
        sun_topo = CorrectionModel.apply_parallax(sun_geo, lat, 0.0, lst)
        
        # Horizontal Coordinates
        hor = sun_topo.to_horizontal(lat, lst)
        
        # Refraction (Standard)
        alt_app = CorrectionModel.apply_refraction(
            hor.altitude_degrees, pressure_mbar=1013, temp_celsius=15, enable_refraction=True
        )

        # 2. Format Data for the Popup (HTML)
        # We determine if it is Day or Night based on Altitude
        state_color = "#FFD700" if alt_app > 0 else "#888";
        state_text = "DAY" if alt_app > 0 else "NIGHT"
        
        # Calculate full JD for display
        total_jd = t.jd_utc[0] + t.jd_utc[1]
        
        html = f"""
        <div style="display: flex; justify-content: space-between; align-items: center;">
            <b style="color: {state_color}; font-size: 14px;">{state_text}</b>
            <span style="font-family: monospace;">{total_jd:.2f} JD</span>
        </div>
        <hr style="border: 0; border-top: 1px solid #444; margin: 5px 0;">
        <table style="width: 100%; font-size: 12px; color: #ddd;">
            <tr><td>Altitude:</td><td style="text-align: right;"><b>{alt_app:.2f}°</b></td></tr>
            <tr><td>Azimuth:</td><td style="text-align: right;"><b>{hor.azimuth_degrees:.2f}°</b></td></tr>
            <tr><td>Right Asc:</td><td style="text-align: right;">{sun_topo.ra_hours:.2f}h</td></tr>
            <tr><td>Declination:</td><td style="text-align: right;">{sun_topo.dec_degrees:.2f}°</td></tr>
        </table>
        """
        
        # 3. Call JS back to show popup
        if self.parent():
            self.parent().show_popup_in_js(lat, lon, f"Pos: {lat:.3f}, {lon:.3f}", html)

    @pyqtSlot(float, float)
    def requestAnalysis(self, lat, lon):
        """Called when user clicks 'Detailed Plot' in the popup."""
        print(f"[Map] Analysis Requested for {lat}, {lon}")
        self.analysisRequested.emit(lat, lon)

# ==============================================================================
# The Map Widget
# ==============================================================================

class MapWidget(QWebEngineView):
    """
    The Main Map Component.
    Wraps the HTML/Leaflet engine and manages the Python-JS Bridge.
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # 1. Setup Bridge
        self.channel = QWebChannel()
        self.bridge = PyBridge(self) # Pass self as parent so Bridge can call back
        self.channel.registerObject("pyBridge", self.bridge)
        self.page().setWebChannel(self.channel)

        # 2. Configure Settings to allow Remote Content (FIX for 'L is not defined')
        settings = self.settings()
        settings.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.LocalStorageEnabled, True)
        
        # 3. Load Resources
        # Resolve absolute path to map.html
        current_dir = os.path.dirname(os.path.abspath(__file__))
        html_path = os.path.join(current_dir, "resources", "map.html")
        
        if not os.path.exists(html_path):
            print(f"ERROR: Map HTML not found at {html_path}")
            self.setHtml(f"<h1>Error: map.html not found</h1><p>{html_path}</p>")
        else:
            self.setUrl(QUrl.fromLocalFile(html_path))
            
        # 4. UI Settings
        # FIXED: Must use Enum in PyQt6, not int(0)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.NoContextMenu) 

    def update_time(self, t: Time):
        """
        Updates the map's Day/Night terminator and Sun position.
        
        Args:
            t (Time): The current simulation time.
        """
        # Update the bridge's internal time (for click calculations)
        self.bridge.set_current_time(t)
        
        # 1. Calculate Solar Position
        sun_geo = SunModel.compute_geocentric_position(t)
        gmst = SiderealTime.mean_greenwich(t)
        
        # 2. Calculate Sub-Solar Point (Zenith)
        # Latitude = Declination
        sub_solar_lat = sun_geo.dec_degrees
        
        # Longitude = RA - GMST
        # Explanation: The Sun is at the meridian (Longitude 0 relative to sky) when LST = RA.
        # LST = GMST + Lon. So RA = GMST + Lon => Lon = RA - GMST.
        sub_solar_lon = sun_geo.ra_degrees - gmst
        
        # Normalize Longitude to [-180, 180] for Leaflet
        sub_solar_lon = (sub_solar_lon + 180) % 360 - 180
        
        # 3. Generate ISO Date String for Leaflet.Terminator
        # The JS library needs a Date() compatible string to calculate the shadow shape.
        # We use pandas for a robust JD -> ISO conversion.
        try:
            total_jd = t.jd_utc[0] + t.jd_utc[1]
            ts = pd.to_datetime(total_jd, unit='D', origin='julian')
            iso_date_str = ts.isoformat()
        except Exception as e:
            print(f"Error converting Date: {e}")
            return

        # 4. Send to JS
        self.set_solar_state(iso_date_str, sub_solar_lat, sub_solar_lon)

    def set_solar_state(self, iso_date_str, sub_solar_lat, sub_solar_lon):
        """
        Direct API to update JS variables.
        """
        # Encode data to JSON to prevent syntax errors in JS injection
        safe_date = json.dumps(iso_date_str)
        
        script = f"updateSolarState({safe_date}, {sub_solar_lat}, {sub_solar_lon});"
        self.page().runJavaScript(script)

    def show_popup_in_js(self, lat, lon, title, html_content):
        """
        Executes JS to open a popup at the specific location.
        """
        # Sanitize strings for JS injection
        safe_title = json.dumps(title)
        safe_html = json.dumps(html_content)
        
        script = f"showLocationPopup({lat}, {lon}, {safe_title}, {safe_html});"
        self.page().runJavaScript(script)