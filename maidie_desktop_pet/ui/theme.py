from __future__ import annotations

import ctypes
import sys
from pathlib import Path

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QColor, QFont, QPalette
from PyQt6.QtWidgets import QApplication, QWidget


_UI_ASSETS = (Path(__file__).resolve().parents[1] / "assets" / "ui").as_posix()


BASE_STYLE = """
QDialog {
  background: rgba(235, 242, 252, 244);
  color: #172033;
}
QDialog QWidget {
  color: #172033;
  font-family: "Segoe UI Variable Text", "Microsoft YaHei UI", "Segoe UI";
}
QLabel, QCheckBox, QRadioButton {
  background: transparent;
  color: #273147;
}
QLabel#panelTitle {
  color: #111827;
  font-size: 18px;
  font-weight: 650;
  padding: 6px 2px;
}
QLabel#sectionTitle {
  color: #111827;
  font-size: 16px;
  font-weight: 650;
}
QLabel#sectionSubtitle, QLabel#settingHint {
  color: #6a768c;
}
QLabel#settingHint {
  font-size: 12px;
}
QWidget#settingsCard {
  background: rgba(255, 255, 255, 112);
  border: 1px solid rgba(128, 151, 184, 80);
  border-radius: 15px;
}
QLineEdit, QTextEdit, QPlainTextEdit, QTextBrowser, QComboBox, QSpinBox {
  background: rgba(255, 255, 255, 178);
  color: #172033;
  border: 1px solid rgba(126, 148, 184, 112);
  border-radius: 11px;
  padding: 7px 9px;
  selection-background-color: #0a84ff;
  selection-color: white;
}
QLineEdit:hover, QTextEdit:hover, QPlainTextEdit:hover, QTextBrowser:hover,
QComboBox:hover, QSpinBox:hover {
  border-color: rgba(64, 139, 230, 150);
  background: rgba(255, 255, 255, 205);
}
QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus, QTextBrowser:focus,
QComboBox:focus, QSpinBox:focus {
  border: 1px solid #0a84ff;
  background: rgba(255, 255, 255, 225);
}
QLineEdit:disabled, QTextEdit:disabled, QComboBox:disabled, QSpinBox:disabled {
  background: rgba(215, 224, 237, 135);
  color: #7b8598;
  border-color: rgba(139, 153, 177, 75);
}
QComboBox {
  padding-right: 30px;
}
QComboBox::drop-down {
  width: 28px;
  border: none;
  background: transparent;
}
QComboBox::down-arrow {
  image: url(__UI_ASSETS__/chevron-down.svg);
  width: 12px;
  height: 8px;
}
QCheckBox {
  spacing: 8px;
}
QCheckBox::indicator {
  width: 17px;
  height: 17px;
  background: rgba(255, 255, 255, 190);
  border: 1px solid rgba(89, 116, 154, 145);
  border-radius: 5px;
}
QCheckBox::indicator:hover {
  border-color: #0a84ff;
  background: rgba(255, 255, 255, 225);
}
QCheckBox::indicator:checked {
  image: url(__UI_ASSETS__/check.svg);
  background: #0a84ff;
  border-color: #0879e6;
}
QCheckBox::indicator:disabled {
  background: rgba(194, 205, 220, 125);
  border-color: rgba(119, 137, 164, 65);
}
QTextBrowser#resultBrowser, QTextBrowser#recentChatsBrowser,
QTextBrowser#helpBrowser {
  background: rgba(255, 255, 255, 148);
  border-color: rgba(105, 137, 180, 90);
  padding: 12px;
}
QPlainTextEdit#openCodeInstallLog {
  background: rgba(235, 243, 253, 190);
  color: #25324a;
  border-color: rgba(91, 126, 173, 105);
  padding: 10px;
  font-family: "Cascadia Mono", "Consolas", "Microsoft YaHei UI";
  font-size: 12px;
}
QPushButton {
  min-height: 18px;
  background: rgba(255, 255, 255, 172);
  color: #1e2a3f;
  border: 1px solid rgba(111, 135, 172, 105);
  border-radius: 10px;
  padding: 7px 15px;
  font-weight: 560;
}
QPushButton:hover {
  background: rgba(255, 255, 255, 225);
  border-color: rgba(55, 132, 226, 170);
  color: #075fbd;
}
QPushButton:pressed {
  background: rgba(197, 220, 248, 205);
  border-color: #0a84ff;
}
QPushButton:default, QPushButton#primaryButton {
  background: #0a84ff;
  color: white;
  border-color: #0a76e6;
}
QPushButton:default:hover, QPushButton#primaryButton:hover {
  background: #2794ff;
  color: white;
}
QTabWidget::pane {
  background: rgba(255, 255, 255, 104);
  border: 1px solid rgba(131, 151, 181, 85);
  border-radius: 14px;
  top: -1px;
}
QTabBar::tab {
  background: rgba(218, 228, 243, 150);
  color: #536079;
  border: 1px solid transparent;
  padding: 8px 14px;
  margin-right: 4px;
  border-radius: 9px;
}
QTabBar::tab:hover {
  background: rgba(255, 255, 255, 178);
  color: #1d4f8c;
}
QTabBar::tab:selected {
  background: rgba(255, 255, 255, 220);
  color: #075fbd;
  border-color: rgba(116, 150, 193, 95);
}
QGroupBox {
  background: rgba(255, 255, 255, 82);
  border: 1px solid rgba(132, 153, 184, 82);
  border-radius: 13px;
  margin-top: 11px;
  padding-top: 11px;
}
QGroupBox::title {
  subcontrol-origin: margin;
  left: 12px;
  padding: 0 5px;
  color: #33415c;
  font-weight: 600;
}
QMenu {
  background: rgba(238, 246, 255, 250);
  color: #273b52;
  border: 1px solid rgba(132, 172, 213, 125);
  border-radius: 14px;
  padding: 8px;
}
QMenu::item {
  background: transparent;
  border-radius: 9px;
  padding: 9px 32px 9px 14px;
}
QMenu::item:selected {
  background: rgba(117, 177, 238, 70);
  color: #225f9c;
}
QMenu::item:disabled {
  color: #567798;
  font-weight: 700;
}
QMenu::indicator {
  width: 16px;
  height: 16px;
}
QMenu::indicator:checked {
  image: url(__UI_ASSETS__/check.svg);
  background: #78afe6;
  border-radius: 5px;
}
QMenu::separator {
  height: 1px;
  background: rgba(108, 147, 187, 52);
  margin: 5px 9px;
}
QScrollBar:vertical {
  background: transparent;
  width: 10px;
  margin: 3px;
}
QScrollBar::handle:vertical {
  background: rgba(105, 127, 158, 105);
  border-radius: 4px;
  min-height: 24px;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical,
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
  background: transparent;
  height: 0;
}
QScrollBar:horizontal {
  background: transparent;
  height: 10px;
  margin: 3px;
}
QScrollArea, QScrollArea > QWidget > QWidget {
  background: transparent;
  border: none;
}
QScrollBar::handle:horizontal {
  background: rgba(105, 127, 158, 105);
  border-radius: 4px;
  min-width: 24px;
}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal,
QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {
  background: transparent;
  width: 0;
}
QToolTip {
  background: rgba(32, 40, 55, 242);
  color: white;
  border: 1px solid rgba(255, 255, 255, 55);
  border-radius: 7px;
  padding: 5px 8px;
}
"""

