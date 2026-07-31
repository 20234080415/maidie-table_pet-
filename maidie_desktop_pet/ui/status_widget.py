from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

from PyQt6.QtCore import QPoint, QRect, Qt, QTimer
from PyQt6.QtGui import QColor, QPainter, QPixmap
from PyQt6.QtWidgets import (
    QDialog,
    QAbstractScrollArea,
    QFrame,
    QGraphicsDropShadowEffect,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from ui.theme import (
    apply_dialog_theme,
    disable_windows_backdrop,
    prepare_translucent_window,
)


STATUS_STYLE = """
QDialog#statusWidget {
  background: transparent;
  border: none;
}
QFrame#statusSurface {
  background: #edf6ff;
  border: none;
  border-radius: 28px;
}
QFrame#statusCard {
  background: rgba(255, 255, 255, 238);
  border: 1px solid rgba(151, 188, 226, 95);
  border-radius: 20px;
}
QLabel#petName {
  color: #365674;
  font-size: 24px;
  font-weight: 700;
}
QLabel#petLevel {
  color: #718da8;
  font-size: 14px;
  font-weight: 650;
}
QLabel#relationshipChip {
  background: #dcecff;
  color: #4d78a7;
  border: 1px solid #c3ddf7;
  border-radius: 10px;
  padding: 4px 10px;
  font-weight: 650;
}
QLabel#attributeLabel {
  color: #52677c;
  font-size: 14px;
  font-weight: 620;
}
QLabel#attributeValue {
  color: #6f89a2;
  font-size: 14px;
}
QProgressBar {
  min-height: 12px;
  max-height: 12px;
  background: #e5eef7;
  border: none;
  border-radius: 6px;
  text-align: center;
  color: transparent;
}
QProgressBar#affectionBar::chunk {
  background: #8ebcf0;
  border-radius: 6px;
}
QProgressBar#energyBar::chunk {
  background: #9dcfc1;
  border-radius: 6px;
}
QFrame#interactionItem {
  background: #f8fbff;
  border: 1px solid #cfe2f5;
  border-radius: 15px;
}
QLabel#interactionCount {
  color: #486987;
  font-size: 20px;
  font-weight: 700;
}
QLabel#interactionName {
  color: #7891a9;
  font-size: 12px;
}
QPushButton#statusCloseButton {
  background: #9ac5f2;
  color: #244c75;
  border: 1px solid #82b3e7;
  border-radius: 12px;
  padding: 8px 18px;
  font-weight: 650;
}
QPushButton#statusCloseButton:hover {
  background: #afd3f7;
  color: #244c75;
  border-color: #6ca7e3;
}
QPushButton#statusCloseButton:pressed {
  background: #82b4e8;
}
QPushButton#statusWindowClose {
  min-width: 28px;
  max-width: 28px;
  min-height: 28px;
  max-height: 28px;
  background: rgba(255, 255, 255, 155);
  color: #6f89a2;
  border: 1px solid rgba(130, 170, 211, 105);
  border-radius: 14px;
  padding: 0;
  font-size: 16px;
}
QPushButton#statusWindowClose:hover {
  background: #dcecff;
  color: #315f8c;
  border-color: #8dbbe8;
}
"""


def _soft_shadow(widget: QWidget, blur: int = 24) -> None:
    effect = QGraphicsDropShadowEffect(widget)
    effect.setBlurRadius(blur)
    effect.setOffset(0, 6)
    effect.setColor(QColor(74, 112, 151, 44))
    widget.setGraphicsEffect(effect)


class StatusWidget(QDialog):
    """Maidie's warm, notebook-like companionship status panel."""

    def __init__(
        self,
        controller,
        assets_dir: Path,
        parent=None,
        avatar_provider: Callable[[], QPixmap] | None = None,
    ) -> None:
        super().__init__(parent)
        self.controller = controller
        self.assets_dir = Path(assets_dir)
        self.avatar_provider = avatar_provider
        self._drag_offset: QPoint | None = None
        self.setObjectName("statusWidget")
        self.setWindowTitle("我的 Maidie")
        self.setWindowFlags(
            Qt.WindowType.Dialog
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.NoDropShadowWindowHint
        )
        prepare_translucent_window(self)
        self.setMinimumSize(340, 300)
        # DWM backdrop materials paint the transparent corners of a frameless
        # window black on some Windows builds.  The status surface already owns
        # its background and rounded shape, so it must stay fully transparent.
        apply_dialog_theme(self, backdrop=False)
        self.setStyleSheet(self.styleSheet() + STATUS_STYLE)
        self._build_ui()
        self._screen_position_initialized = False

        state_changed = getattr(controller, "pet_state_changed", None)
        if state_changed is not None:
            state_changed.connect(self.set_state)
        self._refresh_timer = QTimer(self)
        self._refresh_timer.setInterval(60_000)
        self._refresh_timer.timeout.connect(self.refresh)
        self._refresh_timer.start()
        self._avatar_timer = QTimer(self)
        self._avatar_timer.setInterval(700)
        self._avatar_timer.timeout.connect(self._refresh_avatar)
        self._avatar_timer.start()
        self.refresh()

    def _build_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(14, 14, 14, 14)
        self.surface = QFrame()
        self.surface.setObjectName("statusSurface")
        outer.addWidget(self.surface)

        root = QVBoxLayout(self.surface)
        root.setContentsMargins(28, 24, 28, 24)
        root.setSpacing(18)

        header = QHBoxLayout()
        title = QLabel("✨ 我的 Maidie")
        title.setObjectName("panelTitle")
        window_close = QPushButton("×")
        window_close.setObjectName("statusWindowClose")
        window_close.setAutoDefault(False)
        window_close.clicked.connect(self.close)
        header.addWidget(title)
        header.addStretch()
        header.addWidget(window_close)
        root.addLayout(header)

        self.scroll_area = QScrollArea()
        self.scroll_area.setObjectName("statusScroll")
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll_area.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self.scroll_area.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded
        )
        self.scroll_area.setSizeAdjustPolicy(
            QAbstractScrollArea.SizeAdjustPolicy.AdjustToContentsOnFirstShow
        )
        self.scroll_area.viewport().setAutoFillBackground(False)
        self.content = QWidget()
        self.content.setObjectName("statusContent")
        content_layout = QVBoxLayout(self.content)
        content_layout.setContentsMargins(8, 8, 8, 10)
        content_layout.setSpacing(18)
        self.scroll_area.setWidget(self.content)
        root.addWidget(self.scroll_area, 1)

        profile = self._card()
        profile_layout = QHBoxLayout(profile)
        profile_layout.setContentsMargins(22, 20, 22, 20)
        profile_layout.setSpacing(22)
        self.avatar = QLabel()
        self.avatar.setFixedSize(150, 150)
        self.avatar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.avatar.setStyleSheet(
            "background:#e4f1ff;border:1px solid #c1dbf3;border-radius:75px;"
        )
        self._refresh_avatar()
        profile_layout.addWidget(self.avatar)

        identity = QVBoxLayout()
        identity.setSpacing(8)
        self.name_label = QLabel("Maidie")
        self.name_label.setObjectName("petName")
        self.level_label = QLabel("Lv.1")
        self.level_label.setObjectName("petLevel")
        self.relationship_label = QLabel("初识")
        self.relationship_label.setObjectName("relationshipChip")
        identity.addStretch()
        identity.addWidget(self.name_label)
        identity.addWidget(self.level_label)
        identity.addWidget(
            self.relationship_label, alignment=Qt.AlignmentFlag.AlignLeft
        )
        identity.addStretch()
        profile_layout.addLayout(identity, 1)
        content_layout.addWidget(profile)

        attributes = self._card()
        grid = QGridLayout(attributes)
        grid.setContentsMargins(22, 20, 22, 20)
        grid.setHorizontalSpacing(14)
        grid.setVerticalSpacing(13)
        self.affection_bar = self._progress_bar("affectionBar")
        self.energy_bar = self._progress_bar("energyBar")
        self.affection_value = QLabel("0 / 100")
        self.mood_value = QLabel("平静")
        self.energy_value = QLabel("82%")
        self.companion_value = QLabel("0天0小时")
        for value in (
            self.affection_value,
            self.mood_value,
            self.energy_value,
            self.companion_value,
        ):
            value.setObjectName("attributeValue")
        self._add_attribute(grid, 0, "❤️ 亲密度", self.affection_value)
        grid.addWidget(self.affection_bar, 1, 0, 1, 2)
        self._add_attribute(grid, 2, "😊 当前心情", self.mood_value)
        self._add_attribute(grid, 3, "⚡ 精力", self.energy_value)
        grid.addWidget(self.energy_bar, 4, 0, 1, 2)
        self._add_attribute(grid, 5, "🌱 陪伴时间", self.companion_value)
        content_layout.addWidget(attributes)

        interactions_title = QLabel("今天也有好好陪着彼此")
        interactions_title.setObjectName("sectionTitle")
        content_layout.addWidget(interactions_title)
        interactions = QHBoxLayout()
        interactions.setSpacing(12)
        self.chat_count = self._interaction_item("💬", "聊天", interactions)
        self.headpat_count = self._interaction_item("✋", "摸头", interactions)
        self.click_count = self._interaction_item("👆", "点击", interactions)
        content_layout.addLayout(interactions)

        close_button = QPushButton("好啦，继续陪我")
        close_button.setObjectName("statusCloseButton")
        close_button.setAutoDefault(False)
        close_button.setDefault(False)
        close_button.clicked.connect(self.close)
        content_layout.addWidget(
            close_button, alignment=Qt.AlignmentFlag.AlignRight
        )

    def _card(self) -> QFrame:
        card = QFrame()
        card.setObjectName("statusCard")
        _soft_shadow(card)
        return card

    @staticmethod
    def _progress_bar(name: str) -> QProgressBar:
        bar = QProgressBar()
        bar.setObjectName(name)
        bar.setRange(0, 100)
        bar.setTextVisible(False)
        return bar

    @staticmethod
    def _add_attribute(
        layout: QGridLayout, row: int, label: str, value: QLabel
    ) -> None:
        title = QLabel(label)
        title.setObjectName("attributeLabel")
        layout.addWidget(title, row, 0)
        layout.addWidget(value, row, 1, alignment=Qt.AlignmentFlag.AlignRight)

    @staticmethod
    def _interaction_item(
        icon: str, label: str, layout: QHBoxLayout
    ) -> QLabel:
        card = QFrame()
        card.setObjectName("interactionItem")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(16, 12, 16, 12)
        card_layout.setSpacing(2)
        count = QLabel("0")
        count.setObjectName("interactionCount")
        name = QLabel(f"{icon} {label}")
        name.setObjectName("interactionName")
        count.setAlignment(Qt.AlignmentFlag.AlignCenter)
        name.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card_layout.addWidget(count)
        card_layout.addWidget(name)
        layout.addWidget(card, 1)
        return count

    def _refresh_avatar(self) -> None:
        pixmap = QPixmap()
        if self.avatar_provider is not None:
            try:
                current = self.avatar_provider()
                if isinstance(current, QPixmap):
                    pixmap = current
            except Exception:
                pixmap = QPixmap()
        if pixmap.isNull():
            pixmap = QPixmap(str(self.assets_dir / "maidie.png"))
        if pixmap.isNull():
            self.avatar.clear()
            self.avatar.setText("Maidie")
            return
        self.avatar.setPixmap(
            pixmap.scaled(
                130,
                130,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        )

    def refresh(self) -> None:
        snapshot = getattr(self.controller, "pet_state_snapshot", None)
        if callable(snapshot):
            self.set_state(snapshot())

    def set_state(self, state: dict[str, Any]) -> None:
        self.name_label.setText(str(state.get("name", "Maidie")))
        self.level_label.setText(f"Lv.{int(state.get('level', 1))}")
        self.relationship_label.setText(str(state.get("relationship", "初识")))
        affection = max(0, min(100, int(state.get("affection", 0))))
        energy = max(0, min(100, int(state.get("energy", 0))))
        self.affection_bar.setValue(affection)
        self.affection_value.setText(f"{affection} / 100")
        self.mood_value.setText(str(state.get("mood_label", "平静")))
        self.energy_bar.setValue(energy)
        self.energy_value.setText(f"{energy}%")
        self.companion_value.setText(str(state.get("companion_time", "0天0小时")))
        self.chat_count.setText(str(int(state.get("chat_count", 0))))
        self.headpat_count.setText(str(int(state.get("headpat_count", 0))))
        self.click_count.setText(str(int(state.get("click_count", 0))))

    def closeEvent(self, event) -> None:
        self._refresh_timer.stop()
        self._avatar_timer.stop()
        super().closeEvent(event)

    def showEvent(self, event) -> None:
        self._refresh_timer.start()
        self._avatar_timer.start()
        self._refresh_avatar()
        self.refresh()
        super().showEvent(event)
        QTimer.singleShot(0, lambda: disable_windows_backdrop(self))
        QTimer.singleShot(0, self._fit_to_available_screen)

    def paintEvent(self, event) -> None:
        """Clear every alpha pixel before Qt paints the antialiased child surface."""
        painter = QPainter(self)
        painter.setCompositionMode(
            QPainter.CompositionMode.CompositionMode_Source
        )
        painter.fillRect(event.rect(), QColor(0, 0, 0, 0))
        painter.end()
        super().paintEvent(event)

    def _fit_to_available_screen(self) -> None:
        screen = self.screen()
        if screen is None:
            return
        self._fit_to_available_rect(screen.availableGeometry())

    def _fit_to_available_rect(self, available: QRect) -> None:
        """Fit the panel to the current monitor and let content scroll if needed."""
        if available.width() <= 0 or available.height() <= 0:
            return
        self.content.layout().activate()
        self.surface.layout().activate()
        content_hint = self.content.sizeHint()
        header_height = max(52, self.surface.layout().itemAt(0).sizeHint().height())
        ideal_width = max(500, content_hint.width() + 72)
        ideal_height = content_hint.height() + header_height + 76
        max_width = max(340, round(available.width() * 0.92))
        max_height = max(300, round(available.height() * 0.90))
        target_width = min(ideal_width, max_width)
        target_height = min(ideal_height, max_height)
        self.resize(target_width, target_height)

        if not self._screen_position_initialized:
            parent = self.parentWidget()
            center = (
                parent.frameGeometry().center()
                if parent is not None and parent.isVisible()
                else available.center()
            )
            top_left = QPoint(
                center.x() - target_width // 2,
                center.y() - target_height // 2,
            )
            self.move(
                max(available.left(), min(top_left.x(), available.right() - target_width + 1)),
                max(available.top(), min(top_left.y(), available.bottom() - target_height + 1)),
            )
            self._screen_position_initialized = True
            return

        current = self.frameGeometry()
        self.move(
            max(available.left(), min(current.left(), available.right() - target_width + 1)),
            max(available.top(), min(current.top(), available.bottom() - target_height + 1)),
        )

    def mousePressEvent(self, event) -> None:
        if (
            event.button() == Qt.MouseButton.LeftButton
            and event.position().y() <= 72
        ):
            self._drag_offset = (
                event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            )
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:
        if (
            self._drag_offset is not None
            and event.buttons() & Qt.MouseButton.LeftButton
        ):
            self.move(event.globalPosition().toPoint() - self._drag_offset)
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        self._drag_offset = None
        super().mouseReleaseEvent(event)
