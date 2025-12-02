# -*- coding: utf-8 -*-
"""
Seasonal GUI: Analysis Configuration Dialog
===========================================

A modal dialog that asks the user for simulation parameters before
launching the heavy computation.

Inputs:
    - Variable: Altitude / Azimuth (Checkbox)
    - Time Domain: Current Year / Custom
    - Physics: Refraction Toggle
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QGroupBox, 
    QRadioButton, QCheckBox, QDialogButtonBox, QSpinBox
)
from src.gui.windows.graph_window import GraphWindow

class AnalysisDialog(QDialog):
    def __init__(self, lat, lon, parent=None):
        super().__init__(parent)
        self.lat = lat
        self.lon = lon
        self.setWindowTitle(f"Configure Plot: {lat:.3f}, {lon:.3f}")
        self.resize(300, 400)
        
        # Styling
        self.setStyleSheet("""
            QDialog { background-color: #2b2b2b; color: #eee; }
            QGroupBox { border: 1px solid #555; margin-top: 10px; border-radius: 4px; padding-top: 15px; font-weight: bold; color: #aaa; }
            QGroupBox::title { subcontrol-origin: margin; subcontrol-position: top left; left: 10px; padding: 0 3px; }
            QLabel { color: #eee; }
            QCheckBox, QRadioButton { color: #eee; spacing: 8px; }
        """)
        
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # 1. Variable Selection
        grp_var = QGroupBox("Target Variables")
        v_layout = QVBoxLayout()
        
        self.chk_alt = QCheckBox("Solar Altitude (Height)")
        self.chk_alt.setChecked(True)
        self.chk_alt.setEnabled(False) # Forced for this version
        
        v_layout.addWidget(self.chk_alt)
        grp_var.setLayout(v_layout)
        layout.addWidget(grp_var)
        
        # 2. Time Domain
        grp_time = QGroupBox("Time Domain")
        t_layout = QVBoxLayout()
        
        self.rad_year = QRadioButton("Full Year")
        self.rad_year.setChecked(True)
        
        self.spin_year = QSpinBox()
        self.spin_year.setRange(1000, 3000)
        self.spin_year.setValue(2025)
        self.spin_year.setStyleSheet("background: #444; color: white; border: 1px solid #555;")
        
        t_layout.addWidget(self.rad_year)
        t_layout.addWidget(self.spin_year)
        grp_time.setLayout(t_layout)
        layout.addWidget(grp_time)
        
        # 3. Physics Options
        grp_phys = QGroupBox("Physics Engine")
        p_layout = QVBoxLayout()
        
        self.chk_refract = QCheckBox("Atmospheric Refraction")
        self.chk_refract.setChecked(True)
        self.chk_refract.setToolTip("Corrects for light bending near the horizon")
        
        p_layout.addWidget(self.chk_refract)
        grp_phys.setLayout(p_layout)
        layout.addWidget(grp_phys)
        
        layout.addStretch()
        
        # 4. Action Buttons
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def accept(self):
        """Called when user clicks OK/Generate."""
        # Collect Settings
        settings = {
            "year": self.spin_year.value(),
            "refraction": self.chk_refract.isChecked()
        }
        
        # Launch Graph Window
        # Note: We pass 'self.parent()' (MainWindow) as parent to keep window on top logic valid
        # But GraphWindow is a QMainWindow, usually kept independent.
        
        self.graph_win = GraphWindow(self.lat, self.lon, settings)
        self.graph_win.show()
        
        super().accept()