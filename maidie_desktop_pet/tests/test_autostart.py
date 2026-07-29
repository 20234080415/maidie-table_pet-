from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from core.autostart import AutostartError, WindowsAutostartManager


class WindowsAutostartManagerTests(unittest.TestCase):
    def test_packaged_command_uses_only_executable(self):
        manager = WindowsAutostartManager(
            Path("C:/Maidie"),
            executable=Path("C:/Maidie/Maidie.exe"),
            platform="win32",
            frozen=True,
        )

        self.assertEqual(manager.command(), r"C:\Maidie\Maidie.exe")

    def test_source_command_prefers_pythonw(self):
        with tempfile.TemporaryDirectory() as root:
            project = Path(root) / "Maidie Project"
            scripts = Path(root) / "env"
            project.mkdir()
            scripts.mkdir()
            python = scripts / "python.exe"
            pythonw = scripts / "pythonw.exe"
            python.touch()
            pythonw.touch()
            manager = WindowsAutostartManager(
                project,
                executable=python,
                platform="win32",
                frozen=False,
            )

            command = manager.command()

        self.assertIn("pythonw.exe", command)
        self.assertIn("Maidie Project", command)
        self.assertIn("main.py", command)

    @patch("core.autostart.winreg")
    def test_enabling_writes_current_user_run_value(self, registry):
        registry.HKEY_CURRENT_USER = object()
        registry.KEY_SET_VALUE = 2
        registry.KEY_READ = 1
        registry.REG_SZ = 1
        writable = MagicMock()
        readable = MagicMock()
        registry.CreateKeyEx.return_value.__enter__.return_value = writable
        registry.OpenKey.return_value.__enter__.return_value = readable
        registry.QueryValueEx.return_value = (r"C:\Maidie\Maidie.exe", registry.REG_SZ)
        manager = WindowsAutostartManager(
            Path("C:/Maidie"),
            executable=Path("C:/Maidie/Maidie.exe"),
            platform="win32",
            frozen=True,
        )

        self.assertTrue(manager.set_enabled(True))
        registry.SetValueEx.assert_called_once_with(
            writable, "Maidie", 0, registry.REG_SZ, r"C:\Maidie\Maidie.exe"
        )

    @patch("core.autostart.winreg")
    def test_disabling_missing_value_is_idempotent(self, registry):
        registry.HKEY_CURRENT_USER = object()
        registry.KEY_SET_VALUE = 2
        registry.KEY_READ = 1
        registry.OpenKey.side_effect = FileNotFoundError
        manager = WindowsAutostartManager(Path("."), platform="win32")

        self.assertFalse(manager.set_enabled(False))

    def test_non_windows_platform_is_rejected(self):
        manager = WindowsAutostartManager(Path("."), platform="linux")

        self.assertFalse(manager.supported)
        with self.assertRaises(AutostartError):
            manager.set_enabled(True)


if __name__ == "__main__":
    unittest.main()
