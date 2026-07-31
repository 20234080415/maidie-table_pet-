"""Qwen Vision adapter authenticated with Maidie's shared invite token."""

from __future__ import annotations

from typing import Any

import requests

from core.vision.errors import VisionAPIError, VisionConfigError
from core.vision.vision_context import VisionContext


class InviteVisionClient:
    def __init__(
        self,
        endpoint: str,
        user_token: str,
        timeout: float = 30.0,
        request_session: Any = requests,
    ) -> None:
        self.endpoint = endpoint
        self.user_token = user_token
        self.timeout = timeout
        self._requests = request_session

    def analyze_image(
        self,
        image_data_url: str,
        user_question: str,
        image_size: tuple[int, int] | None = None,
    ) -> VisionContext:
        if not self.endpoint or not self.user_token:
            raise VisionConfigError("邀请码视觉服务尚未配置。")
        try:
            response = self._requests.post(
                self.endpoint,
                headers={
                    "Authorization": f"Bearer {self.user_token}",
                    "Content-Type": "application/json",
                },
                json={
                    "image_data_url": image_data_url,
                    "user_question": str(user_question or ""),
                },
                timeout=self.timeout,
            )
            if response.status_code == 401:
                raise VisionConfigError("邀请码授权已失效，请重新激活。")
            response.raise_for_status()
            payload = response.json()
            context = payload.get("context")
            if not payload.get("success") or not isinstance(context, dict):
                raise VisionAPIError("千问视觉服务调用失败")
            raw = str(payload.get("raw") or "")
            return VisionContext.from_dict(
                context, raw_response=raw, image_size=image_size
            )
        except VisionConfigError:
            raise
        except Exception as exc:
            raise VisionAPIError("千问视觉服务调用失败") from exc
