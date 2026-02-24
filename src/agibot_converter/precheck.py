from __future__ import annotations

import importlib
import re
import shutil
import zipfile
from pathlib import Path

from .any4_health import check_any4_runtime
from .discovery import discover_sources
from .models import ConversionOptions, PrecheckResult, SourceItem, TaskPlan, TaskStatus, TargetKind
from .routing import output_suffix


def run_precheck(options: ConversionOptions) -> PrecheckResult:
    errors: list[str] = []
    warnings: list[str] = []

    if not options.input_path.exists():
        errors.append(f"输入路径不存在: {options.input_path}")
    elif not _readable(options.input_path):
        errors.append(f"输入路径不可读: {options.input_path}")

    if not _ensure_writable_dir(options.output_path):
        errors.append(f"输出路径不可写: {options.output_path}")

    if options.concurrency <= 0:
        errors.append("并发数必须大于 0")

    if options.target is TargetKind.LEROBOT:
        if options.lerobot_version not in {"v3.0", "v2.1", "v2.0", "HDF5"}:
            errors.append(f"不支持的 LeRobot 版本: {options.lerobot_version}")
    else:
        if options.bag_type not in {"MCAP", "ROS2 .db3", "ROS1 .bag"}:
            errors.append(f"不支持的 Rosbag 类型: {options.bag_type}")
        ok_rb, diag_rb = _check_rosbags_runtime(options.bag_type)
        if not ok_rb:
            errors.append(f"Rosbag 依赖缺失: {diag_rb}")
        if not _has_h5py():
            errors.append("未检测到 h5py 模块，无法读取 Agibot H5 数据")
        if not _has_cv2():
            errors.append("未检测到 opencv-python 模块，无法读取 MP4 帧")

    sources = discover_sources(options.input_path) if not errors else []
    if not errors and not sources:
        errors.append("未识别到可转换数据源（支持 zip 或包含 mp4/h5/json 的目录）")
    if not errors and options.target is TargetKind.LEROBOT and options.lerobot_version != "HDF5":
        rt = check_any4_runtime(options.lerobot_version)
        if not rt.ok:
            errors.append(
                "未检测到 any4lerobot 转换依赖，无法执行当前源数据的 LeRobot 非 HDF5 转换。"
                "请安装 any4lerobot 运行依赖（ray/torch/lerobot/agibot_utils），"
                f"或切换为 HDF5 导出。诊断: {rt.diagnostic}"
            )
        else:
            warnings.append(f"LeRobot 运行时: {rt.mode}")
            has_unknown = any((not _is_any4_agibot_source(source) and not _is_agibot_raw_source(source)) for source in sources)
            has_raw = any(_is_agibot_raw_source(source) for source in sources)
            if has_unknown:
                errors.append(
                    "当前输入既不满足 any4lerobot AgiBotWorld 结构（task_info/*.json + observations/*），"
                    "也不是可适配的原始包结构（aligned_joints.h5 + state.json）。"
                )
            elif has_raw:
                warnings.append("检测到原始包输入，将自动适配为 any4 结构后再执行 LeRobot 转换。")
    if not errors and options.target is TargetKind.ROSBAG:
        if not any(_is_agibot_raw_source(source) for source in sources):
            errors.append("当前 Rosbag 直写仅支持 Agibot 原始源（含 aligned_joints.h5 + state.json）")

    tasks = _build_tasks(sources, options)
    ready = 0
    skipped = 0
    blocked = 0
    for task in tasks:
        stale_dirs = _find_stale_version_dirs(task.output_dir)
        if stale_dirs:
            details = ", ".join(str(p) for p in stale_dirs[:3])
            warnings.append(f"检测到历史版本残留目录，建议先清理输出目录: {details}")
        if task.output_dir.exists():
            if options.conflict_policy == "skip":
                task.status = TaskStatus.SKIPPED
                task.reasons.append("目标目录已存在，按策略 skip")
                skipped += 1
            else:
                task.status = TaskStatus.BLOCKED
                task.reasons.append("目标目录已存在")
                blocked += 1
        elif errors:
            task.status = TaskStatus.BLOCKED
            blocked += 1
        else:
            task.status = TaskStatus.PENDING
            ready += 1

    ok = len(errors) == 0 and ready > 0
    return PrecheckResult(
        ok=ok,
        ready=ready,
        skipped=skipped,
        blocked=blocked,
        global_errors=errors,
        global_warnings=warnings,
        tasks=tasks,
    )


