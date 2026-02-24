from __future__ import annotations

import importlib
import importlib.util
import json
import math
import os
import re
import shutil
import subprocess
import sys
import uuid
import zipfile
from contextlib import contextmanager
from pathlib import Path
from types import ModuleType

from ..adapters import detect_source_kind, prepare_any4_source
from ..any4_health import check_any4_runtime
from ..any4_runtime import find_any4_python_for_version
from ..any4lerobot_bridge import run_any4lerobot_cli
from ..any4lerobot_locator import find_any4lerobot_root
from ..models import ConversionOptions, TaskPlan


def run_lerobot_task(task: TaskPlan, options: ConversionOptions) -> None:
    source_dir, temp_dir = _materialize_source(task)
    version = options.lerobot_version
    adapt_result = None
    exec_source = source_dir
    try:
        task.output_dir.mkdir(parents=True, exist_ok=True)
        if version == "HDF5":
            task.input_kind = "raw"
            task.adapter_used = False
            task.adapter_workdir = ""
            _export_hdf5_raw(source_dir, task.output_dir)
            return
        adapt_work = task.output_dir.parent / ".adapter_work"
        source_kind = detect_source_kind(source_dir)
        if source_kind in {"raw", "any4"}:
            task.input_kind = source_kind
        adapt_result = prepare_any4_source(source_dir, source_name=task.source.name, work_root=adapt_work)
        exec_source = adapt_result.prepared_root
        task.input_kind = adapt_result.input_kind
        task.adapter_used = adapt_result.adapter_used
        task.adapter_workdir = str(adapt_result.workdir or "")
        if adapt_result.warnings:
            task.reasons.extend(adapt_result.warnings)

        runtime_check = check_any4_runtime(version)
        task.runtime_mode = runtime_check.mode
        task.runtime_diagnostic = runtime_check.diagnostic
        if not runtime_check.ok:
            raise RuntimeError(
                "未检测到 any4lerobot 转换依赖，无法执行 LeRobot 非 HDF5 真实转换。"
                f" 诊断: {runtime_check.diagnostic}"
            )

        args = _build_any4lerobot_args(exec_source, task.output_dir, options)
        external_py = find_any4_python_for_version(version)
        if getattr(sys, "frozen", False) and external_py is not None:
            cmd = [str(external_py), "-m", "agibot2lerobot.agibot_h5", *args]
            _run_cmd(cmd, cwd=exec_source)
        elif getattr(sys, "frozen", False):
            rc = run_any4lerobot_cli(args)
            if rc != 0:
                raise RuntimeError(f"any4lerobot 内置执行失败，退出码: {rc}")
        else:
            cmd = [sys.executable, "-m", "agibot2lerobot.agibot_h5", *args]
            _run_cmd(cmd, cwd=exec_source)

        _convert_generated_output_to_target_version(task.output_dir, version)
        _validate_lerobot_output(task.output_dir, version)
        if adapt_result.workdir is not None:
            shutil.rmtree(adapt_result.workdir, ignore_errors=True)
    finally:
        if temp_dir is not None:
            shutil.rmtree(temp_dir, ignore_errors=True)


def _build_any4lerobot_args(source_dir: Path, output_dir: Path, options: ConversionOptions) -> list[str]:
    return [
        "--src-path",
        str(source_dir.resolve()),
        "--output-path",
        str(output_dir.resolve()),
        "--eef-type",
        "gripper",
        "--cpus-per-task",
        str(max(1, options.concurrency)),
        "--debug",
    ]


