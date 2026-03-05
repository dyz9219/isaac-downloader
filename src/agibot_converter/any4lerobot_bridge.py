from __future__ import annotations

import argparse
import importlib
import sys
import traceback
from contextlib import redirect_stderr, redirect_stdout
from dataclasses import dataclass
from io import StringIO
from pathlib import Path

from .any4lerobot_locator import find_any4lerobot_root


@dataclass(slots=True)
class Any4RunResult:
    returncode: int
    error: str = ""
    stdout: str = ""
    stderr: str = ""


def run_any4lerobot_cli_result(argv: list[str]) -> Any4RunResult:
    out_buf = StringIO()
    err_buf = StringIO()

    def _combine(detail: str) -> str:
        stdout = out_buf.getvalue().strip()
        stderr = err_buf.getvalue().strip()
        parts = [detail]
        if stdout:
            parts.append(f"STDOUT:\n{stdout}")
        if stderr:
            parts.append(f"STDERR:\n{stderr}")
        return "\n\n".join(parts)

    root = find_any4lerobot_root()
    if root is not None:
        sys.path.insert(0, str(root))
        # Also add agibot2lerobot directory for direct imports like agibot_utils
        agibot2lerobot_dir = root / "agibot2lerobot"
        if agibot2lerobot_dir.exists():
            sys.path.insert(0, str(agibot2lerobot_dir))

    try:
        with redirect_stdout(out_buf), redirect_stderr(err_buf):
            agibot_h5 = importlib.import_module("agibot2lerobot.agibot_h5")
    except Exception as exc:
        detail = _combine(f"加载 any4lerobot 失败: {exc}\n{traceback.format_exc()}")
        print(detail, file=sys.stderr)
        return Any4RunResult(
            returncode=2,
            error=detail,
            stdout=out_buf.getvalue(),
            stderr=err_buf.getvalue(),
        )

    parser = argparse.ArgumentParser(prog="any4lerobot", add_help=True)
    parser.add_argument("--src-path", type=Path, required=True)
    parser.add_argument("--output-path", type=Path, required=True)
    parser.add_argument("--eef-type", type=str, choices=["gripper", "dexhand", "tactile"], default="gripper")
    parser.add_argument("--task-ids", type=str, nargs="+", default=[])
    parser.add_argument("--cpus-per-task", type=int, default=3)
    parser.add_argument("--save-depth", action="store_true")
    parser.add_argument("--debug", action="store_true")
    args = parser.parse_args(argv)

    try:
        with redirect_stdout(out_buf), redirect_stderr(err_buf):
            agibot_h5.main(**vars(args))
        return Any4RunResult(returncode=0, stdout=out_buf.getvalue(), stderr=err_buf.getvalue())
    except Exception as exc:
        detail = _combine(f"any4lerobot 执行失败: {exc}\n{traceback.format_exc()}")
        print(detail, file=sys.stderr)
        return Any4RunResult(
            returncode=1,
            error=detail,
            stdout=out_buf.getvalue(),
            stderr=err_buf.getvalue(),
        )


def run_any4lerobot_cli(argv: list[str]) -> int:
    return run_any4lerobot_cli_result(argv).returncode
