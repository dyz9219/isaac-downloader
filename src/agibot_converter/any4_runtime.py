from __future__ import annotations

import os
import sys
from pathlib import Path


def _resolve_env_python(name: str) -> Path | None:
    env_py = os.environ.get(name, "").strip()
    if env_py:
        p = Path(env_py).expanduser()
        if p.exists():
            return p
    return None


def _get_venv_python(base_path: Path) -> Path:
    """Get the Python executable path for a virtual environment, handling platform differences."""
    if sys.platform == "win32":
        return base_path / ".venv" / "Scripts" / "python.exe"
    else:
        return base_path / ".venv" / "bin" / "python"


def find_any4_python() -> Path | None:
    p = _resolve_env_python("ANY4LEROBOT_PYTHON")
    if p is not None:
        return p

    candidates: list[Path] = []
    if getattr(sys, "frozen", False):
        exe_dir = Path(sys.executable).resolve().parent
        current = exe_dir
        for _ in range(6):
            candidates.append(_get_venv_python(current))
            current = current.parent
    else:
        repo_root = Path(__file__).resolve().parents[1]
        candidates.append(_get_venv_python(repo_root))

    cwd = Path.cwd().resolve()
    candidates.append(_get_venv_python(cwd))
    candidates.append(_get_venv_python(cwd.parent))

    seen: set[Path] = set()
    for candidate in candidates:
        resolved = candidate.resolve()
        if resolved in seen:
            continue
        seen.add(resolved)
        if resolved.exists():
            return resolved
    return None


def find_any4_python_for_version(version: str) -> Path | None:
    if version == "v2.0":
        p = _resolve_env_python("ANY4_RUNTIME_V21_PYTHON")
        if p is not None:
            return p
    elif version in {"v2.1", "v3.0"}:
        p = _resolve_env_python("ANY4_RUNTIME_V30_PYTHON")
        if p is not None:
            return p
    return find_any4_python()
