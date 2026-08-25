"""Regression tests for dq_check.py's fail-closed configuration handling."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).with_name("dq_check.py")


class DataQualityGateTests(unittest.TestCase):
    def run_gate(self, config_value: object) -> subprocess.CompletedProcess[str]:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            data = root / "data.csv"
            config = root / "config.json"
            data.write_text("id\n1\n", encoding="utf-8")
            config.write_text(json.dumps(config_value), encoding="utf-8")
            return subprocess.run(
                [sys.executable, str(SCRIPT), "--data", str(data), "--config", str(config)],
                capture_output=True,
                text=True,
                check=False,
            )

    def test_non_mapping_configs_are_errors(self) -> None:
        for value in ([], None):
            with self.subTest(value=value):
                result = self.run_gate(value)
                self.assertEqual(result.returncode, 3, result.stderr)
                self.assertIn("config root must be an object/mapping", result.stderr)

    def test_empty_mapping_with_nonempty_csv_passes(self) -> None:
        result = self.run_gate({})
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["verdict"], "PASS")


if __name__ == "__main__":
    unittest.main()
