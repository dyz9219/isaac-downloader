from __future__ import annotations

import argparse
import importlib
import sys
from pathlib import Path

from .any4lerobot_locator import find_any4lerobot_root


def run_any4lerobot_cli(argv: list[str]) -> int:
    root = find_any4lerobot_root()
    if root is not None:
        sys.path.insert(0, str(root))
        # Also add agibot2lerobot directory for direct imports like agibot_utils
        agibot2lerobot_dir = root / "agibot2lerobot"
        if agibot2lerobot_dir.exists():
            sys.path.insert(0, str(agibot2lerobot_dir))

    try:
        agibot_h5 = importlib.import_module("agibot2lerobot.agibot_h5")
    except Exception as exc:
        print(f"加载 any4lerobot 失败: {exc}", file=sys.stderr)
        return 2

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
        agibot_h5.main(**vars(args))
        return 0
    except Exception as exc:
        print(f"any4lerobot 执行失败: {exc}", file=sys.stderr)
        return 1
