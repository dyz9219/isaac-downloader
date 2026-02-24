from __future__ import annotations

import importlib
import importlib.util
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path

from .any4_runtime import find_any4_python_for_version
from .any4lerobot_locator import find_any4lerobot_root

_TTL_SECONDS = 300.0
_CACHE: dict[tuple[str, str, str], tuple[float, "RuntimeCheckResult"]] = {}


@dataclass(slots=True)
class RuntimeCheckResult:
    ok: bool
    mode: str
    root: str
    python: str
    missing: list[str]
    diagnostic: str


def check_any4_runtime(version: str) -> RuntimeCheckResult:
    root = find_any4lerobot_root()
    py = find_any4_python_for_version(version)
    cache_key = (
        version,
        str(root.resolve()) if root is not None else "",
        str(py.resolve()) if py is not None else "",
    )
    now = time.monotonic()
    cached = _CACHE.get(cache_key)
    if cached is not None and now - cached[0] < _TTL_SECONDS:
        return cached[1]

    result = _check_bundled_runtime(version, root)
    if not result.ok:
        result = _check_external_runtime(version, root, py)
    _CACHE[cache_key] = (now, result)
    return result


def _check_bundled_runtime(version: str, root: Path | None) -> RuntimeCheckResult:
    missing: list[str] = []
    if root is None:
        missing.append("any4_root")
        return _result(False, "none", root, None, missing)

    inserted: list[str] = []
    try:
        for p in [str(root), str(root / "agibot2lerobot")]:
            if p not in sys.path and Path(p).exists():
                sys.path.insert(0, p)
                inserted.append(p)
        importlib.import_module("agibot2lerobot.agibot_h5")
        _check_version_scripts(version, root, missing)
        if missing:
            return _result(False, "bundled", root, None, missing)
        return _result(True, "bundled", root, None, [])
    except Exception:
        missing.append("agibot2lerobot_import")
        return _result(False, "bundled", root, None, missing)
    finally:
        for p in inserted:
            try:
                sys.path.remove(p)
            except ValueError:
                pass


def _check_external_runtime(version: str, root: Path | None, py: Path | None) -> RuntimeCheckResult:
    missing: list[str] = []
    if py is None:
        missing.append("python")
        return _result(False, "none", root, py, missing)

    code_parts = [
        "import importlib,sys",
        "from pathlib import Path",
    ]
    if root is not None:
        code_parts += [
            f"root=Path(r'{str(root)}')",
            "sys.path.insert(0,str(root))",
            "sys.path.insert(0,str(root/'agibot2lerobot'))",
        ]
    code_parts.append("importlib.import_module('agibot2lerobot.agibot_h5')")
    if root is not None and version in {"v2.1", "v2.0"}:
        code_parts.append(
            f"assert Path(r'{str(root / 'ds_version_convert' / 'v30_to_v21' / 'convert_dataset_v30_to_v21.py')}').exists()"
        )
    if root is not None and version == "v2.0":
        code_parts.append(
            f"assert Path(r'{str(root / 'ds_version_convert' / 'v21_to_v20' / 'convert_dataset_v21_to_v20.py')}').exists()"
        )
    code_parts.append("print('OK')")
    code = ";".join(code_parts)

    proc = _run_hidden_subprocess([str(py), "-c", code])
    if proc.returncode == 0 and "OK" in (proc.stdout or ""):
        return _result(True, "external", root, py, [])
    missing.append("external_probe_failed")
    return _result(False, "none", root, py, missing)


def _check_version_scripts(version: str, root: Path, missing: list[str]) -> None:
    if version in {"v2.1", "v2.0"} and not (
        root / "ds_version_convert" / "v30_to_v21" / "convert_dataset_v30_to_v21.py"
    ).exists():
        missing.append("v30_to_v21_script")
    if version == "v2.0" and not (
        root / "ds_version_convert" / "v21_to_v20" / "convert_dataset_v21_to_v20.py"
    ).exists():
        missing.append("v21_to_v20_script")


def _result(ok: bool, mode: str, root: Path | None, py: Path | None, missing: list[str]) -> RuntimeCheckResult:
    root_text = str(root) if root is not None else ""
    py_text = str(py) if py is not None else ""
    if ok:
        diagnostic = f"mode={mode}; root={root_text}; python={py_text}"
    else:
        diagnostic = f"mode={mode}; root={root_text}; python={py_text}; missing={','.join(missing)}"
    return RuntimeCheckResult(
        ok=ok,
        mode=mode,
        root=root_text,
        python=py_text,
        missing=missing,
        diagnostic=diagnostic,
    )


def _run_hidden_subprocess(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    startupinfo = None
    creationflags = 0
    if sys.platform == "win32":
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startupinfo.wShowWindow = subprocess.SW_HIDE
        creationflags = subprocess.CREATE_NO_WINDOW
    return subprocess.run(
        cmd,
        text=True,
        capture_output=True,
        check=False,
        startupinfo=startupinfo,
        creationflags=creationflags,
    )

