from __future__ import annotations

from PyQt6.QtCore import QEasingCurve, QRectF, Qt, QTimer, QVariantAnimation
from PyQt6.QtGui import QColor, QPainter
from PyQt6.QtWidgets import QMenu

from ui.theme import disable_windows_backdrop, prepare_translucent_window


class PetContextMenu(QMenu):
    """Warm context menu with a small animated hover marker."""

    def __init__(self, title: str = "", parent=None) -> None:
        super().__init__(title, parent)
        self.setWindowFlags(
            self.windowFlags()
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.NoDropShadowWindowHint
        )
        self.setObjectName("maidieContextMenu")
        prepare_translucent_window(self)
        self.setStyleSheet(
            "QMenu#maidieContextMenu { background: transparent; border: none; }"
        )
        self.setMinimumWidth(238)
        self._hover_rect = QRectF()
        self._hover_animation = QVariantAnimation(self)
        self._hover_animation.setDuration(115)
        self._hover_animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._hover_animation.valueChanged.connect(self._set_hover_rect)
        self.hovered.connect(self._animate_hover)

    def _animate_hover(self, action) -> None:
        target = QRectF(self.actionGeometry(action))
        start = self._hover_rect if not self._hover_rect.isNull() else target
        self._hover_animation.stop()
        self._hover_animation.setStartValue(start)
        self._hover_animation.setEndValue(target)
        self._hover_animation.start()

    def _set_hover_rect(self, rect) -> None:
        self._hover_rect = QRectF(rect)
        self.update()

    def paintEvent(self, event) -> None:
        background = QPainter(self)
        background.setCompositionMode(
            QPainter.CompositionMode.CompositionMode_Source
        )
        background.fillRect(self.rect(), QColor(0, 0, 0, 0))
        background.setCompositionMode(
            QPainter.CompositionMode.CompositionMode_SourceOver
        )
        background.setRenderHint(QPainter.RenderHint.Antialiasing)
        background.setPen(QColor(153, 187, 222, 155))
        background.setBrush(QColor(238, 246, 255, 252))
        background.drawRoundedRect(
            QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5), 14, 14
        )
        background.end()
        super().paintEvent(event)
        if self._hover_rect.isNull():
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(QColor(104, 163, 224, 220))
        painter.setBrush(QColor(104, 163, 224, 220))
        marker = QRectF(
            self._hover_rect.left() + 3,
            self._hover_rect.top() + 7,
            3,
            max(8, self._hover_rect.height() - 14),
        )
        painter.drawRoundedRect(marker, 1.5, 1.5)

    def showEvent(self, event) -> None:
        super().showEvent(event)
        QTimer.singleShot(0, lambda: disable_windows_backdrop(self))
