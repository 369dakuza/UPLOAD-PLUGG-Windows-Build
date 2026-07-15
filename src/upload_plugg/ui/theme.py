STYLESHEET = r"""
* { font-family: "Segoe UI", "Inter", sans-serif; font-size: 10pt; }
QMainWindow, QWidget#root { background: #090a0c; color: #f2f3f5; }
QWidget { color: #e9eaed; }
QFrame#sidebar { background: #0d0f12; border-right: 1px solid #24262c; }
QFrame#topbar { background: #0d0f12; border-bottom: 1px solid #24262c; }
QFrame#panel, QGroupBox { background: #121419; border: 1px solid #292c33; border-radius: 12px; }
QGroupBox { margin-top: 12px; padding: 16px 12px 12px; font-weight: 600; }
QGroupBox::title { subcontrol-origin: margin; left: 12px; padding: 0 6px; color: #f2f3f5; }
QPushButton { background: #20232a; border: 1px solid #323640; border-radius: 8px; padding: 8px 14px; min-height: 18px; }
QPushButton:hover { background: #2a2e36; border-color: #454a55; }
QPushButton:pressed { background: #181a1f; }
QPushButton[accent="true"] { background: #a50f22; border-color: #d21b34; color: white; font-weight: 700; }
QPushButton[accent="true"]:hover { background: #c5162c; }
QPushButton[danger="true"] { color: #ff7183; border-color: #682230; }
QPushButton#navButton { text-align: left; padding: 11px 14px; background: transparent; border: 0; color: #aeb2bb; }
QPushButton#navButton:hover { background: #191c22; color: white; }
QPushButton#navButton:checked { background: #321018; color: #ff5268; border-left: 3px solid #d51932; }
QLineEdit, QTextEdit, QPlainTextEdit, QSpinBox, QDoubleSpinBox, QComboBox, QDateEdit, QTimeEdit { background: #0c0e11; border: 1px solid #343740; border-radius: 7px; padding: 7px; selection-background-color: #a50f22; }
QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus, QComboBox:focus { border-color: #c31930; }
QTableWidget { background: #0c0e11; alternate-background-color: #11141a; border: 1px solid #292c33; border-radius: 8px; gridline-color: #20232a; }
QHeaderView::section { background: #191c22; color: #aeb2bb; border: 0; border-right: 1px solid #292c33; padding: 8px; }
QTableWidget::item:selected { background: #541321; }
QScrollBar:vertical { background: #0d0f12; width: 10px; }
QScrollBar::handle:vertical { background: #363943; border-radius: 5px; min-height: 30px; }
QProgressBar { background: #0c0e11; border: 1px solid #2d3037; border-radius: 6px; text-align: center; }
QProgressBar::chunk { background: #c5162c; border-radius: 5px; }
QCheckBox::indicator { width: 18px; height: 18px; border: 1px solid #454954; border-radius: 5px; background: #0c0e11; }
QCheckBox::indicator:checked { background: #c5162c; border-color: #e52841; }
QLabel#appName { font-size: 18pt; font-weight: 800; letter-spacing: 1px; color: white; }
QLabel#pageTitle { font-size: 21pt; font-weight: 750; color: white; }
QLabel#muted { color: #858a95; }
QLabel#credit { color: #6f747e; font-size: 9pt; padding: 10px 4px; }
QLabel#statusGood { color: #59c98b; }
QLabel#statusWarn { color: #f0b84b; }
QLabel#dryRun { color: #ffca5a; background: #30250d; border: 1px solid #6b5115; border-radius: 8px; padding: 8px; font-weight: 700; }
QToolTip { background: #20232a; color: white; border: 1px solid #444954; }
"""

