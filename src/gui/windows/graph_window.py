# -*- coding: utf-8 -*-
"""
Seasonal GUI: Graph Window
==========================

The visualization container. It embeds a Matplotlib canvas to render
high-precision scientific plots.

Features:
    - Threaded Calculation: Runs the physics engine in a background thread.
    - Interactive Plot: Matplotlib toolbar (Zoom, Pan, Save).
    - Dynamic Resizing.
"""

from typing import Optional, List, Dict, Any

from PyQt6.QtWidgets import QMainWindow, QVBoxLayout, QWidget, QLabel, QProgressBar
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QCloseEvent

import matplotlib.pyplot as plt
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg, NavigationToolbar2QT

from src.core.time_struct import Time
from src.core.sun_model import SunModel
from src.core.corrections import CorrectionModel
from src.core.sidereal import SiderealTime


# ==============================================================================
# Worker Thread (Prevents GUI Freeze)
# ==============================================================================

class SimulationWorker(QThread):
    """
    Runs the heavy "Yearly Series" calculation in the background.
    """
    dataReady = pyqtSignal(list, list)  # x (days), y (degrees)
    progress = pyqtSignal(int)

    def __init__(self, lat: float, lon: float, year: int, enable_refraction: bool):
        super().__init__()
        self.lat: float = lat
        self.lon: float = lon
        self.year: int = year
        self.enable_refraction: bool = enable_refraction
        self._is_running: bool = True

    def run(self) -> None:
        """Generates the data series."""
        times: List[float] = []
        heights: List[float] = []
        
        # Standard days per month
        days_in_months = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
        
        # Leap year check
        if self.year % 4 == 0 and (self.year % 100 != 0 or self.year % 400 == 0):
            days_in_months[1] = 29
            
        step_minutes = 30  # Resolution
        total_steps = sum(days_in_months) * 24 * (60 // step_minutes)
        count = 0
        current_day_of_year = 0

        # Optimization: Pre-calculate constants
        lat = self.lat
        lon = self.lon
        
        for month_idx, days in enumerate(days_in_months):
            if not self._is_running:
                break
            
            month = month_idx + 1
            for day in range(1, days + 1):
                for hour in range(0, 24):
                    for minute in range(0, 60, step_minutes):
                        
                        # 1. Math Pipeline
                        t = Time.from_gregorian(self.year, month, day, hour, minute, 0.0)
                        sun_geo = SunModel.compute_geocentric_position(t)
                        lst = SiderealTime.apparent_local(t, lon)
                        
                        # 0m elevation for standard plot
                        sun_topo = CorrectionModel.apply_parallax(sun_geo, lat, 0.0, lst)
                        hor = sun_topo.to_horizontal(lat, lst)
                        
                        alt = CorrectionModel.apply_refraction(
                            hor.altitude_degrees, 
                            pressure_mbar=1013, 
                            temp_celsius=15, 
                            enable_refraction=self.enable_refraction
                        )
                        
                        # 2. Store
                        # X-Axis: Fractional Day of Year
                        time_x = current_day_of_year + (hour + minute / 60.0) / 24.0
                        
                        times.append(time_x)
                        heights.append(alt)
                        
                        count += 1
                        
                        # Update progress every 500 steps
                        if count % 500 == 0 and total_steps > 0:
                            self.progress.emit(int(count / total_steps * 100))

                current_day_of_year += 1
                
        self.dataReady.emit(times, heights)

    def stop(self) -> None:
        self._is_running = False


# ==============================================================================
# The Graph Window
# ==============================================================================

class GraphWindow(QMainWindow):
    def __init__(self, lat: float, lon: float, settings: Dict[str, Any]) -> None:
        super().__init__()
        self.lat: float = lat
        self.lon: float = lon
        self.settings: Dict[str, Any] = settings
        
        self.setWindowTitle(f"Solar Analysis: {lat:.4f}, {lon:.4f}")
        self.resize(1000, 600)
        
        # UI Setup
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        
        # 1. Matplotlib Canvas
        self.figure, self.ax = plt.subplots(figsize=(5, 4), dpi=100)
        self.figure.patch.set_facecolor('#1a1a1a')  # Dark background
        self.ax.set_facecolor('#2b2b2b')
        
        # Style axes
        self.ax.tick_params(colors='white')
        self.ax.xaxis.label.set_color('white')
        self.ax.yaxis.label.set_color('white')
        self.ax.title.set_color('white')
        for spine in self.ax.spines.values():
            spine.set_edgecolor('#555')

        self.canvas = FigureCanvasQTAgg(self.figure)
        self.toolbar = NavigationToolbar2QT(self.canvas, self)
        self.toolbar.setStyleSheet("background-color: #ccc;")  # Make icons visible
        
        layout.addWidget(self.toolbar)
        layout.addWidget(self.canvas)
        
        # 2. Loading Bar
        self.loader_label = QLabel("Initializing Simulation...")
        self.loader_label.setStyleSheet("color: #eee;")
        layout.addWidget(self.loader_label)
        
        self.progress = QProgressBar()
        self.progress.setStyleSheet("""
            QProgressBar { border: 1px solid #555; border-radius: 3px; text-align: center; color: white; }
            QProgressBar::chunk { background-color: #007acc; }
        """)
        layout.addWidget(self.progress)
        
        # Worker handle (set in start_computation)
        self.worker: Optional[SimulationWorker] = None
        
        # Start
        self.start_computation()

    def start_computation(self) -> None:
        year = int(self.settings.get("year", 2025))
        refraction = bool(self.settings.get("refraction", True))
        
        self.loader_label.setText(f"Computing Solar Path for Year {year}...")
        
        self.worker = SimulationWorker(self.lat, self.lon, year, refraction)
        self.worker.progress.connect(self.progress.setValue)
        self.worker.dataReady.connect(self.plot_data)
        self.worker.start()

    def plot_data(self, x: list, y: list) -> None:
        self.loader_label.setText("Rendering...")
        self.ax.clear()
        
        # Plot Logic
        self.ax.plot(x, y, color='#ffa500', linewidth=0.5, alpha=0.9, label='Solar Altitude')
        
        # Decorate
        self.ax.set_title(f"Solar Altitude vs Time ({self.settings['year']})")
        self.ax.set_xlabel("Day of Year")
        self.ax.set_ylabel("Altitude (Degrees)")
        self.ax.axhline(0, color='#00aaff', linewidth=1, linestyle='--', label='Horizon')
        self.ax.grid(True, linestyle=':', alpha=0.3, color='#555')
        self.ax.set_xlim(0, 365)
        self.ax.set_ylim(-65, 90)
        
        self.ax.legend(facecolor='#333', edgecolor='white', labelcolor='white')
        
        self.canvas.draw()
        
        # Hide loader
        self.progress.hide()
        self.loader_label.hide()

    def closeEvent(self, event: QCloseEvent) -> None:
        # Kill thread if window closes
        if self.worker is not None and self.worker.isRunning():
            self.worker.stop()
            self.worker.wait()
        event.accept()