BASE_STYLE = BASE_STYLE.replace("__UI_ASSETS__", _UI_ASSETS)


CHAT_INPUT_STYLE = """
QLineEdit {
  background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
    stop:0 rgba(255, 255, 255, 238),
    stop:1 rgba(220, 235, 253, 225));
  color: #142039;
  border: 1px solid rgba(90, 138, 199, 155);
  border-radius: 16px;
  padding: 9px 14px;
  font-size: 14px;
  font-family: "Segoe UI Variable Text", "Microsoft YaHei UI", "Segoe UI";
  selection-background-color: #0a84ff;
}
QLineEdit:hover {
  border-color: rgba(10, 132, 255, 190);
}
QLineEdit:focus {
  background: rgba(255, 255, 255, 244);
  border: 1px solid #0a84ff;
}
"""


CONSOLE_STYLE = BASE_STYLE + """
QDialog {
  background: rgba(20, 27, 40, 246);
  color: #e5edf8;
}
QDialog QWidget, QDialog QLabel {
  color: #dce7f6;
}
QTextEdit, QPlainTextEdit {
  background: rgba(7, 12, 21, 205);
  color: #c9f7df;
  border: 1px solid rgba(111, 155, 190, 105);
  font-family: "Cascadia Mono", "Consolas";
}
QPlainTextEdit#codingAgentOutput {
  background: rgba(5, 10, 18, 218);
  color: #d9e7f7;
  border-color: rgba(116, 164, 211, 95);
  border-radius: 12px;
  padding: 11px;
  font-size: 12px;
}
QLabel#statusChip {
  background: rgba(10, 132, 255, 52);
  color: #cfe7ff;
  border: 1px solid rgba(93, 167, 244, 85);
  border-radius: 8px;
  padding: 4px 9px;
  font-weight: 600;
}
QPushButton {
  background: rgba(255, 255, 255, 28);
  color: #e8f1ff;
  border-color: rgba(164, 191, 224, 70);
}
QPushButton:hover {
  background: rgba(77, 148, 230, 70);
  color: white;
}
"""


