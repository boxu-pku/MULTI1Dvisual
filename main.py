#!/usr/bin/env python3
"""
MULTI1D Visualizer v2.3.1.1 - Main Entry Point
A GUI application for visualizing MULTI1D simulation output files.
Supports direct reading of fort.10 binary files.
"""
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt

from ui.main_window import MainWindow
from utils.config import Config
from utils.logger import Logger


def main():
    """Main entry point"""
    # Initialize logger
    Logger.init()
    logger = Logger.get_logger('Main')

    logger.info(f"启动 {Config.APP_NAME} v{Config.APP_VERSION}")

    # Enable high DPI scaling
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

    app = QApplication(sys.argv)
    app.setApplicationName(Config.APP_NAME)
    app.setApplicationVersion(Config.APP_VERSION)

    # Set style
    app.setStyle('Fusion')

    # Create and show main window
    window = MainWindow()
    window.showMaximized()

    logger.info("主窗口已显示")

    # Run application
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
