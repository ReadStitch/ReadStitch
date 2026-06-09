DARK_STYLE_SHEET = """
/* Premium Modern Dark Theme */

QWidget {
    background-color: #121212;
    color: #e0e0e0;
    font-family: "Segoe UI", "Roboto", "Helvetica Neue", sans-serif;
    font-size: 10pt;
}

/* Group Boxes (Panels) */
QGroupBox {
    background-color: #1a1a1a;
    border: 1px solid #2a2a2a;
    border-radius: 8px;
    margin-top: 24px;
    padding-top: 12px;
}
QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 0 8px;
    color: #26ee9f;
    font-weight: bold;
    font-size: 11pt;
    margin-left: 8px;
}

/* Buttons */
QPushButton {
    background-color: #26ee9f;
    color: #121212;
    font-weight: bold;
    border-radius: 6px;
    padding: 8px 16px;
    border: none;
}
QPushButton:hover {
    background-color: #43e689;
}
QPushButton:pressed {
    background-color: #1fca86;
}
QPushButton:checked {
    background-color: #1a1a1a;
    color: #26ee9f;
    border: 2px solid #26ee9f;
    font-weight: 900;
}
QPushButton:disabled {
    background-color: #2a2a2a;
    color: #666666;
}

/* Inputs & Combos */
QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox {
    background-color: #242424;
    border: 1px solid #333333;
    border-radius: 6px;
    padding: 6px 10px;
    color: #ffffff;
    selection-background-color: #26ee9f;
    selection-color: #121212;
}
QLineEdit:focus, QSpinBox:focus, QComboBox:focus {
    border: 1px solid #26ee9f;
}
QComboBox::drop-down {
    border: none;
    padding-right: 8px;
}
QComboBox QAbstractItemView {
    background-color: #242424;
    border: 1px solid #333333;
    border-radius: 6px;
    selection-background-color: #26ee9f;
    selection-color: #121212;
}

/* Tabs */
QTabWidget::pane {
    border: 1px solid #2a2a2a;
    border-radius: 8px;
    background-color: #1a1a1a;
    top: -1px;
}
QTabBar::tab {
    background-color: transparent;
    color: #888888;
    padding: 10px 20px;
    font-weight: bold;
    border-bottom: 2px solid transparent;
}
QTabBar::tab:hover {
    color: #e0e0e0;
}
QTabBar::tab:selected {
    color: #26ee9f;
    border-bottom: 2px solid #26ee9f;
}

/* List Widget */
QListWidget {
    background-color: #1a1a1a;
    border: 1px solid #2a2a2a;
    border-radius: 8px;
    padding: 4px;
}
QListWidget::item {
    padding: 6px;
    border-radius: 4px;
}
QListWidget::item:hover {
    background-color: #242424;
}
QListWidget::item:selected {
    background-color: rgba(38, 238, 159, 0.2);
    color: #26ee9f;
    border-left: 3px solid #26ee9f;
    font-weight: bold;
}

/* Progress Bar */
QProgressBar {
    background-color: #242424;
    border: 1px solid #333333;
    border-radius: 6px;
    text-align: center;
    color: #ffffff;
    font-weight: bold;
}
QProgressBar::chunk {
    background-color: #26ee9f;
    border-radius: 4px;
}

/* Checkboxes */
QCheckBox {
    spacing: 8px;
}
QCheckBox::indicator {
    width: 18px;
    height: 18px;
    border-radius: 4px;
    border: 1px solid #555555;
    background-color: #242424;
}
QCheckBox::indicator:hover {
    border: 1px solid #26ee9f;
}
QCheckBox::indicator:checked {
    background-color: #26ee9f;
    border: 1px solid #26ee9f;
    image: url(./assets/CheckboxHighlight.svg);
}

/* Text Edit (Console) */
QTextEdit {
    background-color: #0d0d0d;
    border: 1px solid #2a2a2a;
    border-radius: 8px;
    padding: 8px;
    color: #cccccc;
    font-family: "Consolas", "Courier New", monospace;
}
/* Scrollbars */
QScrollBar:vertical {
    border: none;
    background-color: #121212;
    width: 14px;
    margin: 0px 0px 0px 0px;
}
QScrollBar::handle:vertical {
    background-color: #333333;
    min-height: 20px;
    border-radius: 7px;
    margin: 2px;
}
QScrollBar::handle:vertical:hover {
    background-color: #444444;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    border: none;
    background: none;
}
QScrollBar:horizontal {
    border: none;
    background-color: #121212;
    height: 14px;
    margin: 0px 0px 0px 0px;
}
QScrollBar::handle:horizontal {
    background-color: #333333;
    min-width: 20px;
    border-radius: 7px;
    margin: 2px;
}
QScrollBar::handle:horizontal:hover {
    background-color: #444444;
}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    border: none;
    background: none;
}
"""

def load_styling():
    return DARK_STYLE_SHEET