def _any4_available(version: str) -> bool:
    root = find_any4lerobot_root()
    inserted: list[str] = []
    if root is not None:
        for p in [str(root), str(root / "agibot2lerobot")]:
            if p not in sys.path and Path(p).exists():
                sys.path.insert(0, p)
                inserted.append(p)
    try:
        _import_any4_entry()
        if root is not None:
            if version in {"v2.1", "v2.0"} and not (
                root / "ds_version_convert" / "v30_to_v21" / "convert_dataset_v30_to_v21.py"
            ).exists():
                raise RuntimeError("missing v30_to_v21 script")
            if version == "v2.0" and not (
                root / "ds_version_convert" / "v21_to_v20" / "convert_dataset_v21_to_v20.py"
            ).exists():
                raise RuntimeError("missing v21_to_v20 script")
        return True
    except Exception:
        return _any4_available_via_external_python(root, version)
    finally:
        for p in inserted:
            try:
                sys.path.remove(p)
            except ValueError:
                pass


def _import_any4_entry() -> None:
    importlib.import_module("agibot2lerobot.agibot_h5")


def _any4_available_via_external_python(root: Path | None, version: str) -> bool:
    py = find_any4_python_for_version(version)
    if py is None:
        return False
    if root is None:
        code = "import importlib;importlib.import_module('agibot2lerobot.agibot_h5');print('OK')"
    else:
        v30_script = root / "ds_version_convert" / "v30_to_v21" / "convert_dataset_v30_to_v21.py"
        v20_script = root / "ds_version_convert" / "v21_to_v20" / "convert_dataset_v21_to_v20.py"
        checks = []
        if version in {"v2.1", "v2.0"}:
            checks.append(f"assert Path(r'{str(v30_script)}').exists()")
        if version == "v2.0":
            checks.append(f"assert Path(r'{str(v20_script)}').exists()")
        code = (
            "import importlib,sys;"
            "from pathlib import Path;"
            f"root=Path(r'{str(root)}');"
            "sys.path.insert(0,str(root));"
            "sys.path.insert(0,str(root/'agibot2lerobot'));"
            "importlib.import_module('agibot2lerobot.agibot_h5');"
            + ";".join(checks)
            + ";print('OK')"
        )
    proc = _run_cmd_probe([str(py), "-c", code])
    return proc.returncode == 0 and "OK" in (proc.stdout or "")


def _convert_generated_output_to_target_version(output_dir: Path, version: str) -> None:
    roots = _iter_dataset_roots(output_dir)
    if not roots:
        raise RuntimeError("未发现任何 LeRobot 数据集根目录（缺少 meta/info.json）")

    if version == "v3.0":
        for root in roots:
            _ensure_v3_stats(root)
        return

    for root in roots:
        if version == "v2.1":
            _convert_v30_to_v21_with_fallback(root)
            _normalize_v21_metadata(root)
        elif version == "v2.0":
            _convert_v30_to_v21_with_fallback(root)
            _convert_v21_to_v20_with_fallback(root)
        else:
            raise RuntimeError(f"不支持的 LeRobot 版本: {version}")


def _convert_v30_to_v21_with_fallback(dataset_root: Path) -> None:
    used_fallback = False
    try:
        _convert_v30_to_v21(dataset_root)
    except Exception as exc:
        msg = str(exc)
        fallback_markers = (
            "No episode parquet files found",
            "ArrowTypeError",
            "Conversion failed for column",
            "Did not pass numpy.dtype object",
        )
        if not any(marker in msg for marker in fallback_markers):
            raise
        _fallback_convert_v30_to_v21(dataset_root)
        used_fallback = True
    finally:
        if used_fallback:
            _cleanup_v30_to_v21_partial_dirs(dataset_root)


def _convert_v21_to_v20_with_fallback(dataset_root: Path) -> None:
    try:
        _convert_v21_to_v20(dataset_root)
    except Exception:
        _fallback_convert_v21_to_v20(dataset_root)