def _build_tasks(sources: list[SourceItem], options: ConversionOptions) -> list[TaskPlan]:
    suffix = output_suffix(options)
    plans: list[TaskPlan] = []
    for idx, source in enumerate(sources, start=1):
        out_dir = options.output_path / f"{source.name}__{suffix}"
        plans.append(
            TaskPlan(
                task_id=f"task_{idx:04d}",
                source=source,
                output_dir=out_dir,
            )
        )
    return plans


def _readable(path: Path) -> bool:
    try:
        if path.is_file():
            with path.open("rb"):
                return True
            return False
        list(path.iterdir())
    except OSError:
        return False
    return True


def _ensure_writable_dir(path: Path) -> bool:
    try:
        path.mkdir(parents=True, exist_ok=True)
        probe = path / ".write_test"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink(missing_ok=True)
        return True
    except OSError:
        return False


def _has_rosbags() -> bool:
    try:
        return importlib.util.find_spec("rosbags.rosbag2") is not None
    except ModuleNotFoundError:
        return False


def _check_rosbags_runtime(bag_type: str) -> tuple[bool, str]:
    required: list[str] = ["rosbags.rosbag2", "rosbags.serde.primitives"]
    if bag_type in {"MCAP", "ROS2 .db3"}:
        required.append("rosbags.typesys.stores.ros2_humble")
    elif bag_type == "ROS1 .bag":
        required.append("rosbags.typesys.stores.ros1_noetic")

    missing = [name for name in required if not _module_exists(name)]
    if not missing:
        return True, f"bag_type={bag_type}"
    return False, f"bag_type={bag_type}, missing={','.join(missing)}"


def _module_exists(name: str) -> bool:
    try:
        return importlib.util.find_spec(name) is not None
    except ModuleNotFoundError:
        return False


def _has_h5py() -> bool:
    try:
        return importlib.util.find_spec("h5py") is not None
    except ModuleNotFoundError:
        return False


def _has_cv2() -> bool:
    try:
        return importlib.util.find_spec("cv2") is not None
    except ModuleNotFoundError:
        return False


def _is_agibot_raw_source(source: SourceItem) -> bool:
    path = source.source_path
    if not source.is_zip:
        return _is_agibot_raw_path(path)
    try:
        with zipfile.ZipFile(path, "r") as zf:
            names = [n.replace("\\", "/").lower() for n in zf.namelist()]
    except OSError:
        return False
    has_h5 = any(name.endswith("/aligned_joints.h5") or name == "aligned_joints.h5" for name in names)
    has_state = any(name.endswith("/state.json") or name == "state.json" for name in names)
    return has_h5 and has_state


def _is_any4_agibot_source(source: SourceItem) -> bool:
    if not source.is_zip:
        return _is_any4_agibot_path(source.source_path)
    try:
        with zipfile.ZipFile(source.source_path, "r") as zf:
            names = [n.replace("\\", "/").strip("/") for n in zf.namelist()]
    except OSError:
        return False
    has_task_info_json = any("/task_info/" in f"/{n}" and n.lower().endswith(".json") for n in names)
    has_observations = any("/observations/" in f"/{n}" for n in names)
    return has_task_info_json and has_observations


def _is_agibot_raw_path(path: Path) -> bool:
    if path.is_file():
        return False
    if (path / "aligned_joints.h5").exists() and (path / "state.json").exists():
        return True
    for h5 in path.rglob("aligned_joints.h5"):
        if (h5.parent / "state.json").exists():
            return True
    return False


def _is_any4_agibot_path(path: Path) -> bool:
    if path.is_file():
        return False
    task_info = path / "task_info"
    observations = path / "observations"
    if not task_info.exists() or not observations.exists():
        return False
    has_task_info_json = any(p.suffix.lower() == ".json" for p in task_info.glob("*.json"))
    has_observations_subdir = any(p.is_dir() for p in observations.iterdir()) if observations.exists() else False
    return has_task_info_json and has_observations_subdir


def _find_stale_version_dirs(output_dir: Path) -> list[Path]:
    if not output_dir.exists():
        return []
    stale: list[Path] = []
    for info in output_dir.rglob("meta/info.json"):
        root = info.parent.parent
        if re.search(r"_v\d+\.\d+$", root.name):
            stale.append(root)
    return sorted(set(stale))