def apply_application_theme(app: QApplication) -> None:
    """Apply the shared visual language without changing the pet canvas."""
    app.setStyle("Fusion")
    font = QFont("Segoe UI Variable Text", 10)
    if not font.exactMatch():
        font = QFont("Microsoft YaHei UI", 10)
    app.setFont(font)
    app.setStyleSheet(BASE_STYLE)


def apply_dialog_theme(
    widget: QWidget, *, dark: bool = False, backdrop: bool = True
) -> None:
    widget.setStyleSheet(CONSOLE_STYLE if dark else BASE_STYLE)
    if backdrop:
        QTimer.singleShot(0, lambda: _enable_windows_backdrop(widget, dark=dark))


def prepare_translucent_window(widget: QWidget) -> None:
    """Configure a custom-painted window for a real antialiased alpha surface."""

    widget.setWindowFlag(Qt.WindowType.NoDropShadowWindowHint, True)
    widget.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
    widget.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, True)
    widget.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent, False)
    widget.setAutoFillBackground(False)
    palette = widget.palette()
    palette.setColor(QPalette.ColorRole.Window, QColor(0, 0, 0, 0))
    widget.setPalette(palette)


def disable_windows_backdrop(widget: QWidget) -> None:
    """Keep custom alpha edges untouched by DWM backdrops and native borders."""

    if sys.platform != "win32" or not widget.isVisible():
        return
    try:
        hwnd = int(widget.winId())
        dwm = ctypes.windll.dwmapi
        backdrop = ctypes.c_int(1)  # DWMSBT_NONE.
        corner = ctypes.c_int(1)  # DWMWCP_DONOTROUND; Qt paints the smooth edge.
        border = ctypes.c_uint32(0xFFFFFFFE)  # DWMWA_COLOR_NONE.
        dwm.DwmSetWindowAttribute(
            hwnd, 38, ctypes.byref(backdrop), ctypes.sizeof(backdrop)
        )
        dwm.DwmSetWindowAttribute(
            hwnd, 33, ctypes.byref(corner), ctypes.sizeof(corner)
        )
        dwm.DwmSetWindowAttribute(
            hwnd, 34, ctypes.byref(border), ctypes.sizeof(border)
        )
    except (AttributeError, OSError, ValueError):
        return


def _enable_windows_backdrop(widget: QWidget, *, dark: bool = False) -> None:
    """Use the Windows 11 transient backdrop when available; fail softly elsewhere."""
    if sys.platform != "win32" or not widget.isVisible():
        return
    try:
        hwnd = int(widget.winId())
        dwm = ctypes.windll.dwmapi
        backdrop = ctypes.c_int(3)  # DWMSBT_TRANSIENTWINDOW, acrylic-like.
        corner = ctypes.c_int(2)  # DWMWCP_ROUND.
        dark_mode = ctypes.c_int(1 if dark else 0)
        border = ctypes.c_uint32(0xFFFFFFFE)  # Remove the dark native outline.
        dwm.DwmSetWindowAttribute(
            hwnd, 38, ctypes.byref(backdrop), ctypes.sizeof(backdrop)
        )
        dwm.DwmSetWindowAttribute(
            hwnd, 33, ctypes.byref(corner), ctypes.sizeof(corner)
        )
        dwm.DwmSetWindowAttribute(
            hwnd, 20, ctypes.byref(dark_mode), ctypes.sizeof(dark_mode)
        )
        dwm.DwmSetWindowAttribute(
            hwnd, 34, ctypes.byref(border), ctypes.sizeof(border)
        )
    except (AttributeError, OSError, ValueError):
        return
