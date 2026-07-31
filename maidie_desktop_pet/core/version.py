"""从根目录 ``version.json`` 提供 Maidie 的统一版本信息。"""

from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path


_SEMVER_PATTERN = re.compile(
    r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$"
)
_SUPPORTED_CHANNELS = {"beta", "stable"}


@dataclass(frozen=True, slots=True)
class VersionInfo:
    """经过校验的应用版本数据。"""

    name: str
    version: str
    channel: str
    build: int
    release_date: str

    @property
    def semver_parts(self) -> tuple[int, int, int]:
        major, minor, patch = (int(part) for part in self.version.split("."))
        return major, minor, patch

    @property
    def version_label(self) -> str:
        return f"v{self.version}"

    @property
    def channel_label(self) -> str:
        return self.channel.capitalize()

    @property
    def full_version(self) -> str:
        return f"{self.version}-{self.channel} (Build {self.build})"


def version_file_path() -> Path:
    """返回源码运行或 PyInstaller 运行时的 ``version.json`` 路径。"""

    bundle_root = getattr(sys, "_MEIPASS", None)
    if bundle_root:
        return Path(bundle_root) / "version.json"
    return Path(__file__).resolve().parents[1] / "version.json"


def load_version_info(path: Path | None = None) -> VersionInfo:
    """读取并严格校验版本文件，避免各发布入口出现版本漂移。"""

    source = Path(path) if path is not None else version_file_path()
    try:
        payload = json.loads(source.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"无法读取 Maidie 版本文件：{source}") from exc

    if not isinstance(payload, dict):
        raise ValueError("version.json 顶层必须是 JSON 对象")

    name = payload.get("name")
    version = payload.get("version")
    channel = payload.get("channel")
    build = payload.get("build")
    release_date = payload.get("release_date")

    if not isinstance(name, str) or not name.strip():
        raise ValueError("version.json 的 name 必须是非空字符串")
    if not isinstance(version, str) or _SEMVER_PATTERN.fullmatch(version) is None:
        raise ValueError("version.json 的 version 必须符合 MAJOR.MINOR.PATCH")
    if channel not in _SUPPORTED_CHANNELS:
        raise ValueError("version.json 的 channel 只能是 beta 或 stable")
    if isinstance(build, bool) or not isinstance(build, int) or build < 0:
        raise ValueError("version.json 的 build 必须是非负整数")
    if not isinstance(release_date, str) or not release_date.strip():
        raise ValueError("version.json 的 release_date 必须是非空字符串")

    return VersionInfo(
        name=name.strip(),
        version=version,
        channel=channel,
        build=build,
        release_date=release_date.strip(),
    )


VERSION_INFO = load_version_info()

# 兼容原有 ``from core.version import APP_*`` 调用方式。
APP_NAME = VERSION_INFO.name
APP_VERSION = VERSION_INFO.version
APP_VERSION_LABEL = VERSION_INFO.version_label
APP_CHANNEL = VERSION_INFO.channel
APP_CHANNEL_LABEL = VERSION_INFO.channel_label
APP_BUILD = VERSION_INFO.build
APP_RELEASE_DATE = VERSION_INFO.release_date
APP_FULL_VERSION = VERSION_INFO.full_version
APP_DISPLAY_VERSION = "0.demo"
APP_AUTHOR = "大橘味定"
APP_DESCRIPTION = "一个行为驱动的 AI 桌面伙伴 / 桌面 Agent"
APP_TECH_STACK = "Python + PyQt6 + LLM Agent + vision_ai"
APP_GITHUB_URL = "https://github.com/20234080415/maidie-table_pet-agent"
