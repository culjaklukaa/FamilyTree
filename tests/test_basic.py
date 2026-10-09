import pytest
from PySide6.QtWidgets import QWidget

def test_pyside6_qtbot(qtbot):
    """
    A simple sanity check to ensure pytest-qt and PySide6 are working together.
    The qtbot fixture is provided by pytest-qt.
    """
    widget = QWidget()
    qtbot.addWidget(widget)
    
    widget.setWindowTitle("Family Tree Test")
    assert widget.windowTitle() == "Family Tree Test"
