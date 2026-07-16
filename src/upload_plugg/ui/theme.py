from __future__ import annotations


STYLESHEET = r"""
* {
    font-family: "Segoe UI Variable", "Segoe UI", sans-serif;
    font-size: 10pt;
    color: #F4F6F8;
}
QMainWindow, QWidget#root { background: #07090C; }
QWidget { background: transparent; color: #F4F6F8; }
QFrame#sidebar { background: #0A0D11; border-right: 1px solid #1C222B; }
QFrame#navIndicator { background: #FF2347; border: 0; border-radius: 1px; }
QFrame#topbar { background: #0B0E12; border-bottom: 1px solid #1C222B; }
QFrame#contentSurface { background: #07090C; }

QFrame#panel, QFrame#sectionCard, QFrame#statCard, QGroupBox {
    background: #10141A;
    border: 1px solid #262D37;
    border-radius: 12px;
}
QFrame#sectionCard:hover, QFrame#statCard:hover { background: #141922; border-color: #323B48; }
QGroupBox { margin-top: 13px; padding: 17px 13px 13px; font-weight: 600; }
QGroupBox::title {
    subcontrol-origin: margin; left: 13px; padding: 0 7px;
    color: #F4F6F8; background: #10141A;
}

QLabel#appName { font-size: 19pt; font-weight: 800; letter-spacing: 1px; color: #F4F6F8; }
QLabel#brandUpload { font-size: 18pt; font-style: italic; font-weight: 800; letter-spacing: 1px; color: #F4F6F8; }
QLabel#brandPlugg { font-size: 18pt; font-style: italic; font-weight: 900; letter-spacing: 1px; color: #E31837; }
QLabel#brandTag { color: #707C8B; font-size: 8pt; letter-spacing: 1px; }
QLabel#pageTitle { font-size: 22pt; font-weight: 750; color: #F4F6F8; }
QLabel#sectionTitle { font-size: 11pt; font-weight: 700; color: #F4F6F8; }
QLabel#muted, QLabel#statLabel { color: #A3ADBA; }
QLabel#caption { color: #707C8B; font-size: 9pt; }
QLabel#credit { color: #707C8B; font-size: 9pt; padding: 10px 4px; }
QLabel#statValue { font-size: 27pt; font-weight: 800; }
QLabel#emptyTitle { color: #A3ADBA; font-size: 11pt; font-weight: 650; }
QLabel#statusGood { color: #32D583; }
QLabel#statusWarn { color: #FFB020; }
QLabel#statusError { color: #FF3B5C; }
QLabel#progressLabel, QLabel#progressPercent { color: #F4F6F8; font-weight: 650; }

QPushButton {
    background: #191E26; border: 1px solid #323B48; border-radius: 8px;
    padding: 8px 14px; min-height: 18px; color: #F4F6F8;
}
QPushButton:hover { background: #202630; border-color: #4A5666; }
QPushButton:pressed { background: #11151B; border-color: #262D37; }
QPushButton:focus { border: 1px solid #E31837; }
QPushButton:disabled { background: #10141A; color: #566170; border-color: #1C222B; }
QPushButton[role="primary"], QPushButton[accent="true"] {
    background: #E31837; border-color: #FF2347; color: white; font-weight: 700;
}
QPushButton[role="primary"]:hover, QPushButton[accent="true"]:hover { background: #FF2347; }
QPushButton[role="primary"]:pressed, QPushButton[accent="true"]:pressed { background: #B90F2C; }
QPushButton[role="secondary"] { background: #191E26; }
QPushButton[role="ghost"] { background: transparent; border-color: #262D37; }
QPushButton[role="success"] { color: #32D583; border-color: #236847; background: #10251C; }
QPushButton[role="warning"] { color: #FFB020; border-color: #6C4D18; background: #241B0D; }
QPushButton[role="danger"], QPushButton[danger="true"] { color: #FF6B80; border-color: #7A2433; background: #251018; }
QPushButton[role="danger"]:hover, QPushButton[danger="true"]:hover { background: #3B111E; border-color: #FF3B5C; }
QPushButton#navButton {
    text-align: left; padding: 11px 14px; background: transparent; border: 0;
    border-left: 3px solid transparent; color: #A3ADBA; border-radius: 8px;
}
QPushButton#navButton:hover { background: #141922; color: #F4F6F8; }
QPushButton#navButton:checked {
    background: #291018; color: #FF5268; border-left: 3px solid #E31837;
}

QLineEdit, QTextEdit, QPlainTextEdit, QSpinBox, QDoubleSpinBox,
QComboBox, QDateEdit, QTimeEdit {
    background: #0C1015; border: 1px solid #262D37; border-radius: 8px;
    padding: 7px 9px; selection-background-color: #7A1425; selection-color: #FFFFFF;
}
QLineEdit:hover, QTextEdit:hover, QPlainTextEdit:hover, QSpinBox:hover,
QDoubleSpinBox:hover, QComboBox:hover, QDateEdit:hover, QTimeEdit:hover { border-color: #3A4554; }
QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus, QSpinBox:focus,
QDoubleSpinBox:focus, QComboBox:focus, QDateEdit:focus, QTimeEdit:focus { border-color: #E31837; }
QLineEdit:disabled, QTextEdit:disabled, QPlainTextEdit:disabled, QSpinBox:disabled,
QDoubleSpinBox:disabled, QComboBox:disabled { background: #0A0D11; color: #566170; border-color: #1C222B; }
QPlainTextEdit#terminalLog { font-family: "Cascadia Mono", "Consolas", monospace; font-size: 9.5pt; padding: 12px; }
QComboBox { color: #F4F6F8; }
QComboBox::drop-down { border: 0; width: 30px; background: #141922; border-top-right-radius: 8px; border-bottom-right-radius: 8px; }
QComboBox QAbstractItemView {
    background-color: #080a0d;
    color: #ffffff;
    border: 1px solid #343740;
    selection-background-color: #291018;
    selection-color: #ffffff;
    outline: 0;
    padding: 5px;
}
QComboBox QAbstractItemView::item { min-height: 30px; padding: 5px 10px; color: #ffffff; }
QComboBox QAbstractItemView::item:hover { background: #191E26; color: #ffffff; }

QTableWidget {
    background: #0C1015; alternate-background-color: #10141A;
    border: 1px solid #262D37; border-radius: 10px; gridline-color: #1C222B;
    selection-background-color: #43121E; selection-color: #FFFFFF;
}
QTableWidget::item { padding: 6px; border-bottom: 1px solid #161B22; }
QTableWidget::item:hover { background: #191E26; }
QTableWidget::item:selected { background: #43121E; border-left: 2px solid #E31837; }
QHeaderView::section {
    background: #141922; color: #A3ADBA; border: 0; border-right: 1px solid #262D37;
    border-bottom: 1px solid #262D37; padding: 9px 7px; font-weight: 650;
}

QProgressBar {
    background: #0C1015; border: 1px solid #262D37; border-radius: 6px;
    text-align: center; color: #F4F6F8;
}
QProgressBar::chunk { background: #E31837; border-radius: 5px; }
QFrame#progressStrip { background: #100D12; border-bottom: 1px solid #7A1425; }
QFrame#progressStrip[state="success"] { border-bottom-color: #32D583; }
QFrame#progressStrip[state="error"] { border-bottom-color: #FF3B5C; }
QFrame#progressStrip[state="success"] QProgressBar::chunk { background: #32D583; }
QFrame#progressStrip[state="error"] QProgressBar::chunk { background: #FF3B5C; }

QSlider::groove:horizontal { height: 5px; background: #262D37; border-radius: 2px; }
QSlider::sub-page:horizontal { background: #E31837; border-radius: 2px; }
QSlider::handle:horizontal {
    width: 15px; margin: -5px 0; background: #FF2347; border: 2px solid #F4F6F8; border-radius: 7px;
}
QSlider::handle:horizontal:hover { background: #FFFFFF; border-color: #FF2347; }

QCheckBox { spacing: 8px; color: #F4F6F8; }
QCheckBox::indicator { width: 18px; height: 18px; border: 1px solid #465161; border-radius: 5px; background: #0C1015; }
QCheckBox::indicator:hover { border-color: #E31837; }
QCheckBox::indicator:checked { background: #E31837; border-color: #FF2347; }
QCheckBox[chip="true"] { padding: 7px 10px; background: #0C1015; border: 1px solid #262D37; border-radius: 8px; }
QCheckBox[chip="true"]:checked { background: #7A1425; border-color: #E31837; color: #FFFFFF; }
QCheckBox[chip="true"]::indicator { width: 0; height: 0; border: 0; }

QLabel[status] { padding: 3px 8px; border-radius: 8px; font-size: 9pt; font-weight: 650; }
QLabel[status="ready"], QLabel[status="complete"], QLabel[status="completed"] { color: #32D583; background: #10251C; border: 1px solid #236847; }
QLabel[status="waiting"], QLabel[status="warning"] { color: #FFB020; background: #241B0D; border: 1px solid #6C4D18; }
QLabel[status="scheduled"], QLabel[status="info"] { color: #72B7FF; background: #0E1D2D; border: 1px solid #245A8B; }
QLabel[status="uploading"], QLabel[status="validating"] { color: #FF6B80; background: #2C0E17; border: 1px solid #7A2433; }
QLabel[status="error"], QLabel[status="failed"] { color: #FF6B80; background: #2C0E17; border: 1px solid #8B2437; }
QLabel[status="neutral"], QLabel[status="not_checked"] { color: #A3ADBA; background: #141922; border: 1px solid #323B48; }

QScrollBar:vertical { background: #0A0D11; width: 11px; margin: 1px; }
QScrollBar::handle:vertical { background: #36404D; border-radius: 5px; min-height: 30px; }
QScrollBar::handle:vertical:hover { background: #536071; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QScrollBar:horizontal { background: #0A0D11; height: 11px; margin: 1px; }
QScrollBar::handle:horizontal { background: #36404D; border-radius: 5px; min-width: 30px; }
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0; }
QSplitter::handle { background: #1C222B; }
QSplitter::handle:hover { background: #E31837; }
QToolTip { background: #191E26; color: #FFFFFF; border: 1px solid #4A5666; padding: 5px; }
QMessageBox { background: #10141A; }
QMenu { background: #0C1015; border: 1px solid #262D37; padding: 5px; }
QMenu::item { padding: 7px 24px 7px 10px; border-radius: 5px; }
QMenu::item:selected { background: #291018; color: #FFFFFF; }
"""
