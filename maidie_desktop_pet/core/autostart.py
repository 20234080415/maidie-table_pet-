"""Windows current-user login startup integration for Maidie.

The registry operation is isolated from configuration and UI code so it can be
validated independently and stays optional on non-Windows platforms.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

try:
    import winreg
except ImportError:  # pragma: no cover - exercised on non-Windows hosts.
    winreg = None  # type: ignore[assignment]


class AutostartError(RuntimeError):
    """Raised when the requested login-startup state cannot be applied."""


class WindowsAutostartManager:
    RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
    VALUE_NAME = "Maidie"

    def __init__(
        self,
        project_root: Path,
        *,
        executable: Path | None = None,
        platform: str | None = None,
        frozen: bool | None = None,
    ) -> None:
        self.project_root = Path(project_root).resolve()
        self.executable = Path(executable or sys.executable).resolve()
        self.platform = platform or sys.platform
        self.frozen = bool(getattr(sys, "frozen", False) if frozen is None else frozen)

    @property
    def supported(self) -> bool:
        return self.platform == "win32" and winreg is not None

    def command(self) -> str:
        if self.frozen:
            parts = [str(self.executable)]
        else:
            interpreter = self.executable
            if interpreter.name.lower() == "python.exe":
                pythonw = interpreter.with_name("pythonw.exe")
                if pythonw.exists():
                    interpreter = pythonw
            parts = [str(interpreter), str(self.project_root / "main.py")]
        return subprocess.list2cmdline(parts)

    def is_enabled(self) -> bool:
        if not self.supported:
            return False
        try:
            with winreg.OpenKey(  # type: ignore[union-attr]
                winreg.HKEY_CURRENT_USER, self.RUN_KEY, 0, winreg.KEY_READ
            ) as key:
                value, _value_type = winreg.QueryValueEx(key, self.VALUE_NAME)
                return bool(str(value).strip())
        except FileNotFoundError:
            return False
        except OSError as exc:
            raise AutostartError(f"无法读取 Windows 自启动状态：{exc}") from exc

    def set_enabled(self, enabled: bool) -> bool:
        if not self.supported:
            raise AutostartError("开机自启动仅支持 Windows。")
        try:
            if enabled:
                with winreg.CreateKeyEx(  # type: ignore[union-attr]
                    winreg.HKEY_CURRENT_USER,
                    self.RUN_KEY,
                    0,
                    winreg.KEY_SET_VALUE,
                ) as key:
                    winreg.SetValueEx(
                        key, self.VALUE_NAME, 0, winreg.REG_SZ, self.command()
                    )
            else:
                try:
                    with winreg.OpenKey(  # type: ignore[union-attr]
                        winreg.HKEY_CURRENT_USER,
                        self.RUN_KEY,
                        0,
                        winreg.KEY_SET_VALUE,
                    ) as key:
                        winreg.DeleteValue(key, self.VALUE_NAME)
                except FileNotFoundError:
                    pass
            return self.is_enabled()
        except AutostartError:
            raise
        except OSError as exc:
            action = "启用" if enabled else "关闭"
            raise AutostartError(f"{action}开机自启动失败：{exc}") from exc
