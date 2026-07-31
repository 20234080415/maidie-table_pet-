"""Mode-aware AI service clients.

The production Brain only depends on :class:`AIClient`.  This module chooses a
user-owned OpenAI-compatible client, Maidie's invite-token cloud client, or a
disabled client without leaking those transport details into business code.
"""

from __future__ import annotations

import json
import os
from threading import RLock
from typing import Any, Callable

import requests

from ai.client import AIClient, AIResponse, OpenAICompatibleClient, normalize_response
from ai.prompt import (
    CODEX_STREAM_PROMPT,
    CODEX_SYSTEM_PROMPT,
    DESKTOP_AGENT_CAPABILITY_PROMPT,
    MAIDIE_STREAM_PROMPT,
    MAIDIE_SYSTEM_PROMPT,
)
from core.prompts.memory import (
    MEMORY_EXTRACTION_SYSTEM_PROMPT,
    build_memory_extraction_prompt,
)
from core.cloud import cloud_endpoint, runtime_service_settings

AI_MODE_CUSTOM = "custom"
AI_MODE_INVITE = "invite"
AI_MODE_DISABLED = "disabled"


def _configured_api_key(config: dict[str, Any]) -> str:
    shared = config.get("ai", {})
    provider = str(shared.get("provider") or "deepseek")
    environment_key = (
        os.getenv("DEEPSEEK_API_KEY") if provider == "deepseek" else ""
    )
    return str(environment_key or shared.get("api_key") or "").strip()


def _technical_api_key(config: dict[str, Any], shared_key: str) -> str:
    shared = config.get("ai", {})
    technical = config.get("codex", {})
    environment_key = (
        os.getenv("DEEPSEEK_API_KEY")
        if str(shared.get("provider") or "deepseek") == "deepseek"
        else ""
    )
    return str(environment_key or technical.get("api_key") or shared_key).strip()


def resolve_ai_mode(config: dict[str, Any]) -> str:
    """Honor the startup priority: custom API, invite token, then disabled."""
    api_key = _configured_api_key(config)
    if api_key and api_key != "YOUR_API_KEY_HERE":
        return AI_MODE_CUSTOM
    if str(config.get("user_token") or "").strip():
        return AI_MODE_INVITE
    return AI_MODE_DISABLED


def service_runtime_settings(
    config: dict[str, Any], section: str
) -> dict[str, Any]:
    """Backward-compatible alias for the shared cloud service registry."""
    settings = runtime_service_settings(config, section)
    settings["_ai_mode"] = resolve_ai_mode(config)
    return settings


def _cloud_endpoint(config: dict[str, Any], key: str) -> str:
    cloud = config.get("cloud", {})
    service = {
        "verify_invite_path": "verify",
        "chat_path": "ai",
    }.get(key, key.removesuffix("_path"))
    return cloud_endpoint(cloud, service)


class DisabledAIClient(AIClient):
    """Explicit no-service state; local deterministic tools remain available."""

    is_available = False

    def __init__(self, source: str = "chat") -> None:
        self.source = source

    def ask(self, prompt: str, context: list[dict[str, Any]]) -> AIResponse:
        text = (
            "AI 服务尚未配置。可以使用邀请码解锁，或在设置里填写自己的 API Key。"
            if self.source == "chat"
            else "技术模式尚未配置 AI 服务。"
        )
        return normalize_response(
            {
                "text": text,
                "emotion": "thinking",
                "action": "talk",
                "state": "thinking",
            },
            self.source,
        )

    def route_intent(
        self, prompt: str, context: list[dict[str, Any]]
    ) -> dict[str, Any]:
        raise RuntimeError("AI service is not configured")


