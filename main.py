# -*- coding: utf-8 -*-
"""
Seasonal: Application Entry Point
=================================

Bootstraps the PyQt6 Application and launches the Main Window.
"""

import sys
import os

# Ensure src is in path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from PyQt6.QtWidgets import QApplication
from src.gui.main_window import MainWindow

def main():
    # 1. Init Qt Application
    app = QApplication(sys.argv)
    app.setApplicationName("Seasonal")
    app.setOrganizationName("ScientificCommunity")
    
    # 2. Launch Main Window
    window = MainWindow()
    window.show()
    
    # 3. Event Loop
    sys.exit(app.exec())

if __name__ == "__main__":
    main()