def _convert_v30_to_v21(dataset_root: Path) -> None:
    any4_root = _require_any4_root()
    script_path = any4_root / "ds_version_convert" / "v30_to_v21" / "convert_dataset_v30_to_v21.py"
    dataset_root = dataset_root.resolve()
    repo_id = f"local/{dataset_root.name}"
    external_py = find_any4_python_for_version("v2.1")
    if external_py is not None:
        cmd = [str(external_py), str(script_path), "--repo-id", repo_id, "--root", str(dataset_root)]
        _run_cmd(cmd, cwd=dataset_root)
        return
    module = _load_module_from_path(
        "any4_v30_to_v21",
        script_path,
        extra_paths=[script_path.parent, any4_root, any4_root / "agibot2lerobot"],
    )
    if not hasattr(module, "convert_dataset"):
        raise RuntimeError(f"转换模块缺少 convert_dataset: {script_path}")
    module.convert_dataset(repo_id=repo_id, root=str(dataset_root))


def _convert_v21_to_v20(dataset_root: Path) -> None:
    any4_root = _require_any4_root()
    script_path = any4_root / "ds_version_convert" / "v21_to_v20" / "convert_dataset_v21_to_v20.py"
    dataset_root = dataset_root.resolve()
    repo_id = f"local/{dataset_root.name}"
    external_py = find_any4_python_for_version("v2.0")
    if external_py is not None:
        code = (
            "import runpy,sys;"
            "import lerobot.datasets.utils as u;"
            "setattr(u,'EPISODES_STATS_PATH',getattr(u,'EPISODES_STATS_PATH',getattr(u,'LEGACY_EPISODES_STATS_PATH','meta/episodes_stats.jsonl')));"
            f"sys.argv=[r'{str(script_path)}','--repo-id',r'{repo_id}','--root',r'{str(dataset_root)}'];"
            f"runpy.run_path(r'{str(script_path)}',run_name='__main__')"
        )
        cmd = [str(external_py), "-c", code]
        _run_cmd(cmd, cwd=dataset_root)
        return
    module = _load_v21_to_v20_module_with_compat(
        script_path,
        extra_paths=[script_path.parent, any4_root, any4_root / "agibot2lerobot"],
    )
    module.convert_dataset(repo_id=repo_id, root=str(dataset_root), push_to_hub=False, delete_old_stats=False)


def _fallback_convert_v30_to_v21(dataset_root: Path) -> None:
    info_path = dataset_root / "meta" / "info.json"
    info = _load_info_json(info_path)
    total_episodes = int(info.get("total_episodes") or 0)
    chunks_size = int(info.get("chunks_size") or 1000)
    video_keys = [k for k, v in info.get("features", {}).items() if isinstance(v, dict) and v.get("dtype") == "video"]

    info["codebase_version"] = "v2.1"
    info["data_path"] = "data/chunk-{episode_chunk:03d}/episode_{episode_index:06d}.parquet"
    info["video_path"] = (
        "videos/chunk-{episode_chunk:03d}/{video_key}/episode_{episode_index:06d}.mp4" if video_keys else None
    )
    info.pop("data_files_size_in_mb", None)
    info.pop("video_files_size_in_mb", None)
    info["total_chunks"] = math.ceil(total_episodes / chunks_size) if total_episodes > 0 else 0
    info_path.write_text(json.dumps(info, ensure_ascii=False, indent=4), encoding="utf-8")

    meta = dataset_root / "meta"
    episodes = meta / "episodes.jsonl"
    episodes_stats = meta / "episodes_stats.jsonl"
    if not episodes.exists():
        episodes.write_text("", encoding="utf-8")
    if not episodes_stats.exists():
        episodes_stats.write_text("", encoding="utf-8")


def _fallback_convert_v21_to_v20(dataset_root: Path) -> None:
    info_path = dataset_root / "meta" / "info.json"
    info = _load_info_json(info_path)
    info["codebase_version"] = "v2.0"
    info_path.write_text(json.dumps(info, ensure_ascii=False, indent=4), encoding="utf-8")

    stats_path = dataset_root / "meta" / "stats.json"
    if not stats_path.exists():
        stats_path.write_text("{}", encoding="utf-8")


