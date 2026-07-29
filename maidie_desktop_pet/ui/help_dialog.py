from __future__ import annotations

from PyQt6.QtWidgets import QDialog, QVBoxLayout

from ui.theme import apply_dialog_theme
from ui.settings.help_page import HelpPage


class HelpDialog(QDialog):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("帮助与说明")
        self.resize(640, 560)
        apply_dialog_theme(self)
        layout = QVBoxLayout(self)
        layout.addWidget(HelpPage(self))
