from __future__ import annotations

import os
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtCore import QRect
from PyQt6.QtWidgets import QApplication

from core.pet import PetController
from input.manager import InputManager
from ui.window import PetWindow


class _Memory:
    def get_recent(self): return []
    def prompt_context(self): return ""
    def save(self, *_args): pass


class ShutdownTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])
        cls.assets = Path(__file__).resolve().parents[1] / "assets"

    def make_controller(self):
        return PetController(object(), _Memory(), logger=Mock())

    def test_pet_controller_shutdown_is_idempotent_and_stops_timers(self):
        controller = self.make_controller()
        controller.shutdown()
        controller.shutdown()
        self.assertTrue(controller._shutting_down)
        self.assertFalse(controller._tick_timer.isActive())
        self.assertFalse(controller._proactive_timer.isActive())
        self.assertFalse(controller._proactive_poll_timer.isActive())
        self.assertFalse(controller.ai_session.poll_timer.isActive())

    def test_tick_is_ignored_after_shutdown(self):
        controller = self.make_controller()
        positions = []
        controller.position_requested.connect(lambda x, y: positions.append((x, y)))
        controller.shutdown()
        controller._tick()
        self.assertEqual(positions, [])

    def test_input_manager_shutdown_is_idempotent(self):
        manager = InputManager(lambda: QRect(0, 0, 100, 100))
        manager.shutdown()
        manager.shutdown()
        self.assertFalse(manager._timer.isActive())

    def test_window_shutdown_stops_ui_and_controller_once(self):
        controller = self.make_controller()
        original_shutdown = controller.shutdown
        controller.shutdown = Mock(wraps=original_shutdown)
        manager = InputManager(lambda: QRect(0, 0, 100, 100))
        window = PetWindow(controller, self.assets)
        window.set_input_manager(manager)

        window.shutdown()
        window.shutdown()

        controller.shutdown.assert_called_once_with()
        self.assertFalse(window._handle_visibility_timer.isActive())
        self.assertFalse(window._single_click_timer.isActive())
        self.assertFalse(window.character.engine._timer.isActive())
        self.assertFalse(manager._timer.isActive())
        window.close()

    def test_context_menu_contains_product_entries(self):
        controller = self.make_controller()
        window = PetWindow(controller, self.assets)
        menu = window._build_context_menu()
        actions = {action.text(): action for action in menu.actions() if action.text()}
        for label in (
            "🧸  Maidie", "💬  聊聊", "✨  我的 Maidie",
            "📖  Maidie 日记", "🎨  更换皮肤", "⚙  设置",
            "🧱  锁定位置", "❓  帮助与说明", "🚪  退出",
        ):
            self.assertIn(label, actions)
        for old_label in ("放大 10%", "缩小 10%", "恢复默认大小", "检查更新"):
            self.assertNotIn(old_label, actions)

        settings_menu = actions["⚙  设置"].menu()
        self.assertIsNotNone(settings_menu)
        settings_actions = {
            action.text(): action
            for action in settings_menu.actions()
            if action.text()
        }
        for label in (
            "🎞  动画设置", "🔊  声音设置", "🤖  AI 设置",
            "🚀  开机启动", "👗  外观设置",
        ):
            self.assertIn(label, settings_actions)
        appearance = settings_actions["👗  外观设置"].menu()
        self.assertIsNotNone(appearance)
        self.assertEqual(
            [action.text() for action in appearance.actions() if action.text()],
            ["打开外观设置", "放大 10%", "缩小 10%", "恢复默认大小"],
        )
        window.shutdown()
        window.close()

    def test_lock_position_action_reuses_fence_controller(self):
        controller = self.make_controller()
        window = PetWindow(controller, self.assets)
        menu = window._build_context_menu()
        lock_action = next(
            action for action in menu.actions() if action.text() == "🧱  锁定位置"
        )
        self.assertFalse(lock_action.isChecked())
        lock_action.trigger()
        self.assertTrue(controller.fence.is_enabled())
        window._build_context_menu()
        window._set_position_locked(False)
        self.assertFalse(controller.fence.is_enabled())
        window.shutdown()
        window.close()

    def test_cancelling_independent_settings_does_not_quit_application(self):
        controller = self.make_controller()
        window = PetWindow(controller, self.assets)
        observed = []
        dialog = Mock()
        dialog.exec.side_effect = lambda: observed.append(
            self.app.quitOnLastWindowClosed()
        ) or 0

        self.app.setQuitOnLastWindowClosed(True)
        with patch("ui.window.SettingsDialog", return_value=dialog):
            window.show_settings()

        self.assertEqual(observed, [False])
        self.assertTrue(self.app.quitOnLastWindowClosed())
        window.shutdown()
        window.close()


if __name__ == "__main__":
    unittest.main()
