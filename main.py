#!/usr/bin/env python3
"""
Xiangqi (象棋) GUI Application
Main entry point
"""

import sys
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt

from main_window import MainWindow


def main():
    # Enable high DPI scaling
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    
    app = QApplication(sys.argv)
    app.setApplicationName("中国象棋")
    app.setStyle("Fusion")
    
    # Set stylesheet for better appearance
    app.setStyleSheet("""
        QMainWindow {
            background-color: #f5f5f5;
        }
        QMenuBar {
            background-color: #ffffff;
            border-bottom: 1px solid #ddd;
        }
        QMenuBar::item:selected {
            background-color: #e0e0e0;
        }
        QMenu {
            background-color: #ffffff;
            border: 1px solid #ddd;
        }
        QMenu::item:selected {
            background-color: #4a90d9;
            color: white;
        }
        QToolBar {
            background-color: #ffffff;
            border-bottom: 1px solid #ddd;
            spacing: 5px;
            padding: 5px;
        }
        QToolBar QToolButton {
            padding: 5px 10px;
            border-radius: 3px;
        }
        QToolBar QToolButton:hover {
            background-color: #e0e0e0;
        }
        QStatusBar {
            background-color: #ffffff;
            border-top: 1px solid #ddd;
        }
        QPushButton {
            padding: 5px 15px;
            border: 1px solid #ccc;
            border-radius: 3px;
            background-color: #ffffff;
        }
        QPushButton:hover {
            background-color: #e8e8e8;
        }
        QPushButton:pressed {
            background-color: #d0d0d0;
        }
        QGroupBox {
            font-weight: bold;
            border: 1px solid #ccc;
            border-radius: 5px;
            margin-top: 10px;
            padding-top: 10px;
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            left: 10px;
            padding: 0 5px;
        }
        QSpinBox, QComboBox {
            padding: 5px;
            border: 1px solid #ccc;
            border-radius: 3px;
        }
    """)
    
    window = MainWindow()
    window.show()
    
    return app.exec_()


if __name__ == "__main__":
    sys.exit(main())
