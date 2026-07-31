from __future__ import annotations

import os
import unittest
from pathlib import Path
from time import monotonic
from unittest.mock import Mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtWidgets import QApplication

from core.pet import PetController
from ui.window import PetWindow


class _Memory:
    def get_recent(self):
        return []

    def prompt_context(self):
        return ""

    def save(self, _message, _response):
        pass


class SubmitResponsivenessTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_submit_does_not_route_on_the_qt_thread(self):
        router = Mock()
        router.classify.side_effect = AssertionError("synchronous router call")
        router.ask_stream.return_value = {
            "text": "好。",
            "emotion": "idle",
            "action": "talk",
            "state": "talking",
            "source": "chat",
        }
        controller = PetController(router, _Memory())
        started = monotonic()

        controller.submit_text("你好")

        self.assertLess(monotonic() - started, 0.1)
        router.classify.assert_not_called()
        controller.shutdown()

    def test_busy_request_gets_feedback_instead_of_being_silently_dropped(self):
        controller = PetController(Mock(), _Memory())
        messages = []
        controller.local_message_requested.connect(messages.append)
        controller.ai_session.busy = True

        accepted = controller.submit_text("还有多久")

        self.assertFalse(accepted)
        self.assertEqual(messages, ["我还在分析上一个任务，完成后再告诉我吧。"])
        controller.shutdown()

    def test_submit_reports_when_request_is_accepted(self):
        router = Mock()
        router.ask_stream.return_value = {
            "text": "好。",
            "emotion": "idle",
            "action": "talk",
            "state": "talking",
            "source": "chat",
        }
        controller = PetController(router, _Memory())

        accepted = controller.submit_text("你好")

        self.assertTrue(accepted)
        controller.shutdown()

    def test_busy_window_keeps_unsent_text_in_editor(self):
        controller = PetController(Mock(), _Memory())
        controller.ai_session.busy = True
        window = PetWindow(
            controller,
            Path(__file__).resolve().parents[1] / "assets",
        )
        window.chat_input.open()
        window.chat_input.setText("这条消息还没有发送")

        window.chat_input._submit()

        self.assertEqual(window.chat_input.text(), "这条消息还没有发送")
        self.assertTrue(window.chat_input.isVisible())
        window.shutdown()
        window.close()


if __name__ == "__main__":
    unittest.main()
