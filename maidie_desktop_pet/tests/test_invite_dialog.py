from __future__ import annotations

import unittest

from PyQt6.QtWidgets import QApplication, QDialog

from ui.invite_dialog import InviteCodeDialog


class InviteCodeDialogTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def test_failure_uses_service_message_instead_of_generic_invalid_text(self):
        dialog = InviteCodeDialog(lambda _code: {})

        dialog._activation_finished(
            {"success": False, "message": "邀请码服务暂时不可用，请稍后重试"}
        )

        self.assertEqual(
            dialog.status.text(), "邀请码服务暂时不可用，请稍后重试"
        )

    def test_already_active_message_is_preserved(self):
        dialog = InviteCodeDialog(lambda _code: {})

        dialog._activation_finished(
            {"success": True, "message": "邀请码授权已经生效，无需重复激活"}
        )

        self.assertEqual(
            dialog.status.text(), "邀请码授权已经生效，无需重复激活"
        )
        self.assertEqual(dialog.result(), QDialog.DialogCode.Accepted)


if __name__ == "__main__":
    unittest.main()
