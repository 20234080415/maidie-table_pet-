"""Shared invite-cloud service registry.

New invite-backed capabilities register one path key and one transport adapter;
token persistence and the Agent pipeline do not need to change.
"""

from __future__ import annotations

import os
from typing import Any

SERVICE_PATH_KEYS = {
    "verify": "verify_invite_path",
    "ai": "chat_path",
    "search": "search_path",
    "vision": "vision_path",
}


def cloud_endpoint(cloud: dict[str, Any], service: str) -> str:
    base_url = str(
        os.getenv("MAIDIE_CLOUD_BASE_URL") or cloud.get("base_url") or ""
    ).rstrip("/")
    path_key = SERVICE_PATH_KEYS.get(service, f"{service}_path")
    path = str(cloud.get(path_key) or "").strip()
    if not base_url or not path:
        return ""
    return f"{base_url}/{path.lstrip('/')}"


def runtime_service_settings(
    config: dict[str, Any], section: str
) -> dict[str, Any]:
    """Attach opaque cloud auth to one runtime adapter, never to public UI data."""
    settings = dict(config.get(section, {}))
    settings["_user_token"] = str(config.get("user_token") or "")
    settings["_cloud"] = dict(config.get("cloud", {}))
    return settings