class InviteAIClient(AIClient):
    """Cloud-backed AI client authenticated only by the user's invite token."""

    is_available = True

    def __init__(
        self,
        endpoint: str,
        user_token: str,
        source: str = "chat",
        personality_prompt: str = "",
        timeout: int = 30,
        request_session: Any = requests,
    ) -> None:
        self.endpoint = endpoint
        self.user_token = user_token
        self.source = source
        self.personality_prompt = personality_prompt
        self.timeout = timeout
        self._requests = request_session

    def _completion(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float,
        max_tokens: int,
        json_mode: bool,
    ) -> str:
        if not self.endpoint or not self.user_token:
            raise RuntimeError("邀请码 AI 服务尚未配置")
        response = self._requests.post(
            self.endpoint,
            headers={
                "Authorization": f"Bearer {self.user_token}",
                "Content-Type": "application/json",
            },
            json={
                "profile": "technical" if self.source == "codex" else "chat",
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
                "json_mode": json_mode,
            },
            timeout=self.timeout,
        )
        if response.status_code == 401:
            raise RuntimeError("邀请码授权已失效，请重新激活")
        response.raise_for_status()
        payload = response.json()
        content = str(payload.get("content") or "").strip()
        if not payload.get("success") or not content:
            raise RuntimeError(str(payload.get("error") or "云端 AI 服务暂时不可用"))
        return content

    @staticmethod
    def _context_messages(
        context: list[dict[str, Any]], limit: int
    ) -> list[dict[str, str]]:
        messages: list[dict[str, str]] = []
        for item in context[-limit:]:
            if item.get("memory"):
                messages.append({"role": "system", "content": str(item["memory"])})
                continue
            messages.extend(
                [
                    {"role": "user", "content": str(item.get("message", ""))},
                    {
                        "role": "assistant",
                        "content": str(item.get("response", "")),
                    },
                ]
            )
        return messages

    def ask(self, prompt: str, context: list[dict[str, Any]]) -> AIResponse:
        system_prompt = (
            CODEX_SYSTEM_PROMPT if self.source == "codex" else MAIDIE_SYSTEM_PROMPT
        )
        if self.source == "chat" and self.personality_prompt:
            system_prompt += f"\nCurrent personality: {self.personality_prompt}"
        messages = [{"role": "system", "content": system_prompt}]
        messages.extend(self._context_messages(context, 10))
        messages.append({"role": "user", "content": prompt})
        content = self._completion(
            messages,
            temperature=0.8 if self.source == "chat" else 0.2,
            max_tokens=2048,
            json_mode=True,
        )
        return normalize_response(json.loads(content), self.source)

    def ask_stream(
        self,
        prompt: str,
        context: list[dict[str, Any]],
        on_delta: Callable[[str], None],
    ) -> AIResponse:
        streaming_prompt = (
            CODEX_STREAM_PROMPT if self.source == "codex" else MAIDIE_STREAM_PROMPT
        )
        if self.source == "chat" and self.personality_prompt:
            streaming_prompt += f"\nCurrent personality: {self.personality_prompt}"
        messages = [{"role": "system", "content": streaming_prompt}]
        messages.extend(self._context_messages(context, 10))
        messages.append({"role": "user", "content": prompt})
        content = self._completion(
            messages,
            temperature=0.8 if self.source == "chat" else 0.2,
            max_tokens=2048,
            json_mode=False,
        )
        on_delta(content)
        return normalize_response(
            {
                "text": content,
                "emotion": "thinking" if self.source == "codex" else "idle",
                "action": "talk",
                "state": "talking",
            },
            self.source,
        )

    def route_intent(
        self, prompt: str, context: list[dict[str, Any]]
    ) -> dict[str, Any]:
        messages = [
            {
                "role": "system",
                "content": "You return only strict JSON for intent routing.",
            }
        ]
        messages.extend(self._context_messages(context, 6))
        messages.append({"role": "user", "content": prompt})
        result = json.loads(
            self._completion(
                messages, temperature=0, max_tokens=300, json_mode=True
            )
        )
        if not isinstance(result, dict):
            raise ValueError("intent router returned non-object JSON")
        return result

    def extract_memories(
        self, message: str, response: str
    ) -> dict[str, list[Any]]:
        try:
            result = json.loads(
                self._completion(
                    [
                        {
                            "role": "system",
                            "content": (
                                DESKTOP_AGENT_CAPABILITY_PROMPT
                                + "\n"
                                + MEMORY_EXTRACTION_SYSTEM_PROMPT
                            ),
                        },
                        {
                            "role": "user",
                            "content": build_memory_extraction_prompt(
                                message, response
                            ),
                        },
                    ],
                    temperature=0,
                    max_tokens=800,
                    json_mode=True,
                )
            )
            return {
                "facts": result.get("facts", []) if isinstance(result, dict) else [],
                "preferences": (
                    result.get("preferences", [])
                    if isinstance(result, dict)
                    else []
                ),
            }
        except Exception:
            return {"facts": [], "preferences": []}

    def plan_task(
        self, message: str, memory_context: str
    ) -> dict[str, Any] | None:
        planner_prompt = (
            "你是 Maidie 的任务规划器，只能输出 JSON，不能回答用户。"
            "格式：{\"goal\":\"...\",\"steps\":[{\"tool\":"
            "\"time|weather|search|system|memory|llm\",\"action\":\"...\","
            "\"params\":{},\"requires_confirmation\":false}]}。至少一个步骤；"
            "显式选择工具；llm 只能用于最终总结。时间必须用 time，天气必须用 weather，"
            "需要外部资料才用 search。\n文件或应用操作必须用 system，并在 "
            "params.operation 指定动作；非只读操作 requires_confirmation 必须为 true。\n"
            f"用户背景：{memory_context or '无'}\n用户任务：{message}"
        )
        try:
            result = json.loads(
                self._completion(
                    [
                        {
                            "role": "system",
                            "content": (
                                DESKTOP_AGENT_CAPABILITY_PROMPT
                                + "\n只生成任务计划 JSON。"
                            ),
                        },
                        {"role": "user", "content": planner_prompt},
                    ],
                    temperature=0,
                    max_tokens=1000,
                    json_mode=True,
                )
            )
            return result if isinstance(result, dict) else None
        except Exception:
            return None


