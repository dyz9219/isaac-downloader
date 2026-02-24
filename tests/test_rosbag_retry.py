from __future__ import annotations

import shutil
import unittest
import uuid
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch

from agibot_converter.backend import ConversionBackend
from agibot_converter.models import ConversionOptions, SourceItem, TargetKind, TaskPlan


@contextmanager
def _workspace_tempdir():
    base = Path.cwd() / ".tmp-tests"
    base.mkdir(parents=True, exist_ok=True)
    path = base / f"case_{uuid.uuid4().hex[:10]}"
    path.mkdir(parents=True, exist_ok=False)
    try:
        yield path
    finally:
        shutil.rmtree(path, ignore_errors=True)


class RosbagRetryTests(unittest.TestCase):
    def test_retry_cleans_partial_ros2_output(self) -> None:
        with _workspace_tempdir() as root:
            plan = TaskPlan(
                task_id="task_0001",
                source=SourceItem(name="s", source_path=root, is_zip=False),
                output_dir=root / "out",
            )
            opts = ConversionOptions(
                input_path=root,
                output_path=root / "out_root",
                target=TargetKind.ROSBAG,
                bag_type="MCAP",
                concurrency=1,
                retry_limit=1,
            )
            calls = {"n": 0}

            def _flaky(task: TaskPlan, options: ConversionOptions) -> None:
                del options
                calls["n"] += 1
                if calls["n"] == 1:
                    d = task.output_dir / "ros2_output"
                    d.mkdir(parents=True, exist_ok=True)
                    (d / "metadata.yaml").write_text("x", encoding="utf-8")
                    raise RuntimeError("first failure")
                self.assertFalse((task.output_dir / "ros2_output").exists())

            with patch("agibot_converter.backend.run_rosbag_task", side_effect=_flaky):
                ConversionBackend()._run_task(plan, opts)

            self.assertEqual(calls["n"], 2)
            self.assertEqual(plan.attempts, 1)

    def test_retry_preserves_first_error_context(self) -> None:
        with _workspace_tempdir() as root:
            plan = TaskPlan(
                task_id="task_0001",
                source=SourceItem(name="s", source_path=root, is_zip=False),
                output_dir=root / "out",
            )
            opts = ConversionOptions(
                input_path=root,
                output_path=root / "out_root",
                target=TargetKind.ROSBAG,
                bag_type="MCAP",
                concurrency=1,
                retry_limit=1,
            )
            with patch(
                "agibot_converter.backend.run_rosbag_task",
                side_effect=[RuntimeError("first failure"), RuntimeError("exists already, not overwriting")],
            ):
                with self.assertRaises(RuntimeError) as ctx:
                    ConversionBackend()._run_task(plan, opts)
            msg = str(ctx.exception)
            self.assertIn("首次失败: first failure", msg)
            self.assertIn("重试失败: exists already, not overwriting", msg)


if __name__ == "__main__":
    unittest.main()

