"""Maidie 程序资源、用户数据路径与首次启动迁移。"""

from __future__ import annotations

import os
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping


def _resolve_app_path() -> Path:
    """返回源码根目录或 PyInstaller 可执行文件所在目录。"""

    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[1]


def _resolve_resource_path(app_path: Path) -> Path:
    """返回静态资源根目录；兼容 PyInstaller 的临时解包目录。"""

    bundle_root = getattr(sys, "_MEIPASS", None)
    return Path(bundle_root).resolve() if bundle_root else app_path


def _resolve_user_data_path(
    environ: Mapping[str, str] | None = None,
) -> Path:
    """按 Windows 约定解析 ``%APPDATA%\Maidie``。"""

    values = os.environ if environ is None else environ
    roaming = str(values.get("APPDATA") or "").strip()
    if roaming:
        return Path(roaming).expanduser().resolve() / "Maidie"
    if os.name == "nt":
        return Path.home().resolve() / "AppData" / "Roaming" / "Maidie"
    return Path.home().resolve() / ".config" / "Maidie"


@dataclass(frozen=True, slots=True)
class AppPaths:
    """一组可注入测试的 Maidie 路径。"""

    app_path: Path
    resource_path: Path
    user_data_path: Path
    config_path: Path
    log_path: Path
    memory_path: Path
    pet_state_path: Path
    scheduled_tasks_path: Path
    skins_path: Path

    @classmethod
    def create(
        cls,
        *,
        app_path: Path,
        user_data_path: Path,
        resource_path: Path | None = None,
    ) -> "AppPaths":
        app = Path(app_path).resolve()
        resources = Path(resource_path or app).resolve()
        user = Path(user_data_path).resolve()
        return cls(
            app_path=app,
            resource_path=resources,
            user_data_path=user,
            config_path=user / "config.json",
            log_path=user / "logs",
            memory_path=user / "memory.db",
            pet_state_path=user / "pet_state.db",
            scheduled_tasks_path=user / "scheduled_tasks.json",
            skins_path=user / "skins",
        )


@dataclass(frozen=True, slots=True)
class MigrationResult:
    """首次启动迁移的可观测结果。"""

    copied: tuple[Path, ...]
    preserved: tuple[Path, ...]


APP_PATH = _resolve_app_path()
RESOURCE_PATH = _resolve_resource_path(APP_PATH)
USER_DATA_PATH = _resolve_user_data_path()
PATHS = AppPaths.create(
    app_path=APP_PATH,
    resource_path=RESOURCE_PATH,
    user_data_path=USER_DATA_PATH,
)

CONFIG_PATH = PATHS.config_path
LOG_PATH = PATHS.log_path
MEMORY_PATH = PATHS.memory_path
PET_STATE_PATH = PATHS.pet_state_path
SCHEDULED_TASKS_PATH = PATHS.scheduled_tasks_path
SKINS_PATH = PATHS.skins_path
MAIDIE_LOG_PATH = LOG_PATH / "maidie.log"
FILE_AUDIT_PATH = LOG_PATH / "file_operations.jsonl"


def _copy_file_if_missing(source: Path, destination: Path) -> bool:
    """以独占创建方式复制文件，确保并发启动也不会覆盖目标。"""

    if not source.is_file():
        return False
    destination.parent.mkdir(parents=True, exist_ok=True)
    created = False
    try:
        with source.open("rb") as reader, destination.open("xb") as writer:
            created = True
            shutil.copyfileobj(reader, writer)
    except FileExistsError:
        return False
    except Exception:
        if created:
            destination.unlink(missing_ok=True)
        raise
    try:
        shutil.copystat(source, destination)
    except OSError:
        pass
    return True


def _copy_sqlite_if_missing(source: Path, destination: Path) -> list[Path]:
    """复制 SQLite 主文件及可能存在的 WAL/SHM，不改变数据库内容。"""

    if destination.exists() or not source.is_file():
        return []
    if not _copy_file_if_missing(source, destination):
        return []
    copied = [destination]
    for suffix in ("-wal", "-shm"):
        source_sidecar = Path(f"{source}{suffix}")
        destination_sidecar = Path(f"{destination}{suffix}")
        if _copy_file_if_missing(source_sidecar, destination_sidecar):
            copied.append(destination_sidecar)
    return copied


