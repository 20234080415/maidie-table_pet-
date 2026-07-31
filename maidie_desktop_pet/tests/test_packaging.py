from __future__ import annotations

import json
import importlib.util
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]


def load_build_module():
    spec = importlib.util.spec_from_file_location(
        "maidie_release_build", ROOT / "scripts" / "build.py"
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class PackagingConfigurationTests(unittest.TestCase):
    def test_default_package_config_contains_no_keys(self):
        config = json.loads(
            (ROOT / "packaging" / "config.json").read_text(encoding="utf-8")
        )
        self.assertEqual(config["ai"]["api_key"], "")
        self.assertEqual(config["network"]["search_api_key"], "")
        self.assertIn("fence", config)
        self.assertIn("vision", config)

    def test_spec_collects_extensible_data_directories(self):
        spec = (ROOT / "maidie.spec").read_text(encoding="utf-8")
        self.assertIn('project_root / "assets"', spec)
        self.assertIn('project_root / "docs"', spec)
        self.assertIn('project_root / "version.json"', spec)
        self.assertIn('collect_submodules("core.plugins")', spec)
        self.assertIn('contents_directory="."', spec)
        self.assertIn("version=str(version_info_path)", spec)

    def test_build_script_uses_active_python_and_spec(self):
        script = (ROOT / "scripts" / "build.py").read_text(encoding="utf-8")
        spec = (ROOT / "maidie.spec").read_text(encoding="utf-8")
        self.assertIn('"-m",', script)
        self.assertIn('"PyInstaller"', script)
        self.assertIn('SPEC_FILE = PROJECT_ROOT / "maidie.spec"', script)
        self.assertIn("shutil.rmtree", script)
        self.assertIn("shutil.copytree", script)
        self.assertNotIn(".venv\\Scripts\\python", script)
        self.assertTrue((ROOT / "packaging" / "maidie.ico").is_file())
        self.assertIn('icon=str(project_root / "packaging" / "maidie.ico")', spec)

    def test_legacy_batch_files_are_thin_beta_compatibility_entries(self):
        for filename in ("build_exe.bat", "build_installer.bat"):
            script = (ROOT / filename).read_text(encoding="utf-8")
            self.assertIn("python scripts\\build.py beta", script)
            self.assertNotIn("PyInstaller", script)
            self.assertNotIn("ISCC", script)
            self.assertNotIn("MAIDIE_VERSION", script)

    def test_installer_preserves_user_config_and_packages_full_build(self):
        script = (ROOT / "scripts" / "build.py").read_text(encoding="utf-8")
        installer_path = ROOT / "installer" / "MaidieSetup.iss"
        installer = installer_path.read_text(encoding="utf-8")
        self.assertFalse((ROOT / "packaging" / "maidie.iss").exists())
        self.assertIn("INNO_SETUP_COMPILER", script)
        self.assertIn("/DMyAppVersion={0}", script)
        self.assertIn("/DMyAppChannel={0}", script)
        self.assertIn("/DMyAppBuild={0}", script)
        self.assertIn("/DMyAppSourceDir={0}", script)
        self.assertIn("/DMyOutputDir={0}", script)
        self.assertIn("Maidie_Setup_v{0}_{1}.exe", script)
        self.assertIn('DefaultDirName={autopf}\\Maidie', installer)
        self.assertIn("PrivilegesRequired=admin", installer)
        self.assertIn("UsePreviousAppDir=no", installer)
        self.assertIn(
            "ArchitecturesInstallIn64BitMode=x64compatible",
            installer,
        )
        self.assertIn("SetupIconFile=..\\packaging\\maidie.ico", installer)
        self.assertIn("VersionInfoVersion={#MyAppVersion}.{#MyAppBuild}", installer)
        self.assertIn("VersionInfoProductVersion={#MyAppVersion}.{#MyAppBuild}", installer)
        self.assertIn('Source: "{#MyAppSourceDir}\\*"', installer)
        self.assertIn("OutputDir={#MyOutputDir}", installer)
        self.assertIn("OutputBaseFilename={#MyOutputBaseFilename}", installer)
        self.assertIn("recursesubdirs", installer)
        self.assertIn("logs\\*,memory\\*,database\\*,skins\\*", installer)
        self.assertIn("PyQt6\\Qt6\\resources\\*.debug.pak", installer)
        self.assertIn("PyQt6\\Qt6\\resources\\*.debug.bin", installer)
        self.assertNotIn("onlyifdoesntexist", installer)
        self.assertNotIn("[Registry]", installer)
        self.assertNotIn("{userappdata}", installer)

    def test_release_names_and_channel_update_come_from_version_json(self):
        build = load_build_module()
        version = {
            "version": "0.9.0",
            "channel": "stable",
            "build": 1,
            "release_date": "2026-07-31",
        }
        self.assertEqual(
            build.release_bundle_path(version).name,
            "Maidie-v0.9.0-stable-win64",
        )
        self.assertEqual(
            build.installer_output_path(version).name,
            "Maidie_Setup_v0.9.0_stable.exe",
        )

        with tempfile.TemporaryDirectory() as root:
            version_file = Path(root) / "version.json"
            version_file.write_text(
                json.dumps({
                    "name": "Maidie",
                    "version": "0.9.0",
                    "channel": "beta",
                    "build": 1,
                    "release_date": "2026-07-31",
                }),
                encoding="utf-8",
            )
            with patch.object(build, "VERSION_FILE", version_file):
                selected = build.load_version("stable")
            saved = json.loads(version_file.read_text(encoding="utf-8"))
            self.assertEqual(selected["channel"], "stable")
            self.assertEqual(saved["channel"], "stable")

    def test_invalid_semver_produces_build_error(self):
        build = load_build_module()
        with tempfile.TemporaryDirectory() as root:
            version_file = Path(root) / "version.json"
            version_file.write_text(
                json.dumps({
                    "name": "Maidie",
                    "version": "0.9",
                    "channel": "beta",
                    "build": 1,
                    "release_date": "2026-07-31",
                }),
                encoding="utf-8",
            )
            with patch.object(build, "VERSION_FILE", version_file):
                with self.assertRaises(build.BuildError):
                    build.load_version("beta")


if __name__ == "__main__":
    unittest.main()
