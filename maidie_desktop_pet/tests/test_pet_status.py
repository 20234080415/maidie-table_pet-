from __future__ import annotations

import os
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtCore import QObject, QRect, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QImage, QPainter, QPixmap
from PyQt6.QtWidgets import QApplication

from core.affection_system import AffectionSystem
from core.pet_state import PetStateData, PetStateManager
from core.time_manager import TimeManager
from database.pet_state_store import PetStateStore
from ui.pet_menu import PetContextMenu
from ui.status_widget import StatusWidget


class PetStateTests(unittest.TestCase):
    def test_relationship_thresholds_and_interaction_growth(self):
        system = AffectionSystem()
        state = PetStateData(
            affection=44,
            level=5,
            first_meet_time=datetime(2026, 1, 1).astimezone(),
        )
        state = system.apply_interaction(state, "headpat")
        self.assertEqual(state.affection, 47)
        self.assertEqual(state.level, 5)
        self.assertEqual(system.relationship_for(state.affection), "朋友")
        self.assertEqual(state.interaction_count, 1)

    def test_manager_tracks_today_counts_and_ui_snapshot(self):
        manager = PetStateManager()
        manager.record_interaction("chat")
        manager.record_interaction("headpat")
        manager.record_interaction("click")
        snapshot = manager.snapshot("shy")
        self.assertEqual(snapshot["chat_count"], 1)
        self.assertEqual(snapshot["headpat_count"], 1)
        self.assertEqual(snapshot["click_count"], 1)
        self.assertEqual(snapshot["interaction_count"], 3)
        self.assertEqual(snapshot["mood_label"], "害羞")
        self.assertIn(snapshot["relationship"], ("初识", "熟悉"))

    def test_sqlite_store_round_trip(self):
        with tempfile.TemporaryDirectory() as root:
            store = PetStateStore(Path(root) / "pet_state.db")
            state = PetStateData(
                mood=77,
                energy=66,
                affection=42,
                level=5,
                first_meet_time=datetime(2026, 2, 3, 4, 5).astimezone(),
                interaction_count=12,
                chat_count=3,
            )
            store.save(state)
            restored = store.load()
        self.assertEqual(restored.mood, 77)
        self.assertEqual(restored.affection, 42)
        self.assertEqual(restored.chat_count, 3)
        self.assertEqual(restored.interaction_count, 12)

    def test_companion_time_format(self):
        first = datetime(2026, 1, 1, 8, 0).astimezone()
        now = datetime(2026, 1, 24, 14, 0).astimezone()
        self.assertEqual(TimeManager().companion_time_text(first, now), "23天6小时")


class _StatusController(QObject):
    pet_state_changed = pyqtSignal(object)

    def pet_state_snapshot(self):
        return {
            "name": "Maidie",
            "level": 4,
            "relationship": "朋友",
            "affection": 48,
            "mood_label": "开心",
            "energy": 73,
            "companion_time": "23天6小时",
            "chat_count": 5,
            "headpat_count": 2,
            "click_count": 9,
        }


class StatusWidgetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])
        cls.assets = Path(__file__).resolve().parents[1] / "assets"

    def test_status_widget_renders_companionship_state(self):
        widget = StatusWidget(_StatusController(), self.assets)
        self.assertEqual(widget.windowTitle(), "我的 Maidie")
        self.assertTrue(
            widget.testAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        )
        self.assertTrue(
            widget.testAttribute(Qt.WidgetAttribute.WA_NoSystemBackground)
        )
        self.assertEqual(widget.name_label.text(), "Maidie")
        self.assertEqual(widget.level_label.text(), "Lv.4")
        self.assertEqual(widget.relationship_label.text(), "朋友")
        self.assertEqual(widget.affection_bar.value(), 48)
        self.assertEqual(widget.mood_value.text(), "开心")
        self.assertEqual(widget.energy_value.text(), "73%")
        self.assertEqual(widget.companion_value.text(), "23天6小时")
        self.assertEqual(widget.chat_count.text(), "5")
        widget._fit_to_available_rect(QRect(0, 0, 520, 420))
        self.assertLessEqual(widget.width(), round(520 * 0.92))
        self.assertLessEqual(widget.height(), round(420 * 0.90))
        self.assertEqual(
            widget.scroll_area.verticalScrollBarPolicy(),
            Qt.ScrollBarPolicy.ScrollBarAsNeeded,
        )
        self.assertTrue(widget.mask().isEmpty())
        rendered = QImage(
            widget.size(), QImage.Format.Format_ARGB32_Premultiplied
        )
        rendered.fill(Qt.GlobalColor.transparent)
        painter = QPainter(rendered)
        widget.render(painter)
        painter.end()
        self.assertEqual(rendered.pixelColor(0, 0).alpha(), 0)
        self.assertGreater(
            rendered.pixelColor(widget.width() // 2, widget.height() // 2).alpha(),
            0,
        )
        widget.close()

    def test_status_widget_prefers_current_pet_avatar_provider(self):
        current_pet = QPixmap(24, 24)
        current_pet.fill(QColor("#336699"))
        widget = StatusWidget(
            _StatusController(),
            self.assets,
            avatar_provider=lambda: current_pet,
        )
        rendered = widget.avatar.pixmap()
        self.assertIsNotNone(rendered)
        self.assertFalse(rendered.isNull())
        self.assertEqual(rendered.toImage().pixelColor(10, 10), QColor("#336699"))
        widget.close()

    def test_pet_menu_uses_smooth_transparent_popup_surface(self):
        menu = PetContextMenu()
        menu.addAction("聊聊")
        menu.addAction("设置")
        menu.resize(238, 110)
        rendered = QImage(
            menu.size(), QImage.Format.Format_ARGB32_Premultiplied
        )
        rendered.fill(Qt.GlobalColor.transparent)
        painter = QPainter(rendered)
        menu.render(painter)
        painter.end()

        self.assertTrue(
            menu.windowFlags() & Qt.WindowType.FramelessWindowHint
        )
        self.assertTrue(
            menu.windowFlags() & Qt.WindowType.NoDropShadowWindowHint
        )
        self.assertEqual(rendered.pixelColor(0, 0).alpha(), 0)
        corner_alphas = {
            rendered.pixelColor(x, y).alpha()
            for x in range(0, 18)
            for y in range(0, 18)
        }
        self.assertTrue(any(0 < alpha < 255 for alpha in corner_alphas))
        menu.close()


if __name__ == "__main__":
    unittest.main()