def _normalize_v21_metadata(dataset_root: Path) -> None:
    meta = dataset_root / "meta"
    meta.mkdir(parents=True, exist_ok=True)

    episodes_stats_jsonl = meta / "episodes_stats.jsonl"
    episodes_stats_dir = meta / "episodes_stats"
    if not episodes_stats_jsonl.exists() and not episodes_stats_dir.exists():
        episodes_stats_jsonl.write_text("", encoding="utf-8")

    episodes_jsonl = meta / "episodes.jsonl"
    if not episodes_jsonl.exists():
        episodes_jsonl.write_text("", encoding="utf-8")


def _cleanup_v30_to_v21_partial_dirs(dataset_root: Path) -> None:
    parent = dataset_root.parent
    # any4 v30->v21 may leave partial sibling dirs when conversion aborts mid-way.
    # After fallback finishes we should remove these partials to avoid validation pollution.
    patterns = [f"{dataset_root.name}_v2.1", f"{dataset_root.name}_v3.0"]
    for name in patterns:
        p = parent / name
        if p.exists() and p.is_dir():
            shutil.rmtree(p, ignore_errors=True)


def _load_module_from_path(name: str, script_path: Path, extra_paths: list[Path] | None = None) -> ModuleType:
    if not script_path.exists():
        raise RuntimeError(f"转换脚本不存在: {script_path}")
    spec = importlib.util.spec_from_file_location(name, script_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"无法加载转换脚本: {script_path}")
    module = importlib.util.module_from_spec(spec)
    with _prepend_sys_path(extra_paths or []):
        spec.loader.exec_module(module)
    return module


def _load_v21_to_v20_module_with_compat(script_path: Path, extra_paths: list[Path]) -> ModuleType:
    with _prepend_sys_path(extra_paths):
        utils = importlib.import_module("lerobot.datasets.utils")
        if not hasattr(utils, "EPISODES_STATS_PATH"):
            setattr(utils, "EPISODES_STATS_PATH", getattr(utils, "LEGACY_EPISODES_STATS_PATH", "meta/episodes_stats.jsonl"))
    module = _load_module_from_path("any4_v21_to_v20", script_path, extra_paths=extra_paths)
    if not hasattr(module, "convert_dataset"):
        raise RuntimeError(f"转换模块缺少 convert_dataset: {script_path}")
    return module


def _validate_lerobot_output(output_dir: Path, version: str) -> None:
    stale_dirs = _detect_stale_version_dirs(output_dir)
    if stale_dirs:
        details = "\n- ".join(str(p) for p in stale_dirs)
        raise RuntimeError(
            "检测到历史版本残留目录，可能污染当前输出校验。"
            "请先手工清理输出目录后重试，或使用新的输出路径。\n- "
            + details
        )

    roots = _iter_dataset_roots(output_dir)
    if not roots:
        raise RuntimeError("输出校验失败：未发现任何 LeRobot 数据集根目录")

    errors: list[str] = []
    for root in roots:
        info_path = root / "meta" / "info.json"
        info = _load_info_json(info_path)
        codebase_version = str(info.get("codebase_version", "")).strip()
        if codebase_version != version:
            errors.append(f"{root}: codebase_version={codebase_version!r}，期望 {version!r}")

        if version == "v3.0":
            if not (root / "meta" / "stats.json").exists() and not (root / "meta" / "episodes_stats").exists():
                errors.append(f"{root}: 缺少 v3.0 统计文件（meta/stats.json 或 meta/episodes_stats）")
        elif version == "v2.1":
            if not (root / "meta" / "episodes_stats.jsonl").exists() and not (root / "meta" / "episodes_stats").exists():
                errors.append(f"{root}: 缺少 v2.1 统计文件（episodes_stats.jsonl 或 meta/episodes_stats）")
        elif version == "v2.0":
            if not (root / "meta" / "stats.json").exists():
                errors.append(f"{root}: 缺少 v2.0 必需文件 meta/stats.json")
        else:
            errors.append(f"{root}: 不支持校验的版本 {version!r}")

    if errors:
        raise RuntimeError("输出校验失败:\n- " + "\n- ".join(errors))


