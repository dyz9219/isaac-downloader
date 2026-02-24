from __future__ import annotations

import json
import shutil
import unittest
import uuid
from contextlib import contextmanager
from pathlib import Path

import h5py
import numpy as np

from agibot_converter.converters.lerobot_runner import _validate_lerobot_output
from agibot_converter.converters import lerobot_runner


HDF5_SIGNATURE = b"\x89HDF\r\n\x1a\n"


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


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


class FormatContractTests(unittest.TestCase):
    def test_v30_contract(self) -> None:
        with _workspace_tempdir() as td:
            out = Path(td)
            root = out / "dataset"
            _write_json(root / "meta" / "info.json", {"codebase_version": "v3.0"})
            _write_json(root / "meta" / "stats.json", {"ok": True})
            _validate_lerobot_output(out, "v3.0")

    def test_v21_contract(self) -> None:
        with _workspace_tempdir() as td:
            out = Path(td)
            root = out / "dataset"
            _write_json(root / "meta" / "info.json", {"codebase_version": "v2.1"})
            (root / "meta").mkdir(parents=True, exist_ok=True)
            (root / "meta" / "episodes_stats.jsonl").write_text('{"episode_index":0}\n', encoding="utf-8")
            _validate_lerobot_output(out, "v2.1")

    def test_v21_contract_passes_after_normalize(self) -> None:
        with _workspace_tempdir() as td:
            out = Path(td)
            root = out / "dataset"
            _write_json(root / "meta" / "info.json", {"codebase_version": "v2.1"})
            with self.assertRaises(RuntimeError):
                _validate_lerobot_output(out, "v2.1")
            lerobot_runner._normalize_v21_metadata(root)
            _validate_lerobot_output(out, "v2.1")

    def test_v20_contract(self) -> None:
        with _workspace_tempdir() as td:
            out = Path(td)
            root = out / "dataset"
            _write_json(root / "meta" / "info.json", {"codebase_version": "v2.0"})
            _write_json(root / "meta" / "stats.json", {"ok": True})
            _validate_lerobot_output(out, "v2.0")

    def test_version_mismatch_fails(self) -> None:
        with _workspace_tempdir() as td:
            out = Path(td)
            root = out / "dataset"
            _write_json(root / "meta" / "info.json", {"codebase_version": "v3.0"})
            _write_json(root / "meta" / "stats.json", {"ok": True})
            with self.assertRaises(RuntimeError):
                _validate_lerobot_output(out, "v2.0")

    def test_v21_stale_version_dir_fails_with_clear_error(self) -> None:
        with _workspace_tempdir() as td:
            out = Path(td)
            root = out / "dataset_v2.1"
            _write_json(root / "meta" / "info.json", {"codebase_version": "v2.1"})
            (root / "meta" / "episodes_stats.jsonl").write_text("", encoding="utf-8")
            with self.assertRaises(RuntimeError) as ctx:
                _validate_lerobot_output(out, "v2.1")
            self.assertIn("历史版本残留目录", str(ctx.exception))

    def test_hdf5_signature_and_readability(self) -> None:
        with _workspace_tempdir() as td:
            h5_path = Path(td) / "aligned_joints.h5"
            with h5py.File(h5_path, "w") as h5f:
                g = h5f.create_group("joints")
                g.create_dataset("qpos", data=np.zeros((4, 7), dtype=np.float32))

            header = h5_path.read_bytes()[:8]
            self.assertEqual(header, HDF5_SIGNATURE)

            with h5py.File(h5_path, "r") as h5f:
                self.assertIn("joints", h5f.keys())
                arr = h5f["joints"]["qpos"][...]
                self.assertEqual(arr.shape, (4, 7))


if __name__ == "__main__":
    unittest.main()