class UnifiedAIClient(AIClient):
    """Hot-swappable client used by the unchanged Agent pipeline."""

    def __init__(
        self,
        config: dict[str, Any],
        source: str,
        personality_prompt: str = "",
    ) -> None:
        self.source = source
        self._lock = RLock()
        self._mode = AI_MODE_DISABLED
        self._delegate: AIClient = DisabledAIClient(source)
        self.configure(config, personality_prompt)

    @property
    def mode(self) -> str:
        return self._mode

    @property
    def is_available(self) -> bool:
        return bool(getattr(self._delegate, "is_available", True))

    @property
    def personality_prompt(self) -> str:
        return str(getattr(self._delegate, "personality_prompt", ""))

    @personality_prompt.setter
    def personality_prompt(self, value: str) -> None:
        if hasattr(self._delegate, "personality_prompt"):
            self._delegate.personality_prompt = value

    def configure(
        self, config: dict[str, Any], personality_prompt: str = ""
    ) -> None:
        mode = resolve_ai_mode(config)
        shared = config.get("ai", {})
        technical = config.get("codex", {})
        if mode == AI_MODE_CUSTOM:
            shared_key = _configured_api_key(config)
            delegate: AIClient = OpenAICompatibleClient(
                api_key=(
                    _technical_api_key(config, shared_key)
                    if self.source == "codex"
                    else shared_key
                ),
                base_url=(
                    str(technical.get("base_url") or shared.get("base_url") or "")
                    if self.source == "codex"
                    else str(shared.get("base_url") or "")
                ),
                model=(
                    str(technical.get("model") or "deepseek-v4-pro")
                    if self.source == "codex"
                    else str(shared.get("model") or "deepseek-v4-flash")
                ),
                system_prompt=(
                    CODEX_SYSTEM_PROMPT
                    if self.source == "codex"
                    else MAIDIE_SYSTEM_PROMPT
                ),
                source=self.source,
                personality_prompt=personality_prompt,
                timeout=int(
                    technical.get("timeout", 90)
                    if self.source == "codex"
                    else shared.get("timeout", 30)
                ),
            )
        elif mode == AI_MODE_INVITE:
            cloud = config.get("cloud", {})
            delegate = InviteAIClient(
                endpoint=_cloud_endpoint(config, "chat_path"),
                user_token=str(config.get("user_token") or ""),
                source=self.source,
                personality_prompt=personality_prompt,
                timeout=int(cloud.get("timeout", 30)),
            )
        else:
            delegate = DisabledAIClient(self.source)
        with self._lock:
            self._delegate = delegate
            self._mode = mode

    def _current(self) -> AIClient:
        with self._lock:
            return self._delegate

    def ask(self, prompt: str, context: list[dict[str, Any]]) -> AIResponse:
        return self._current().ask(prompt, context)

    def ask_stream(
        self,
        prompt: str,
        context: list[dict[str, Any]],
        on_delta: Callable[[str], None],
    ) -> AIResponse:
        return self._current().ask_stream(prompt, context, on_delta)

    def route_intent(
        self, prompt: str, context: list[dict[str, Any]]
    ) -> dict[str, Any]:
        return self._current().route_intent(prompt, context)

    def decide_recovery(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self._current().decide_recovery(payload)

    def extract_memories(
        self, message: str, response: str
    ) -> dict[str, list[Any]]:
        return self._current().extract_memories(message, response)

    def plan_task(
        self, message: str, memory_context: str
    ) -> dict[str, Any] | None:
        return self._current().plan_task(message, memory_context)


class InviteActivationService:
    """Verify an invite and persist only the returned user token."""

    def __init__(self, config_store: Any, request_session: Any = requests) -> None:
        self.config_store = config_store
        self._requests = request_session

    def activate(self, invite_code: str) -> dict[str, Any]:
        code = str(invite_code or "").strip()
        if not code:
            return {"success": False, "message": "邀请码无效，请检查后重试"}
        config = self.config_store.load()
        endpoint = _cloud_endpoint(config, "verify_invite_path")
        if not endpoint:
            return {
                "success": False,
                "message": "邀请码服务尚未配置，请稍后重试",
            }
        try:
            existing_token = str(config.get("user_token") or "").strip()
            headers = (
                {"Authorization": f"Bearer {existing_token}"}
                if existing_token
                else None
            )
            response = self._requests.post(
                endpoint,
                headers=headers,
                json={
                    "invite_code": code,
                    "device_id": self.config_store.ensure_device_id(),
                },
                timeout=int(config.get("cloud", {}).get("timeout", 30)),
            )
            payload = response.json()
        except (requests.RequestException, ValueError, TypeError):
            return {
                "success": False,
                "message": "邀请码服务暂时不可用，请稍后重试",
            }

        token = str(payload.get("token") or "").strip()
        if (
            response.ok
            and payload.get("success") is True
            and payload.get("already_active") is True
            and existing_token
        ):
            return {
                "success": True,
                "message": "邀请码授权已经生效，无需重复激活",
                "config": config,
            }
        if response.ok and payload.get("success") is True and token:
            try:
                saved = self.config_store.save_invite_token(token)
            except (OSError, ValueError, TypeError):
                return {
                    "success": False,
                    "message": "邀请码已验证，但授权保存失败，请重新输入同一邀请码",
                }
            return {
                "success": True,
                "message": "Maidie准备好陪你啦~",
                "config": saved,
            }
        return {"success": False, "message": "邀请码无效，请检查后重试"}


def build_ai_clients(
    config: dict[str, Any], personality_prompt: str = ""
) -> tuple[UnifiedAIClient, UnifiedAIClient]:
    return (
        UnifiedAIClient(config, "chat", personality_prompt),
        UnifiedAIClient(config, "codex"),
    )
