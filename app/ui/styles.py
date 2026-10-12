"""
Modern mechanical keyboard design system and stylesheets for PySide6.
"""

DARK_THEME_QSS = """
QMainWindow, QWidget {
    background-color: #121316;
    color: #e2e8f0;
    font-family: "Helvetica Neue", "Arial", "Lucida Grande";
    font-size: 13px;
}

/* Tab Bar */
QTabBar::tab {
    background: #18191e;
    color: #94a3b8;
    padding: 10px 18px;
    margin-right: 4px;
    border-top-left-radius: 8px;
    border-top-right-radius: 8px;
    font-weight: 600;
    border: 1px solid #22252c;
    border-bottom: none;
}

QTabBar::tab:selected {
    background: #22252c;
    color: #6366f1;
    border-top: 2px solid #6366f1;
}

QTabBar::tab:hover:!selected {
    background: #1e2027;
    color: #cbd5e1;
}

QTabWidget::pane {
    border: 1px solid #22252c;
    border-radius: 8px;
    background: #18191e;
    top: -1px;
}

/* Panels and Cards */
QGroupBox {
    background-color: #1a1b22;
    border: 1px solid #282c37;
    border-radius: 10px;
    margin-top: 14px;
    padding-top: 18px;
    font-weight: 700;
    color: #f1f5f9;
}

QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 0 10px;
    color: #818cf8;
}

/* Buttons */
QPushButton {
    background-color: #272a34;
    color: #f8fafc;
    border: 1px solid #373b49;
    border-radius: 7px;
    padding: 8px 16px;
    font-weight: 600;
}

QPushButton:hover {
    background-color: #323643;
    border-color: #4f46e5;
}

QPushButton:pressed {
    background-color: #4338ca;
    color: #ffffff;
}

QPushButton:disabled {
    background-color: #1b1c22;
    color: #475569;
    border-color: #242730;
}

QPushButton#PrimaryButton {
    background-color: #4f46e5;
    border: 1px solid #6366f1;
    color: #ffffff;
}

QPushButton#PrimaryButton:hover {
    background-color: #4338ca;
    border-color: #818cf8;
}

QPushButton#AccentButton {
    background-color: #0d9488;
    border: 1px solid #14b8a6;
    color: #ffffff;
}

QPushButton#AccentButton:hover {
    background-color: #0f766e;
}

/* Sliders */
QSlider::groove:horizontal {
    height: 6px;
    background: #272a34;
    border-radius: 3px;
}

QSlider::sub-page:horizontal {
    background: #6366f1;
    border-radius: 3px;
}

QSlider::handle:horizontal {
    background: #ffffff;
    border: 2px solid #6366f1;
    width: 16px;
    height: 16px;
    margin-top: -5px;
    margin-bottom: -5px;
    border-radius: 8px;
}

QSlider::handle:horizontal:hover {
    background: #818cf8;
}

/* Combo Box */
QComboBox {
    background-color: #22252e;
    color: #f1f5f9;
    border: 1px solid #323643;
    border-radius: 6px;
    padding: 6px 12px;
}

QComboBox:hover {
    border-color: #6366f1;
}

QComboBox::drop-down {
    border: none;
    width: 24px;
}

QComboBox QAbstractItemView {
    background-color: #1e2027;
    color: #f1f5f9;
    border: 1px solid #323643;
    selection-background-color: #4338ca;
    selection-color: #ffffff;
}

/* Checkboxes */
QCheckBox {
    spacing: 8px;
    color: #e2e8f0;
    font-weight: 500;
}

QCheckBox::indicator {
    width: 18px;
    height: 18px;
    border: 1px solid #3a3f50;
    border-radius: 4px;
    background: #1f222b;
}

QCheckBox::indicator:checked {
    background: #4f46e5;
    border-color: #6366f1;
}

/* Labels and Scrollbars */
QLabel {
    color: #e2e8f0;
}

QLabel#HeaderLabel {
    font-size: 18px;
    font-weight: 700;
    color: #f8fafc;
}

QLabel#SubheaderLabel {
    font-size: 13px;
    color: #94a3b8;
}

QLabel#BadgeLabel {
    background: #272a36;
    color: #818cf8;
    padding: 3px 8px;
    border-radius: 10px;
    font-size: 11px;
    font-weight: 700;
}

QScrollBar:vertical {
    background: #14151a;
    width: 10px;
    margin: 0;
    border-radius: 5px;
}

QScrollBar::handle:vertical {
    background: #282c38;
    min-height: 24px;
    border-radius: 5px;
}

QScrollBar::handle:vertical:hover {
    background: #3e4456;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}
"""

LIGHT_THEME_QSS = """
QMainWindow, QWidget {
    background-color: #f8fafc;
    color: #1e293b;
    font-family: "Helvetica Neue", "Arial", "Lucida Grande";
    font-size: 13px;
}

QTabBar::tab {
    background: #f1f5f9;
    color: #64748b;
    padding: 10px 18px;
    margin-right: 4px;
    border-top-left-radius: 8px;
    border-top-right-radius: 8px;
    font-weight: 600;
    border: 1px solid #e2e8f0;
    border-bottom: none;
}

QTabBar::tab:selected {
    background: #ffffff;
    color: #4f46e5;
    border-top: 2px solid #4f46e5;
}

QTabWidget::pane {
    border: 1px solid #e2e8f0;
    border-radius: 8px;
    background: #ffffff;
}

QGroupBox {
    background-color: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 10px;
    margin-top: 14px;
    padding-top: 18px;
    font-weight: 700;
    color: #0f172a;
}

QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 0 10px;
    color: #4f46e5;
}

QPushButton {
    background-color: #ffffff;
    color: #1e293b;
    border: 1px solid #cbd5e1;
    border-radius: 7px;
    padding: 8px 16px;
    font-weight: 600;
}

QPushButton:hover {
    background-color: #f1f5f9;
    border-color: #4f46e5;
}

QPushButton#PrimaryButton {
    background-color: #4f46e5;
    border: 1px solid #4338ca;
    color: #ffffff;
}

QSlider::groove:horizontal {
    height: 6px;
    background: #e2e8f0;
    border-radius: 3px;
}

QSlider::sub-page:horizontal {
    background: #4f46e5;
    border-radius: 3px;
}

QSlider::handle:horizontal {
    background: #ffffff;
    border: 2px solid #4f46e5;
    width: 16px;
    height: 16px;
    margin-top: -5px;
    margin-bottom: -5px;
    border-radius: 8px;
}
"""
