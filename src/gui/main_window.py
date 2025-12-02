# -*- coding: utf-8 -*-
"""
Seasonal GUI: Main Window
=========================

The primary application container. It acts as the "Switchboard" connecting
the Spatial View (Map) and the Temporal Controller (TimeBar).

Architecture:
    - Central Widget: QVBoxLayout
        - MapWidget (Expands to fill space)
        - TimeBar (Fixed height at bottom)

Signal Wiring:
    - TimeBar.timeChanged -> MapWidget.update_time
    - MapWidget.bridge.analysisRequested -> open_analysis_dialog
"""

from PyQt6.QtWidgets import QMainWindow, QWidget, QVBoxLayout
from PyQt6.QtCore import Qt

from src.gui.map_view import MapWidget
from src.gui.widgets.time_bar import TimeBar
from src.gui.dialogs.analysis_dialog import AnalysisDialog # New Import

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        
        # 1. Window Setup
        self.setWindowTitle("Seasonal: Scientific Solar Tracker")
        self.resize(1280, 800)
        
        # Use a dark scientific theme for the window frame
        self.setStyleSheet("QMainWindow { background-color: #1a1a1a; }")
        
        # 2. Central Layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(0, 0, 0, 0) # Edge-to-edge
        layout.setSpacing(0)
        
        # 3. Components
        
        # A. The Map (Space) - Stretch Factor 1 (Takes all available space)
        self.map_view = MapWidget()
        layout.addWidget(self.map_view, stretch=1)
        
        # B. The Time Deck (Time) - Stretch Factor 0 (Fixed height)
        self.time_bar = TimeBar()
        layout.addWidget(self.time_bar, stretch=0)
        
        # 4. Wiring (The "Brain")
        
        # Connection 1: Time -> Space
        # When user moves slider, tell map to update Shadow/Sun Icon
        self.time_bar.timeChanged.connect(self.map_view.update_time)
        
        # Connection 2: Space -> Analysis
        # When user clicks "Detailed Plot" in the HTML Popup
        self.map_view.bridge.analysisRequested.connect(self._on_analysis_requested)
        
        # Connection 3: Init Loop
        # When the map finishes loading HTML, send the initial time state immediately
        # so the user doesn't see an empty map until they move the slider.
        self.map_view.loadFinished.connect(self._on_map_ready)

    def _on_map_ready(self, success):
        """Called when HTML/JS is fully loaded."""
        if not success:
            print("ERROR: Map failed to load.")
            return
            
        print("System: Map Engine Ready. Syncing Time...")
        # Force an update with the current slider state
        initial_time = self.time_bar.get_current_time()
        self.map_view.update_time(initial_time)

    def _on_analysis_requested(self, lat, lon):
        """
        Slot called when user wants to plot data for a specific pin.
        Opens the Analysis Configuration Dialog.
        """
        print(f"System: Opening Analysis for {lat}, {lon}...")
        
        # Open the Configuration Dialog (Non-modal or Modal?)
        # Let's make it Modal so they focus on config
        dialog = AnalysisDialog(lat, lon, parent=self)
        dialog.exec()