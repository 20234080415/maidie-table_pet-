from __future__ import annotations

import unittest
from unittest.mock import patch

from core.cloud import cloud_endpoint, runtime_service_settings
from core.plugins.network import NetworkPlugin
from core.vision.invite_vl_client import InviteVisionClient
from core.vision.qwen_vl_client import QwenVLClient
from core.vision.vision_service import VisionService
from network.search import InviteSearchService, SearchService


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


class InviteCloudServiceTests(unittest.TestCase):
    def setUp(self):
        self.config = {
            "ai": {"api_key": ""},
            "user_token": "one-token-unlocks-all-services",
            "cloud": {
                "base_url": "https://maidie.example",
                "search_path": "/functions/v1/maidie-search",
                "vision_path": "/functions/v1/maidie-vision",
                "timeout": 30,
            },
            "network": {
                "enabled": True,
                "search_provider": "tavily",
                "search_api_key": "",
                "timeout": 10,
                "show_sources": True,
            },
            "vision": {
                "api_key": "",
                "workspace_id": "",
                "model": "qwen3-vl-flash",
                "region": "cn-beijing",
            },
        }

    def test_same_invite_token_configures_search_and_vision(self):
        plugin = NetworkPlugin(runtime_service_settings(self.config, "network"))
        vision = VisionService()
        vision.reconfigure(runtime_service_settings(self.config, "vision"))

        self.assertIsInstance(plugin.search_service, InviteSearchService)
        self.assertEqual(
            plugin.search_service.user_token,
            "one-token-unlocks-all-services",
        )
        self.assertIsInstance(vision.client, InviteVisionClient)
        self.assertEqual(
            vision.client.user_token, "one-token-unlocks-all-services"
        )

    def test_registry_accepts_future_service_without_core_changes(self):
        cloud = dict(self.config["cloud"], voice_path="/functions/v1/maidie-voice")
        self.assertEqual(
            cloud_endpoint(cloud, "voice"),
            "https://maidie.example/functions/v1/maidie-voice",
        )

    def test_invite_search_returns_standard_network_result(self):
        plugin = NetworkPlugin(runtime_service_settings(self.config, "network"))
        payload = {
            "success": True,
            "result": {
                "ok": True,
                "title": "result",
                "summary": "answer",
                "sources": [
                    {
                        "title": "Docs",
                        "url": "https://docs.example/page",
                        "domain": "docs.example",
                    }
                ],
            },
        }
        with patch(
            "network.search.requests.post", return_value=_Response(payload)
        ):
            result = plugin.handle("搜索 Maidie 文档")

        self.assertTrue(result["ok"])
        self.assertEqual(result["summary"], "answer")
        self.assertEqual(result["sources"][0]["domain"], "docs.example")

    def test_invite_vision_returns_standard_context(self):
        vision = VisionService()
        vision.reconfigure(runtime_service_settings(self.config, "vision"))
        payload = {
            "success": True,
            "raw": '{"screen_summary":"IDE"}',
            "context": {
                "screen_summary": "IDE",
                "visible_text": "ValueError",
                "task_type": "code_error",
                "important_regions": ["terminal"],
                "user_intent_guess": "debug",
                "confidence": 0.9,
            },
        }
        with patch(
            "core.vision.invite_vl_client.requests.post",
            return_value=_Response(payload),
        ):
            result = vision.client.analyze_image(
                "data:image/jpeg;base64,AA==", "看看报错", (20, 10)
            )

        self.assertEqual(result.task_type, "code_error")
        self.assertEqual(result.image_size, (20, 10))

    def test_own_service_keys_keep_priority_over_invite(self):
        self.config["network"]["search_api_key"] = "own-tavily-key"
        self.config["vision"]["api_key"] = "own-qwen-key"
        self.config["vision"]["workspace_id"] = "own-workspace"
        plugin = NetworkPlugin(runtime_service_settings(self.config, "network"))
        vision = VisionService()
        vision.reconfigure(runtime_service_settings(self.config, "vision"))

        self.assertIsInstance(plugin.search_service, SearchService)
        self.assertEqual(plugin.search_service.api_key, "own-tavily-key")
        self.assertIsInstance(vision.client, QwenVLClient)
        self.assertEqual(vision.client.api_key, "own-qwen-key")
        self.assertEqual(vision.client.workspace_id, "own-workspace")


if __name__ == "__main__":
    unittest.main()