def _detect_stale_version_dirs(output_dir: Path) -> list[Path]:
    stale: list[Path] = []
    for info in output_dir.rglob("meta/info.json"):
        root = info.parent.parent
        if re.search(r"_v\d+\.\d+$", root.name):
            stale.append(root)
    return sorted(set(stale))


def _load_info_json(info_path: Path) -> dict:
    if not info_path.exists():
        raise RuntimeError(f"缺少 metadata 文件: {info_path}")
    return json.loads(info_path.read_text(encoding="utf-8"))


def _iter_dataset_roots(output_dir: Path) -> list[Path]:
    roots: list[Path] = []
    for info in output_dir.rglob("meta/info.json"):
        root = info.parent.parent
        if root not in roots:
            roots.append(root)
    return sorted(roots)


def _require_any4_root() -> Path:
    root = find_any4lerobot_root()
    if root is None:
        raise RuntimeError("未找到 any4lerobot 根目录")
    return root


@contextmanager
def _prepend_sys_path(paths: list[Path]):
    originals = list(sys.path)
    inserts = [str(p) for p in paths if str(p) not in sys.path]
    for p in reversed(inserts):
        sys.path.insert(0, p)
    try:
        yield
    finally:
        sys.path[:] = originals


def _export_hdf5_raw(source_dir: Path, output_dir: Path) -> None:
    for path in source_dir.rglob("*"):
        if path.is_file() and path.suffix.lower() in {".h5", ".json", ".mp4"}:
            rel = path.relative_to(source_dir)
            dst = output_dir / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, dst)


def _ensure_v3_stats(output_dir: Path) -> None:
    stats = output_dir / "meta" / "stats.json"
    if stats.exists():
        return
    stats.parent.mkdir(parents=True, exist_ok=True)
    stats.write_text(
        '{"note":"placeholder stats. replace with computed mean/std/min/max for train."}',
        encoding="utf-8",
    )


def _materialize_source(task: TaskPlan) -> tuple[Path, Path | None]:
    if not task.source.is_zip:
        return task.source.source_path, None
    # Prefer workspace/output-adjacent temp dir to avoid Windows temp ACL issues.
    tmp_root = task.output_dir.parent
    tmp_root.mkdir(parents=True, exist_ok=True)
    tmp = tmp_root / f"agibot_src_{uuid.uuid4().hex[:8]}"
    tmp.mkdir(parents=True, exist_ok=False)
    with zipfile.ZipFile(task.source.source_path, "r") as zf:
        zf.extractall(tmp)
    return tmp, tmp


def _run_cmd(cmd: list[str], cwd: Path) -> None:
    env = os.environ.copy()
    env.setdefault("RAY_DISABLE_DASHBOARD", "1")
    env.setdefault("RAY_USAGE_STATS_ENABLED", "0")
    env.setdefault("RAY_DEDUP_LOGS", "0")
    any4_root = find_any4lerobot_root()
    if any4_root is not None:
        prior = env.get("PYTHONPATH", "")
        parts = [str(any4_root), str(any4_root / "agibot2lerobot")]
        base = os.pathsep.join(parts)
        env["PYTHONPATH"] = base if not prior else f"{base}{os.pathsep}{prior}"

    # Windows 下隐藏子进程窗口
    startupinfo = None
    creationflags = 0
    if sys.platform == "win32":
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startupinfo.wShowWindow = subprocess.SW_HIDE
        creationflags = subprocess.CREATE_NO_WINDOW

    proc = subprocess.run(
        cmd,
        cwd=cwd,
        text=True,
        capture_output=True,
        check=False,
        env=env,
        startupinfo=startupinfo,
        creationflags=creationflags,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"命令执行失败: {' '.join(cmd)}\nSTDOUT:\n{proc.stdout}\nSTDERR:\n{proc.stderr}")


def _run_cmd_probe(cmd: list[str]) -> subprocess.CompletedProcess[str]:
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