def _copy_tree_missing(source: Path, destination: Path) -> list[Path]:
    """递归补充缺失文件，跳过符号链接且绝不覆盖现有数据。"""

    copied: list[Path] = []
    if not source.is_dir():
        return copied
    for item in sorted(source.rglob("*")):
        if not item.is_file() or item.is_symlink():
            continue
        target = destination / item.relative_to(source)
        if _copy_file_if_missing(item, target):
            copied.append(target)
    return copied


def _first_existing(candidates: tuple[Path, ...]) -> Path | None:
    return next((path for path in candidates if path.is_file()), None)


def initialize_user_data(paths: AppPaths = PATHS) -> MigrationResult:
    """创建用户目录，并按“APPDATA、旧安装目录、默认配置”顺序迁移。

    每个目标仅在不存在时写入，因此升级或重复启动不会覆盖用户数据。
    """

    paths.user_data_path.mkdir(parents=True, exist_ok=True)
    paths.log_path.mkdir(parents=True, exist_ok=True)
    paths.skins_path.mkdir(parents=True, exist_ok=True)

    copied: list[Path] = []
    preserved: list[Path] = []

    # 先兼容可能已经写入 APPDATA 旧子目录的配置。
    if paths.config_path.exists():
        preserved.append(paths.config_path)
    else:
        appdata_config = _first_existing((
            paths.user_data_path / "config" / "config.json",
        ))
        legacy_config = _first_existing((
            paths.app_path / "config" / "config.json",
        ))
        default_config = _first_existing((
            paths.resource_path / "config" / "config.json",
            paths.app_path / "packaging" / "config.json",
            paths.resource_path / "packaging" / "config.json",
        ))
        config_source = appdata_config or legacy_config or default_config
        if config_source is None:
            raise FileNotFoundError("找不到 Maidie 默认配置文件，无法初始化用户数据")
        if _copy_file_if_missing(config_source, paths.config_path):
            copied.append(paths.config_path)
        else:
            preserved.append(paths.config_path)

    # APPDATA 内的旧文件名优先于安装目录中的旧数据库。
    if paths.memory_path.exists():
        preserved.append(paths.memory_path)
    else:
        memory_source = _first_existing((
            paths.user_data_path / "memories.db",
            paths.user_data_path / "memory" / "memory.db",
            paths.user_data_path / "memory" / "memories.db",
            paths.app_path / "memory" / "memory.db",
            paths.app_path / "memory" / "memories.db",
            paths.app_path / "memory.db",
        ))
        if memory_source is not None:
            copied.extend(_copy_sqlite_if_missing(memory_source, paths.memory_path))

    if paths.pet_state_path.exists():
        preserved.append(paths.pet_state_path)
    else:
        pet_state_source = _first_existing((
            paths.user_data_path / "database" / "pet_state.db",
            paths.app_path / "database" / "pet_state.db",
            paths.app_path / "pet_state.db",
        ))
        if pet_state_source is not None:
            copied.extend(_copy_sqlite_if_missing(pet_state_source, paths.pet_state_path))

    if paths.scheduled_tasks_path.exists():
        preserved.append(paths.scheduled_tasks_path)
    else:
        scheduled_source = _first_existing((
            paths.user_data_path / "memory" / "scheduled_tasks.json",
            paths.app_path / "memory" / "scheduled_tasks.json",
        ))
        if scheduled_source is not None and _copy_file_if_missing(
            scheduled_source, paths.scheduled_tasks_path
        ):
            copied.append(paths.scheduled_tasks_path)

    # 日志和皮肤逐文件补齐；同名目标始终保留 APPDATA 版本。
    copied.extend(_copy_tree_missing(paths.app_path / "logs", paths.log_path))
    copied.extend(_copy_tree_missing(paths.app_path / "skins", paths.skins_path))

    return MigrationResult(tuple(copied), tuple(preserved))
