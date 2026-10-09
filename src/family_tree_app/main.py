import sys
from pathlib import Path
from PySide6.QtWidgets import QApplication
from family_tree_app.db import Database
from family_tree_app.ui.main_window import MainWindow

MODERN_STYLE = """
/* Global Default */
QWidget {
    font-family: "Segoe UI", "Helvetica Neue", Helvetica, Arial, sans-serif;
    font-size: 14px;
    color: #2c3e50;
}

/* Main Window & Dialogs */
QMainWindow, QDialog {
    background-color: #f0f2f5;
}

/* Buttons */
QPushButton {
    background-color: #3498db;
    color: white;
    border: none;
    border-radius: 6px;
    padding: 8px 16px;
    font-weight: bold;
}

QPushButton:hover {
    background-color: #2980b9;
}

QPushButton:pressed {
    background-color: #1c5980;
}

QPushButton:disabled {
    background-color: #bdc3c7;
    color: #ecf0f1;
}

/* Tab Widget & Tab Bar */
QTabWidget::pane {
    border: 1px solid #d1d8e0;
    background-color: white;
    border-radius: 6px;
    margin-top: -1px;
}

QTabBar::tab {
    background-color: #e4e8ec;
    color: #7f8c8d;
    padding: 10px 20px;
    margin-right: 4px;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    border: 1px solid #d1d8e0;
    border-bottom: none;
}

QTabBar::tab:selected {
    background-color: white;
    color: #2980b9;
    font-weight: bold;
    border-bottom: 2px solid #3498db;
}

QTabBar::tab:hover:!selected {
    background-color: #f1f3f5;
    color: #34495e;
}

/* Tables */
QTableWidget {
    background-color: white;
    alternate-background-color: #f8f9fa;
    border: 1px solid #d1d8e0;
    border-radius: 4px;
    gridline-color: #ecf0f1;
    selection-background-color: #e8f4f8;
    selection-color: #2980b9;
}

QHeaderView::section {
    background-color: #ecf0f1;
    color: #2c3e50;
    padding: 8px;
    border: none;
    border-right: 1px solid #d1d8e0;
    border-bottom: 2px solid #bdc3c7;
    font-weight: bold;
}

/* Inputs and Comboboxes */
QLineEdit, QComboBox, QDateEdit, QSpinBox, QTextEdit {
    border: 1px solid #cbd4c2;
    border-radius: 5px;
    padding: 8px;
    background-color: white;
    selection-background-color: #3498db;
}

QLineEdit:focus, QComboBox:focus, QDateEdit:focus, QSpinBox:focus, QTextEdit:focus {
    border: 2px solid #3498db;
    padding: 7px; /* Compensate for thicker border */
}

QComboBox::drop-down {
    border-left: 1px solid #cbd4c2;
    width: 24px;
    background: transparent;
}

/* Scrollbars */
QScrollBar:vertical {
    border: none;
    background: #f1f2f6;
    width: 10px;
    margin: 0px 0px 0px 0px;
}
QScrollBar::handle:vertical {
    background: #a4b0be;
    min-height: 20px;
    border-radius: 5px;
}
QScrollBar::handle:vertical:hover {
    background: #747d8c;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}

QScrollBar:horizontal {
    border: none;
    background: #f1f2f6;
    height: 10px;
    margin: 0px 0px 0px 0px;
}
QScrollBar::handle:horizontal {
    background: #a4b0be;
    min-width: 20px;
    border-radius: 5px;
}
QScrollBar::handle:horizontal:hover {
    background: #747d8c;
}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    width: 0px;
}

/* Menus */
QMenuBar {
    background-color: #f5f6fa;
    border-bottom: 1px solid #dcdde1;
}
QMenuBar::item {
    spacing: 3px;
    padding: 4px 8px;
    background: transparent;
    border-radius: 4px;
}
QMenuBar::item:selected {
    background: #e8e8e8;
}
QMenu {
    background-color: white;
    border: 1px solid #dcdde1;
}
QMenu::item {
    padding: 6px 24px 6px 24px;
}
QMenu::item:selected {
    background-color: #4a90e2;
    color: white;
}

/* Status Bar */
QStatusBar {
    background-color: #f1f2f6;
    border-top: 1px solid #dcdde1;
}
"""

def main():
    app = QApplication(sys.argv)
    app.setStyleSheet(MODERN_STYLE)
    
    # Initialize DB and run migrations
    data_dir = Path("data")
    data_dir.mkdir(exist_ok=True)
    db_path = data_dir / "family_tree.db"
    
    db = Database(db_path)
    schema_dir = Path(__file__).parent / "schema"
    db.run_migrations(schema_dir)
    
    window = MainWindow(db)
    window.show()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
