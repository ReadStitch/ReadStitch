DARK_STYLE_SHEET = """
/* Premium Modern Dark Theme - Orange Edition */

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
    border-radius: 10px;
    margin-top: 24px;
    padding-top: 16px;
}
QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 0 10px;
    color: #fb5c00;
    font-weight: bold;
    font-size: 11pt;
    margin-left: 10px;
}

/* Buttons */
QPushButton {
    background-color: #fb5c00;
    color: #ffffff;
    font-weight: bold;
    border-radius: 6px;
    padding: 10px 18px;
    border: none;
}
QPushButton:hover {
    background-color: #ff7b24;
}
QPushButton:pressed {
    background-color: #e05200;
}
QPushButton:checked {
    background-color: #1a1a1a;
    color: #fb5c00;
    border: 2px solid #fb5c00;
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
    padding: 8px 12px;
    color: #ffffff;
    selection-background-color: #fb5c00;
    selection-color: #ffffff;
}
QLineEdit:focus, QSpinBox:focus, QComboBox:focus {
    border: 1px solid #fb5c00;
    background-color: #2a2a2a;
}
QComboBox::drop-down {
    border: none;
    padding-right: 8px;
}
QComboBox QAbstractItemView {
    background-color: #242424;
    border: 1px solid #333333;
    border-radius: 6px;
    selection-background-color: #fb5c00;
    selection-color: #ffffff;
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
    padding: 12px 24px;
    font-weight: bold;
    border-bottom: 2px solid transparent;
}
QTabBar::tab:hover {
    color: #e0e0e0;
}
QTabBar::tab:selected {
    color: #fb5c00;
    border-bottom: 2px solid #fb5c00;
}

/* List Widget */
QListWidget {
    background-color: #1a1a1a;
    border: 1px solid #2a2a2a;
    border-radius: 8px;
    padding: 6px;
    outline: none;
}
QListWidget::item {
    padding: 8px;
    border-radius: 6px;
    margin-bottom: 2px;
}
QListWidget::item:hover {
    background-color: #242424;
}
QListWidget::item:selected {
    background-color: rgba(251, 92, 0, 0.15);
    color: #fb5c00;
    border-left: 3px solid #fb5c00;
    font-weight: bold;
}

/* Progress Bar */
QProgressBar {
    background-color: #242424;
    border: 1px solid #333333;
    border-radius: 8px;
    text-align: center;
    color: #ffffff;
    font-weight: bold;
    height: 18px;
}
QProgressBar::chunk {
    background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #fb5c00, stop:1 #ff8a40);
    border-radius: 6px;
}

/* Checkboxes */
QCheckBox {
    spacing: 10px;
}
QCheckBox::indicator {
    width: 20px;
    height: 20px;
    border-radius: 5px;
    border: 1px solid #555555;
    background-color: #242424;
}
QCheckBox::indicator:hover {
    border: 1px solid #fb5c00;
}
QCheckBox::indicator:checked {
    background-color: #fb5c00;
    border: 1px solid #fb5c00;
    image: url(./assets/CheckboxHighlight.svg);
}

/* Text Edit (Console) */
QTextEdit {
    background-color: #0d0d0d;
    border: 1px solid #2a2a2a;
    border-radius: 8px;
    padding: 12px;
    color: #cccccc;
    font-family: "Consolas", "Courier New", monospace;
    line-height: 1.5;
}

/* Scrollbars */
QScrollBar:vertical {
    border: none;
    background-color: #121212;
    width: 12px;
    margin: 0px;
}
QScrollBar::handle:vertical {
    background-color: #333333;
    min-height: 30px;
    border-radius: 6px;
    margin: 2px;
}
QScrollBar::handle:vertical:hover {
    background-color: #fb5c00;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    border: none;
    background: none;
}
QScrollBar:horizontal {
    border: none;
    background-color: #121212;
    height: 12px;
    margin: 0px;
}
QScrollBar::handle:horizontal {
    background-color: #333333;
    min-width: 30px;
    border-radius: 6px;
    margin: 2px;
}
QScrollBar::handle:horizontal:hover {
    background-color: #fb5c00;
}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    border: none;
    background: none;
}
"""

def load_styling():
    return DARK_STYLE_SHEET
