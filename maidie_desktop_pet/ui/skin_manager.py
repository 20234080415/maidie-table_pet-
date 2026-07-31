from __future__ import annotations

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QDialog, QLabel, QPushButton, QVBoxLayout

from ui.theme import apply_dialog_theme


class SkinManager(QDialog):
    """Small skin gateway that reuses the established animation settings."""

    open_animation_settings_requested = pyqtSignal()

    def __init__(self, controller, parent=None) -> None:
        super().__init__(parent)
        self.controller = controller
        self.setWindowTitle("更换皮肤")
        self.resize(430, 280)
        apply_dialog_theme(self)
        self.title = QLabel("🎨 Maidie 的衣橱")
        self.title.setObjectName("panelTitle")
        self.current = QLabel()
        self.current.setWordWrap(True)
        note = QLabel(
            "当前版本沿用已有 Sprite / Live2D 模型管理，不复制一套皮肤系统。"
            "后续皮肤预览和收藏会继续放在这个独立入口。"
        )
        note.setObjectName("sectionSubtitle")
        note.setWordWrap(True)
        open_settings = QPushButton("打开动画与模型设置")
        open_settings.clicked.connect(self.open_animation_settings_requested.emit)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(14)
        layout.addWidget(self.title)
        layout.addWidget(self.current)
        layout.addWidget(note)
        layout.addStretch()
        layout.addWidget(open_settings)
        self.refresh()

    def refresh(self) -> None:
        settings = self.controller.settings_snapshot()
        backend = str(settings.get("animation_backend", "sprite"))
        model_id = str(settings.get("animation_current_model_id", "")).strip()
        backend_name = "Live2D" if backend == "live2d_web" else "Sprite"
        suffix = f" · {model_id}" if model_id else ""
        self.current.setText(f"现在穿着：{backend_name}{suffix}")

    def showEvent(self, event) -> None:
        self.refresh()
        super().showEvent(event)
