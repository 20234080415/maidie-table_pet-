from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from ai.service import (
    AI_MODE_CUSTOM,
    AI_MODE_DISABLED,
    AI_MODE_INVITE,
    InviteActivationService,
    build_ai_clients,
)
from core.settings import ConfigStore


class _Response:
    def __init__(self, payload, status_code=200):
        self._payload = payload
        self.status_code = status_code
        self.ok = 200 <= status_code < 300

    def json(self):
        return self._payload

    def raise_for_status(self):
        if not self.ok:
            raise RuntimeError(f"HTTP {self.status_code}")


class _Session:
    def __init__(self, response):
        self.response = response
        self.calls = []

    def post(self, url, **kwargs):
        self.calls.append((url, kwargs))
        return self.response


class DualAIServiceTests(unittest.TestCase):
    def setUp(self):
        self.environment = patch.dict(
            "os.environ",
            {"DEEPSEEK_API_KEY": "", "MAIDIE_CLOUD_BASE_URL": ""},
        )
        self.environment.start()
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / "config.json"
        self.path.write_text(
            json.dumps(
                {
                    "ai": {
                        "provider": "deepseek",
                        "api_key": "",
                        "base_url": "https://api.deepseek.com",
                        "model": "chat-model",
                    },
                    "codex": {"model": "technical-model"},
                    "personality": {"preset": "healing", "custom_prompt": ""},
                    "cloud": {
                        "base_url": "https://maidie.example",
                        "verify_invite_path": "/functions/v1/verify-invite",
                        "chat_path": "/functions/v1/maidie-chat",
                        "timeout": 30,
                    },
                }
            ),
            encoding="utf-8",
        )
        self.store = ConfigStore(self.path)

    def tearDown(self):
        self.temp.cleanup()
        self.environment.stop()

    def test_existing_user_api_has_priority_and_still_chats(self):
        config = self.store.load()
        config["ai"]["api_key"] = "user-owned-key"
        config["user_token"] = "invite-token-that-must-not-win"
        self.store._atomic_write(config)
        chat, _technical = build_ai_clients(self.store.load())

        provider_result = {
            "choices": [
                {
                    "message": {
                        "content": json.dumps(
                            {
                                "text": "custom-ok",
                                "emotion": "idle",
                                "action": "talk",
                                "state": "talking",
                            }
                        )
                    }
                }
            ]
        }
        with patch("ai.client.requests.post", return_value=_Response(provider_result)):
            result = chat.chat("hello")

        self.assertEqual(chat.mode, AI_MODE_CUSTOM)
        self.assertEqual(result["text"], "custom-ok")

    def test_valid_invite_persists_only_token_and_enables_chat(self):
        activation_session = _Session(
            _Response({"success": True, "token": "opaque-user-token"})
        )
        result = InviteActivationService(
            self.store, request_session=activation_session
        ).activate("MAIDIE-OK")
        saved = self.store.load()

        self.assertTrue(result["success"])
        self.assertEqual(saved["ai_mode"], AI_MODE_INVITE)
        self.assertEqual(saved["user_token"], "opaque-user-token")
        self.assertEqual(saved["ai"]["api_key"], "")
        request_json = activation_session.calls[0][1]["json"]
        self.assertEqual(request_json["invite_code"], "MAIDIE-OK")
        self.assertTrue(request_json["device_id"])

        chat, _technical = build_ai_clients(saved)
        cloud_content = json.dumps(
            {
                "text": "invite-ok",
                "emotion": "idle",
                "action": "talk",
                "state": "talking",
            }
        )
        with patch(
            "ai.service.requests.post",
            return_value=_Response({"success": True, "content": cloud_content}),
        ):
            response = chat.chat("hello")
        self.assertEqual(chat.mode, AI_MODE_INVITE)
        self.assertEqual(response["text"], "invite-ok")

    def test_invalid_invite_shows_failure_and_does_not_save_token(self):
        session = _Session(_Response({"success": False}, status_code=400))
        result = InviteActivationService(
            self.store, request_session=session
        ).activate("WRONG-CODE")

        self.assertFalse(result["success"])
        self.assertEqual(result["message"], "邀请码无效，请检查后重试")
        self.assertEqual(self.store.load()["user_token"], "")
        self.assertEqual(self.store.load()["ai_mode"], AI_MODE_DISABLED)

    def test_verified_invite_reports_local_persistence_failure(self):
        session = _Session(
            _Response({"success": True, "token": "recoverable-user-token"})
        )
        with patch.object(
            self.store, "save_invite_token", side_effect=OSError("disk busy")
        ):
            result = InviteActivationService(
                self.store, request_session=session
            ).activate("MAIDIE-RETRY")

        self.assertFalse(result["success"])
        self.assertEqual(
            result["message"],
            "邀请码已验证，但授权保存失败，请重新输入同一邀请码",
        )
        self.assertTrue(self.store.load()["device_id"])
        self.assertEqual(self.store.load()["user_token"], "")

    def test_invite_token_is_saved_even_when_custom_chat_api_has_priority(self):
        config = self.store.load()
        config["ai"]["api_key"] = "user-owned-key"
        self.store._atomic_write(config)
        session = _Session(
            _Response({"success": True, "token": "shared-service-token"})
        )

        result = InviteActivationService(
            self.store, request_session=session
        ).activate("MAIDIE-SHARED")
        saved = self.store.load()

        self.assertTrue(result["success"])
        self.assertEqual(saved["ai_mode"], AI_MODE_CUSTOM)
        self.assertEqual(saved["user_token"], "shared-service-token")

    def test_existing_active_token_is_sent_and_kept_without_redeeming_again(self):
        self.store.save_invite_token("existing-active-token")
        session = _Session(
            _Response({"success": True, "already_active": True})
        )

        result = InviteActivationService(
            self.store, request_session=session
        ).activate("ANOTHER-INVITE")
        saved = self.store.load()

        self.assertTrue(result["success"])
        self.assertEqual(result["message"], "邀请码授权已经生效，无需重复激活")
        self.assertEqual(saved["user_token"], "existing-active-token")
        self.assertEqual(
            session.calls[0][1]["headers"]["Authorization"],
            "Bearer existing-active-token",
        )

    def test_deleting_token_requires_authorization_again(self):
        self.store.save_invite_token("opaque-user-token")
        self.assertEqual(self.store.load()["ai_mode"], AI_MODE_INVITE)

        self.store.clear_invite_token()
        config = self.store.load()
        chat, _technical = build_ai_clients(config)

        self.assertEqual(config["ai_mode"], AI_MODE_DISABLED)
        self.assertEqual(chat.mode, AI_MODE_DISABLED)
        self.assertIn("尚未配置", chat.chat("hello")["text"])

    def test_public_settings_never_expose_token_or_device_id(self):
        self.store.save_invite_token("opaque-user-token")
        self.store.ensure_device_id()
        public = self.store.public_settings()

        self.assertTrue(public["has_user_token"])
        self.assertNotIn("user_token", public)
        self.assertNotIn("device_id", public)
        self.assertNotIn("opaque-user-token", repr(public))


if __name__ == "__main__":
    unittest.main()
