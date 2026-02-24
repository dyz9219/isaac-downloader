from __future__ import annotations

import unittest
from pathlib import Path
from unittest.mock import patch

from agibot_converter.any4_health import RuntimeCheckResult, check_any4_runtime


class Any4HealthTests(unittest.TestCase):
    def test_check_any4_runtime_uses_external_when_bundled_fails(self) -> None:
        with (
            patch.dict("agibot_converter.any4_health._CACHE", {}, clear=True),
            patch("agibot_converter.any4_health.find_any4lerobot_root", return_value=Path.cwd()),
            patch("agibot_converter.any4_health._check_bundled_runtime") as p_bundled,
            patch("agibot_converter.any4_health._check_external_runtime") as p_ext,
        ):
            p_bundled.return_value = RuntimeCheckResult(
                ok=False,
                mode="bundled",
                root=str(Path.cwd()),
                python="",
                missing=["agibot2lerobot_import"],
                diagnostic="bundled failed",
            )
            p_ext.return_value = RuntimeCheckResult(
                ok=True,
                mode="external",
                root=str(Path.cwd()),
                python="py",
                missing=[],
                diagnostic="external ok",
            )
            rt = check_any4_runtime("v3.0")
            self.assertTrue(rt.ok)
            self.assertEqual(rt.mode, "external")
            self.assertTrue(p_ext.called)


if __name__ == "__main__":
    unittest.main()
