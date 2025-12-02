# -*- coding: utf-8 -*-
"""
Seasonal GUI: Time Controller Widget
====================================

This module implements the "Time Deck" - the bottom bar of the application.
It controls the temporal state of the simulation.

Features:
    - 24-Hour Slider (Minute resolution).
    - Date Navigation (Prev/Next Day).
    - Playback (Animation of time).
    - Digital Readout (UTC).
"""

from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QSlider, QLabel, QPushButton, 
    QStyle, QDateEdit
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QDate, QTime

from src.core.time_struct import Time

class TimeBar(QWidget):
    """
    The main time control widget.
    Emits `timeChanged(Time)` when the user interacts with controls.
    """
    
    # Signal carrying the new Physics Time object
    timeChanged = pyqtSignal(Time)

    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Internal State
        # Default to today
        current = QDate.currentDate()
        self._year = current.year()
        self._month = current.month()
        self._day = current.day()
        self._minutes = 720 # Noon (12:00)
        self._is_playing = False
        
        # Animation Timer
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._on_tick)
        self.timer.setInterval(50) # 20 FPS updates
        
        self._init_ui()
        self._update_readout()

    def _init_ui(self):
        """Setup the layout and widgets."""
        # Main vertical layout (Slider on top, Controls below)
        # Or Horizontal strip? 
        # Design doc said: "Sleek 'Player' bar at the bottom."
        # Let's do:
        # [Slider ------------------------------------------------]
        # [ < Day ] [ Play ] [ Day > ]   [ 2025-06-21 12:00 UTC ]
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 5, 10, 10)
        layout.setSpacing(5)
        
        # 1. The Timeline Slider
        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setRange(0, 1439) # 00:00 to 23:59
        self.slider.setValue(self._minutes)
        self.slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.slider.setTickInterval(60) # Tick every hour
        self.slider.valueChanged.connect(self._on_slider_moved)
        
        # Style the slider to look scientific (Optional css later)
        layout.addWidget(self.slider)
        
        # 2. Controls Row
        ctrl_layout = QHBoxLayout()
        
        # Date Controls
        self.btn_prev_day = QPushButton("← Day")
        self.btn_prev_day.clicked.connect(self._prev_day)
        
        self.btn_next_day = QPushButton("Day →")
        self.btn_next_day.clicked.connect(self._next_day)
        
        # Playback
        self.btn_play = QPushButton()
        self.update_play_icon()
        self.btn_play.clicked.connect(self._toggle_play)
        
        # Readout (Large Font)
        self.lbl_readout = QLabel("Loading...")
        self.lbl_readout.setStyleSheet("font-size: 16px; font-weight: bold; font-family: monospace; color: #eee;")
        self.lbl_readout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Add to layout
        ctrl_layout.addWidget(self.btn_prev_day)
        ctrl_layout.addWidget(self.btn_play)
        ctrl_layout.addWidget(self.btn_next_day)
        ctrl_layout.addStretch() # Spacer
        ctrl_layout.addWidget(self.lbl_readout)
        ctrl_layout.addStretch() # Spacer
        
        layout.addLayout(ctrl_layout)
        
        # Dark Theme Background for the bar
        self.setStyleSheet("""
            QWidget { background-color: #2b2b2b; color: #ddd; }
            QSlider::groove:horizontal {
                border: 1px solid #555; height: 8px; background: #1a1a1a; margin: 2px 0; border-radius: 4px;
            }
            QSlider::handle:horizontal {
                background: #007acc; border: 1px solid #007acc; width: 18px; margin: -6px 0; border-radius: 9px;
            }
            QPushButton {
                background-color: #444; border: none; padding: 5px 15px; border-radius: 3px;
            }
            QPushButton:hover { background-color: #555; }
        """)

    def update_play_icon(self):
        """Sets standard Qt icons for play/pause."""
        icon = self.style().standardIcon(
            QStyle.StandardPixmap.SP_MediaPause if self._is_playing else QStyle.StandardPixmap.SP_MediaPlay
        )
        self.btn_play.setIcon(icon)

    # ==========================================================================
    # Logic
    # ==========================================================================

    def _on_slider_moved(self, value):
        """Called when user drags slider."""
        self._minutes = value
        self._update_readout()
        self._emit_time()

    def _prev_day(self):
        """Jump back 24h."""
        self._add_days(-1)

    def _next_day(self):
        """Jump forward 24h."""
        self._add_days(1)

    def _add_days(self, days):
        # Use QDate to handle leap years/month rollovers easily
        d = QDate(self._year, self._month, self._day)
        d = d.addDays(days)
        self._year = d.year()
        self._month = d.month()
        self._day = d.day()
        self._update_readout()
        self._emit_time()

    def _toggle_play(self):
        self._is_playing = not self._is_playing
        self.update_play_icon()
        if self._is_playing:
            self.timer.start()
        else:
            self.timer.stop()

    def _on_tick(self):
        """Called by timer for animation."""
        # Increment time (e.g., 5 minutes per tick)
        step = 5 
        new_val = self._minutes + step
        
        if new_val >= 1440:
            # New Day
            new_val -= 1440
            self._add_days(1) # This emits, so we just update slider
            
            # Block signal to prevent double emission from slider change
            self.slider.blockSignals(True)
            self.slider.setValue(new_val)
            self.slider.blockSignals(False)
            self._minutes = new_val
        else:
            self.slider.setValue(new_val)

    def _update_readout(self):
        """Updates the text label."""
        h = self._minutes // 60
        m = self._minutes % 60
        # Format: YYYY-MM-DD HH:MM UTC
        text = f"{self._year:04d}-{self._month:02d}-{self._day:02d}  {h:02d}:{m:02d}:00 UTC"
        self.lbl_readout.setText(text)

    def _emit_time(self):
        """Constructs the Physics Time object and emits it."""
        h = self._minutes // 60
        m = self._minutes % 60
        
        # Create Core Time Object
        t = Time.from_gregorian(self._year, self._month, self._day, h, m, 0.0)
        self.timeChanged.emit(t)

    # ==========================================================================
    # Public API
    # ==========================================================================
    
    def get_current_time(self) -> Time:
        """Returns the current state as a Time object."""
        h = self._minutes // 60
        m = self._minutes % 60
        return Time.from_gregorian(self._year, self._month, self._day, h, m, 0.0)