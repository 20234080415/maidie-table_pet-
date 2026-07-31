from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from core.version import VERSION_INFO, load_version_info


ROOT = Path(__file__).resolve().parents[1]


class VersionFileTests(unittest.TestCase):
    def test_root_version_file_is_the_loaded_source(self):
        payload = json.loads((ROOT / "version.json").read_text(encoding="utf-8"))
        self.assertEqual(VERSION_INFO.name, payload["name"])
        self.assertEqual(VERSION_INFO.version, payload["version"])
        self.assertEqual(VERSION_INFO.channel, payload["channel"])
        self.assertEqual(VERSION_INFO.build, payload["build"])
        self.assertEqual(VERSION_INFO.release_date, payload["release_date"])

    def test_version_helpers_format_release_information(self):
        self.assertEqual(VERSION_INFO.semver_parts, (0, 9, 0))
        self.assertEqual(VERSION_INFO.version_label, "v0.9.0")
        self.assertEqual(VERSION_INFO.channel_label, "Beta")
        self.assertEqual(VERSION_INFO.full_version, "0.9.0-beta (Build 1)")

    def test_invalid_semver_channel_and_build_are_rejected(self):
        invalid_values = (
            {"version": "0.9", "channel": "beta", "build": 1},
            {"version": "0.9.0", "channel": "dev", "build": 1},
            {"version": "0.9.0", "channel": "stable", "build": True},
        )
        for overrides in invalid_values:
            with self.subTest(overrides=overrides), tempfile.TemporaryDirectory() as root:
                payload = {
                    "name": "Maidie",
                    "version": "0.9.0",
                    "channel": "beta",
                    "build": 1,
                    "release_date": "2026-07-31",
                    **overrides,
                }
                path = Path(root) / "version.json"
                path.write_text(json.dumps(payload), encoding="utf-8")
                with self.assertRaises(ValueError):
                    load_version_info(path)


if __name__ == "__main__":
    unittest.main()
