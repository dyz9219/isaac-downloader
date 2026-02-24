from __future__ import annotations

import json
import shutil
import sys
import unittest
import uuid
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch

from agibot_converter.adapters.raw_to_any4 import detect_source_kind, prepare_any4_source
from agibot_converter.backend import build_options
from agibot_converter.converters import lerobot_runner
from agibot_converter.models import ConversionOptions, SourceItem, TargetKind, TaskPlan
from agibot_converter.precheck import run_precheck


def _write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


@contextmanager
def _workspace_tempdir():
    base = Path.cwd() / ".tmp-tests"
    base.mkdir(parents=True, exist_ok=True)
    path = base / f"case_{uuid.uuid4().hex[:10]}"
    path.mkdir(parents=True, exist_ok=False)
    try:
        yield str(path)
    finally:
        shutil.rmtree(path, ignore_errors=True)


class LerobotFlowTests(unittest.TestCase):
    def test_build_options_keeps_frontend_version(self) -> None:
        opts = build_options(
            input_path="in",
            output_path="out",
            target="lerobot",
            version="v2.1",
            fps="30",
            bag_type="MCAP",
            concurrency="2",
        )
        self.assertEqual(opts.lerobot_version, "v2.1")
        self.assertEqual(opts.target, TargetKind.LEROBOT)

    def test_precheck_accepts_raw_source_with_adapter_warning(self) -> None:
        with _workspace_tempdir() as td:
            root = Path(td)
            raw = root / "raw"
            raw.mkdir(parents=True, exist_ok=True)
            _write_text(raw / "state.json", "{}")
            (raw / "aligned_joints.h5").write_bytes(b"")
            (raw / "head.mp4").write_bytes(b"")

            opts = ConversionOptions(
                input_path=raw,
                output_path=root / "out",
                target=TargetKind.LEROBOT,
                lerobot_version="v3.0",
                concurrency=1,
            )

            with patch("agibot_converter.precheck.check_any4_runtime") as p_rt:
                p_rt.return_value.ok = True
                p_rt.return_value.mode = "bundled"
                p_rt.return_value.diagnostic = "ok"
                result = run_precheck(opts)

            self.assertTrue(result.ok)
            self.assertTrue(any("自动适配" in w for w in result.global_warnings))

    def test_precheck_accepts_any4_structure_for_non_hdf5(self) -> None:
        with _workspace_tempdir() as td:
            root = Path(td)
            ds = root / "dataset"
            _write_text(ds / "task_info" / "task_001.json", "{}")
            _write_text(ds / "observations" / "001" / "dummy.txt", "x")

            opts = ConversionOptions(
                input_path=ds,
                output_path=root / "out",
                target=TargetKind.LEROBOT,
                lerobot_version="v3.0",
                concurrency=1,
            )

            with patch("agibot_converter.precheck.check_any4_runtime") as p_rt:
                p_rt.return_value.ok = True
                p_rt.return_value.mode = "bundled"
                p_rt.return_value.diagnostic = "ok"
                result = run_precheck(opts)

            self.assertTrue(result.ok)
            self.assertEqual(result.ready, 1)

    def test_precheck_warns_when_output_has_stale_version_dirs(self) -> None:
        with _workspace_tempdir() as td:
            root = Path(td)
            ds = root / "dataset"
            _write_text(ds / "task_info" / "task_001.json", "{}")
            _write_text(ds / "observations" / "001" / "dummy.txt", "x")

            out_dir = root / "out" / "dataset__lerobot_v30" / "agibotworld" / "task_001_v2.1" / "meta"
            out_dir.mkdir(parents=True, exist_ok=True)
            _write_text(out_dir / "info.json", json.dumps({"codebase_version": "v2.1"}))

            opts = ConversionOptions(
                input_path=ds,
                output_path=root / "out",
                target=TargetKind.LEROBOT,
                lerobot_version="v3.0",
                concurrency=1,
                conflict_policy="overwrite",
            )

            with patch("agibot_converter.precheck.check_any4_runtime") as p_rt:
                p_rt.return_value.ok = True
                p_rt.return_value.mode = "bundled"
                p_rt.return_value.diagnostic = "ok"
                result = run_precheck(opts)

            self.assertTrue(any("残留目录" in w for w in result.global_warnings))

    def test_rosbag_precheck_mcap_requires_ros2_humble(self) -> None:
        with _workspace_tempdir() as td:
            root = Path(td)
            raw = root / "raw"
            raw.mkdir(parents=True, exist_ok=True)
            _write_text(raw / "state.json", "{}")
            (raw / "aligned_joints.h5").write_bytes(b"")
            (raw / "head.mp4").write_bytes(b"")
            opts = ConversionOptions(
                input_path=raw,
                output_path=root / "out",
                target=TargetKind.ROSBAG,
                bag_type="MCAP",
                concurrency=1,
            )

            with (
                patch("agibot_converter.precheck._has_h5py", return_value=True),
                patch("agibot_converter.precheck._has_cv2", return_value=True),
                patch(
                    "agibot_converter.precheck._module_exists",
                    side_effect=lambda name: name in {"rosbags.rosbag2"},
                ),
            ):
                result = run_precheck(opts)
            self.assertFalse(result.ok)
            self.assertTrue(any("ros2_humble" in e for e in result.global_errors))

    def test_rosbag_precheck_ros1_requires_ros1_noetic(self) -> None:
        with _workspace_tempdir() as td:
            root = Path(td)
            raw = root / "raw"
            raw.mkdir(parents=True, exist_ok=True)
            _write_text(raw / "state.json", "{}")
            (raw / "aligned_joints.h5").write_bytes(b"")
            (raw / "head.mp4").write_bytes(b"")
            opts = ConversionOptions(
                input_path=raw,
                output_path=root / "out",
                target=TargetKind.ROSBAG,
                bag_type="ROS1 .bag",
                concurrency=1,
            )

            with (
                patch("agibot_converter.precheck._has_h5py", return_value=True),
                patch("agibot_converter.precheck._has_cv2", return_value=True),
                patch(
                    "agibot_converter.precheck._module_exists",
                    side_effect=lambda name: name in {"rosbags.rosbag2"},
                ),
            ):
                result = run_precheck(opts)
            self.assertFalse(result.ok)
            self.assertTrue(any("ros1_noetic" in e for e in result.global_errors))

    def test_rosbag_precheck_passes_when_required_typestore_exists(self) -> None:
        with _workspace_tempdir() as td:
            root = Path(td)
            raw = root / "raw"
            raw.mkdir(parents=True, exist_ok=True)
            _write_text(raw / "state.json", "{}")
            (raw / "aligned_joints.h5").write_bytes(b"")
            (raw / "head.mp4").write_bytes(b"")
            opts = ConversionOptions(
                input_path=raw,
                output_path=root / "out",
                target=TargetKind.ROSBAG,
                bag_type="ROS2 .db3",
                concurrency=1,
            )

            with (
                patch("agibot_converter.precheck._has_h5py", return_value=True),
                patch("agibot_converter.precheck._has_cv2", return_value=True),
                patch(
                    "agibot_converter.precheck._module_exists",
                    side_effect=lambda name: name
                    in {"rosbags.rosbag2", "rosbags.serde.primitives", "rosbags.typesys.stores.ros2_humble"},
                ),
            ):
                result = run_precheck(opts)
            self.assertTrue(result.ok)

    def test_rosbag_precheck_requires_serde_primitives(self) -> None:
        with _workspace_tempdir() as td:
            root = Path(td)
            raw = root / "raw"
            raw.mkdir(parents=True, exist_ok=True)
            _write_text(raw / "state.json", "{}")
            (raw / "aligned_joints.h5").write_bytes(b"")
            (raw / "head.mp4").write_bytes(b"")
            opts = ConversionOptions(
                input_path=raw,
                output_path=root / "out",
                target=TargetKind.ROSBAG,
                bag_type="MCAP",
                concurrency=1,
            )

            with (
                patch("agibot_converter.precheck._has_h5py", return_value=True),
                patch("agibot_converter.precheck._has_cv2", return_value=True),
                patch(
                    "agibot_converter.precheck._module_exists",
                    side_effect=lambda name: name in {"rosbags.rosbag2", "rosbags.typesys.stores.ros2_humble"},
                ),
            ):
                result = run_precheck(opts)
            self.assertFalse(result.ok)
            self.assertTrue(any("rosbags.serde.primitives" in e for e in result.global_errors))

    def test_non_hdf5_runner_calls_any4_module(self) -> None:
        with _workspace_tempdir() as td:
            root = Path(td)
            source = root / "dataset"
            _write_text(source / "task_info" / "task_001.json", "{}")
            _write_text(source / "observations" / "001" / "dummy.txt", "x")

            task = TaskPlan(
                task_id="task_0001",
                source=SourceItem(name="dataset", source_path=source, is_zip=False),
                output_dir=root / "out",
            )
            opts = ConversionOptions(
                input_path=source,
                output_path=root / "out-base",
                target=TargetKind.LEROBOT,
                lerobot_version="v3.0",
                concurrency=1,
            )

            captured: list[list[str]] = []

            def _capture(cmd: list[str], cwd: Path) -> None:
                del cwd
                captured.append(cmd)

            with (
                patch("agibot_converter.converters.lerobot_runner.check_any4_runtime") as p_rt,
                patch("agibot_converter.converters.lerobot_runner._run_cmd", side_effect=_capture),
                patch("agibot_converter.converters.lerobot_runner._convert_generated_output_to_target_version", return_value=None),
                patch("agibot_converter.converters.lerobot_runner._validate_lerobot_output", return_value=None),
            ):
                p_rt.return_value.ok = True
                p_rt.return_value.mode = "bundled"
                p_rt.return_value.diagnostic = "ok"
                lerobot_runner.run_lerobot_task(task, opts)

            self.assertEqual(len(captured), 1)
            self.assertIn("-m", captured[0])
            self.assertIn("agibot2lerobot.agibot_h5", captured[0])

    def test_runner_uses_adapter_for_raw_source(self) -> None:
        with _workspace_tempdir() as td:
            root = Path(td)
            raw = root / "raw"
            raw.mkdir(parents=True, exist_ok=True)
            _write_text(raw / "state.json", "{}")
            (raw / "aligned_joints.h5").write_bytes(b"")
            (raw / "head.mp4").write_bytes(b"")

            task = TaskPlan(
                task_id="task_0001",
                source=SourceItem(name="raw", source_path=raw, is_zip=False),
                output_dir=root / "out",
            )
            opts = ConversionOptions(
                input_path=raw,
                output_path=root / "out-base",
                target=TargetKind.LEROBOT,
                lerobot_version="v3.0",
                concurrency=1,
            )
            with (
                patch("agibot_converter.converters.lerobot_runner.check_any4_runtime") as p_rt,
                patch("agibot_converter.converters.lerobot_runner._run_cmd", return_value=None),
                patch("agibot_converter.converters.lerobot_runner._convert_generated_output_to_target_version", return_value=None),
                patch("agibot_converter.converters.lerobot_runner._validate_lerobot_output", return_value=None),
                patch("agibot_converter.adapters.raw_to_any4._build_videos", return_value=None),
                patch("agibot_converter.adapters.raw_to_any4._build_proprio_stats", return_value=None),
            ):
                p_rt.return_value.ok = True
                p_rt.return_value.mode = "bundled"
                p_rt.return_value.diagnostic = "ok"
                lerobot_runner.run_lerobot_task(task, opts)
            self.assertEqual(task.input_kind, "raw")
            self.assertTrue(task.adapter_used)
            self.assertTrue(task.adapter_workdir == "" or not Path(task.adapter_workdir).exists())

    def test_detect_source_kind_any4_and_raw(self) -> None:
        with _workspace_tempdir() as td:
            root = Path(td)
            any4 = root / "any4"
            _write_text(any4 / "task_info" / "task_001.json", "{}")
            _write_text(any4 / "observations" / "001" / "dummy.txt", "x")
            raw = root / "raw"
            raw.mkdir(parents=True, exist_ok=True)
            _write_text(raw / "state.json", "{}")
            (raw / "aligned_joints.h5").write_bytes(b"")
            self.assertEqual(detect_source_kind(any4), "any4")
            self.assertEqual(detect_source_kind(raw), "raw")

    def test_version_conversion_chain_dispatch(self) -> None:
        with _workspace_tempdir() as td:
            root = Path(td)
            ds = root / "dataset"
            (ds / "meta").mkdir(parents=True, exist_ok=True)
            _write_text(ds / "meta" / "info.json", json.dumps({"codebase_version": "v3.0"}))

            with (
                patch("agibot_converter.converters.lerobot_runner._iter_dataset_roots", return_value=[ds]),
                patch("agibot_converter.converters.lerobot_runner._ensure_v3_stats") as p_v3,
                patch("agibot_converter.converters.lerobot_runner._convert_v30_to_v21_with_fallback") as p_30_21,
                patch("agibot_converter.converters.lerobot_runner._convert_v21_to_v20_with_fallback") as p_21_20,
            ):
                lerobot_runner._convert_generated_output_to_target_version(root, "v3.0")
                lerobot_runner._convert_generated_output_to_target_version(root, "v2.1")
                lerobot_runner._convert_generated_output_to_target_version(root, "v2.0")

            self.assertEqual(p_v3.call_count, 1)
            self.assertEqual(p_30_21.call_count, 2)
            self.assertEqual(p_21_20.call_count, 1)

    def test_version_conversion_uses_absolute_root_arg(self) -> None:
        with _workspace_tempdir() as td:
            root = Path(td)
            ds = root / "dataset"
            ds.mkdir(parents=True, exist_ok=True)
            captured: list[list[str]] = []

            def _capture(cmd: list[str], cwd: Path) -> None:
                del cwd
                captured.append(cmd)

            with (
                patch("agibot_converter.converters.lerobot_runner._require_any4_root", return_value=root),
                patch("agibot_converter.converters.lerobot_runner.find_any4_python_for_version", return_value=Path(sys.executable)),
                patch("agibot_converter.converters.lerobot_runner._run_cmd", side_effect=_capture),
            ):
                lerobot_runner._convert_v30_to_v21(ds)

            self.assertEqual(len(captured), 1)
            cmd = captured[0]
            self.assertIn("--root", cmd)
            root_value = cmd[cmd.index("--root") + 1]
            self.assertTrue(Path(root_value).is_absolute())

    def test_v30_to_v21_fallback_when_episodes_parquet_missing(self) -> None:
        with _workspace_tempdir() as td:
            root = Path(td)
            ds = root / "dataset"
            (ds / "meta").mkdir(parents=True, exist_ok=True)
            _write_text(ds / "meta" / "info.json", json.dumps({"codebase_version": "v3.0", "features": {}}))
            with patch(
                "agibot_converter.converters.lerobot_runner._convert_v30_to_v21",
                side_effect=RuntimeError("No episode parquet files found in xxx/meta/episodes"),
            ):
                lerobot_runner._convert_v30_to_v21_with_fallback(ds)
            info = json.loads((ds / "meta" / "info.json").read_text(encoding="utf-8"))
            self.assertEqual(info["codebase_version"], "v2.1")
            self.assertTrue((ds / "meta" / "episodes_stats.jsonl").exists())

    def test_v30_to_v21_fallback_when_arrow_type_error(self) -> None:
        with _workspace_tempdir() as td:
            root = Path(td)
            ds = root / "dataset"
            (ds / "meta").mkdir(parents=True, exist_ok=True)
            _write_text(ds / "meta" / "info.json", json.dumps({"codebase_version": "v3.0", "features": {}}))
            with patch(
                "agibot_converter.converters.lerobot_runner._convert_v30_to_v21",
                side_effect=RuntimeError("pyarrow.lib.ArrowTypeError: Conversion failed for column x"),
            ):
                lerobot_runner._convert_v30_to_v21_with_fallback(ds)
            info = json.loads((ds / "meta" / "info.json").read_text(encoding="utf-8"))
            self.assertEqual(info["codebase_version"], "v2.1")

    def test_v30_to_v21_fallback_cleans_partial_version_dirs(self) -> None:
        with _workspace_tempdir() as td:
            root = Path(td)
            ds = root / "dataset"
            (ds / "meta").mkdir(parents=True, exist_ok=True)
            _write_text(ds / "meta" / "info.json", json.dumps({"codebase_version": "v3.0", "features": {}}))
            partial = root / "dataset_v2.1"
            partial.mkdir(parents=True, exist_ok=True)
            with patch(
                "agibot_converter.converters.lerobot_runner._convert_v30_to_v21",
                side_effect=RuntimeError("ArrowTypeError"),
            ):
                lerobot_runner._convert_v30_to_v21_with_fallback(ds)
            self.assertFalse(partial.exists())

    def test_normalize_v21_metadata_creates_missing_files(self) -> None:
        with _workspace_tempdir() as td:
            root = Path(td) / "dataset"
            (root / "meta").mkdir(parents=True, exist_ok=True)
            lerobot_runner._normalize_v21_metadata(root)
            self.assertTrue((root / "meta" / "episodes_stats.jsonl").exists())
            self.assertTrue((root / "meta" / "episodes.jsonl").exists())

    def test_normalize_v21_metadata_keeps_existing_stats(self) -> None:
        with _workspace_tempdir() as td:
            root = Path(td) / "dataset"
            meta = root / "meta"
            meta.mkdir(parents=True, exist_ok=True)
            stats = meta / "episodes_stats.jsonl"
            stats.write_text('{"episode_index":0}\n', encoding="utf-8")
            lerobot_runner._normalize_v21_metadata(root)
            self.assertEqual(stats.read_text(encoding="utf-8"), '{"episode_index":0}\n')

    def test_adapter_compat_mode_collects_warnings(self) -> None:
        with _workspace_tempdir() as td:
            root = Path(td)
            raw = root / "raw"
            raw.mkdir(parents=True, exist_ok=True)
            _write_text(raw / "state.json", "{}")
            (raw / "aligned_joints.h5").write_bytes(b"")
            (raw / "head.mp4").write_bytes(b"")
            with patch("agibot_converter.adapters.raw_to_any4._build_proprio_stats", return_value=None):
                result = prepare_any4_source(raw, source_name="raw", work_root=root / ".w")
            self.assertTrue(result.adapter_used)
            self.assertTrue(any("缺失" in w for w in result.warnings))


if __name__ == "__main__":
    unittest.main()
