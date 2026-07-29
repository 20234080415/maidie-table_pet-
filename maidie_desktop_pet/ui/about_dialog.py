from __future__ import annotations

from PyQt6.QtWidgets import QDialog, QVBoxLayout

from ui.theme import apply_dialog_theme
from ui.settings.about_page import AboutPage


class AboutDialog(QDialog):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("关于 Maidie")
        self.resize(520, 470)
        apply_dialog_theme(self)
        layout = QVBoxLayout(self)
        layout.addWidget(AboutPage(self))
