from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from core.paths import AppPaths, initialize_user_data


class UserDataPathTests(unittest.TestCase):
    def _paths(self, root: str) -> AppPaths:
        base = Path(root)
        return AppPaths.create(
            app_path=base / "app",
            resource_path=base / "app",
            user_data_path=base / "roaming" / "Maidie",
        )

    @staticmethod
    def _write(path: Path, content: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    def test_path_layout_uses_appdata_root_and_flat_database_files(self):
        with tempfile.TemporaryDirectory() as root:
            paths = self._paths(root)

            self.assertEqual(paths.config_path, paths.user_data_path / "config.json")
            self.assertEqual(paths.log_path, paths.user_data_path / "logs")
            self.assertEqual(paths.memory_path, paths.user_data_path / "memory.db")
            self.assertEqual(paths.pet_state_path, paths.user_data_path / "pet_state.db")
            self.assertEqual(
                paths.scheduled_tasks_path,
                paths.user_data_path / "scheduled_tasks.json",
            )
            self.assertEqual(paths.skins_path, paths.user_data_path / "skins")

    def test_first_start_migrates_legacy_install_data(self):
        with tempfile.TemporaryDirectory() as root:
            paths = self._paths(root)
            self._write(paths.app_path / "config" / "config.json", "legacy-config")
            self._write(paths.app_path / "packaging" / "config.json", "default-config")
            self._write(paths.app_path / "memory" / "memories.db", "legacy-memory")
            self._write(paths.app_path / "memory" / "memories.db-wal", "legacy-wal")
            self._write(paths.app_path / "memory" / "scheduled_tasks.json", "tasks")
            self._write(paths.app_path / "database" / "pet_state.db", "pet-state")
            self._write(paths.app_path / "logs" / "maidie.log", "legacy-log")
            self._write(paths.app_path / "skins" / "custom" / "skin.json", "skin")

            result = initialize_user_data(paths)

            self.assertEqual(paths.config_path.read_text(encoding="utf-8"), "legacy-config")
            self.assertEqual(paths.memory_path.read_text(encoding="utf-8"), "legacy-memory")
            self.assertEqual(
                Path(f"{paths.memory_path}-wal").read_text(encoding="utf-8"),
                "legacy-wal",
            )
            self.assertEqual(paths.pet_state_path.read_text(encoding="utf-8"), "pet-state")
            self.assertEqual(paths.scheduled_tasks_path.read_text(encoding="utf-8"), "tasks")
            self.assertEqual(
                (paths.log_path / "maidie.log").read_text(encoding="utf-8"),
                "legacy-log",
            )
            self.assertEqual(
                (paths.skins_path / "custom" / "skin.json").read_text(encoding="utf-8"),
                "skin",
            )
            self.assertIn(paths.config_path, result.copied)

    def test_existing_appdata_files_are_never_overwritten(self):
        with tempfile.TemporaryDirectory() as root:
            paths = self._paths(root)
            self._write(paths.config_path, "user-config")
            self._write(paths.memory_path, "user-memory")
            self._write(paths.pet_state_path, "user-pet-state")
            self._write(paths.scheduled_tasks_path, "user-tasks")
            self._write(paths.log_path / "maidie.log", "user-log")
            self._write(paths.skins_path / "skin.json", "user-skin")

            self._write(paths.app_path / "config" / "config.json", "legacy-config")
            self._write(paths.app_path / "memory" / "memories.db", "legacy-memory")
            self._write(paths.app_path / "database" / "pet_state.db", "legacy-pet")
            self._write(paths.app_path / "memory" / "scheduled_tasks.json", "legacy-tasks")
            self._write(paths.app_path / "logs" / "maidie.log", "legacy-log")
            self._write(paths.app_path / "logs" / "legacy-only.log", "legacy-only")
            self._write(paths.app_path / "skins" / "skin.json", "legacy-skin")

            first = initialize_user_data(paths)
            second = initialize_user_data(paths)

            self.assertEqual(paths.config_path.read_text(encoding="utf-8"), "user-config")
            self.assertEqual(paths.memory_path.read_text(encoding="utf-8"), "user-memory")
            self.assertEqual(paths.pet_state_path.read_text(encoding="utf-8"), "user-pet-state")
            self.assertEqual(paths.scheduled_tasks_path.read_text(encoding="utf-8"), "user-tasks")
            self.assertEqual(
                (paths.log_path / "maidie.log").read_text(encoding="utf-8"),
                "user-log",
            )
            self.assertEqual(
                (paths.log_path / "legacy-only.log").read_text(encoding="utf-8"),
                "legacy-only",
            )
            self.assertEqual(
                (paths.skins_path / "skin.json").read_text(encoding="utf-8"),
                "user-skin",
            )
            self.assertEqual(first.copied, (paths.log_path / "legacy-only.log",))
            self.assertFalse(second.copied)

    def test_appdata_legacy_layout_has_priority_over_install_directory(self):
        with tempfile.TemporaryDirectory() as root:
            paths = self._paths(root)
            self._write(
                paths.user_data_path / "config" / "config.json",
                "appdata-config",
            )
            self._write(paths.user_data_path / "memories.db", "appdata-memory")
            self._write(paths.app_path / "config" / "config.json", "install-config")
            self._write(paths.app_path / "memory" / "memories.db", "install-memory")

            initialize_user_data(paths)

            self.assertEqual(paths.config_path.read_text(encoding="utf-8"), "appdata-config")
            self.assertEqual(paths.memory_path.read_text(encoding="utf-8"), "appdata-memory")

    def test_default_config_is_used_only_when_no_user_or_legacy_config_exists(self):
        with tempfile.TemporaryDirectory() as root:
            paths = self._paths(root)
            self._write(paths.app_path / "packaging" / "config.json", "default-config")

            initialize_user_data(paths)

            self.assertEqual(paths.config_path.read_text(encoding="utf-8"), "default-config")
            self.assertTrue(paths.log_path.is_dir())
            self.assertTrue(paths.skins_path.is_dir())


if __name__ == "__main__":
    unittest.main()
