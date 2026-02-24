from __future__ import annotations

from concurrent.futures import Future, ThreadPoolExecutor, as_completed
from dataclasses import dataclass
import shutil
from pathlib import Path
from typing import Callable

from .converters.lerobot_runner import run_lerobot_task
from .converters.rosbag_runner import run_rosbag_task
from .manifest import write_manifest
from .models import ConversionOptions, PrecheckResult, TargetKind, TaskPlan, TaskStatus
from .precheck import run_precheck


ProgressCallback = Callable[[TaskPlan], None]


@dataclass(slots=True)
class RunSummary:
    total: int
    success: int
    failed: int
    skipped: int


class ConversionBackend:
    def precheck(self, options: ConversionOptions) -> PrecheckResult:
        return run_precheck(options)

    def run(
        self,
        options: ConversionOptions,
        plans: list[TaskPlan],
        on_progress: ProgressCallback | None = None,
    ) -> RunSummary:
        runnable = [p for p in plans if p.status is TaskStatus.PENDING]
        skipped = len([p for p in plans if p.status is TaskStatus.SKIPPED])
        success = 0
        failed = 0

        if not runnable:
            return RunSummary(total=len(plans), success=0, failed=0, skipped=skipped)

        max_workers = max(1, options.concurrency)
        # any4lerobot uses Ray multiprocessing internally. Running multiple any4 jobs
        # in parallel from the shell causes resource contention and multiple app windows
        # in frozen builds, so keep one outer worker for this route.
        if options.target is TargetKind.LEROBOT and options.lerobot_version != "HDF5":
            max_workers = 1

        with ThreadPoolExecutor(max_workers=max_workers) as pool:
            futures: dict[Future[None], TaskPlan] = {pool.submit(self._run_task, p, options): p for p in runnable}
            for future in as_completed(futures):
                task = futures[future]
                try:
                    future.result()
                    task.status = TaskStatus.SUCCESS
                    success += 1
                    write_manifest(task, options, status=TaskStatus.SUCCESS.value)
                except Exception as exc:  # noqa: BLE001
                    task.status = TaskStatus.FAILED
                    task.reasons.append(str(exc))
                    details = getattr(exc, "issues", None)
                    if isinstance(details, list):
                        task.error_details = [str(x) for x in details]
                    failed += 1
                    write_manifest(task, options, status=TaskStatus.FAILED.value, error=str(exc))
                if on_progress is not None:
                    on_progress(task)

        return RunSummary(total=len(plans), success=success, failed=failed, skipped=skipped)

    def _run_task(self, plan: TaskPlan, options: ConversionOptions) -> None:
        plan.status = TaskStatus.RUNNING
        max_retries = 0 if options.target is TargetKind.LEROBOT else options.retry_limit
        first_exc: Exception | None = None
        while True:
            try:
                if options.target is TargetKind.LEROBOT:
                    run_lerobot_task(plan, options)
                else:
                    run_rosbag_task(plan, options)
                return
            except Exception as exc:  # noqa: BLE001
                if first_exc is None:
                    first_exc = exc
                plan.attempts += 1
                if plan.attempts > max_retries:
                    if first_exc is not None and first_exc is not exc:
                        raise RuntimeError(f"首次失败: {first_exc}\n重试失败: {exc}") from exc
                    raise
                if options.target is TargetKind.ROSBAG:
                    _cleanup_rosbag_partial_outputs(plan.output_dir)


def _cleanup_rosbag_partial_outputs(output_dir: Path) -> None:
    ros2_output = output_dir / "ros2_output"
    if ros2_output.exists():
        shutil.rmtree(ros2_output, ignore_errors=True)
    ros1_output = output_dir / "ros1_output.bag"
    if ros1_output.exists():
        ros1_output.unlink(missing_ok=True)


def build_options(
    *,
    input_path: str,
    output_path: str,
    target: str,
    version: str,
    fps: str,
    bag_type: str,
    concurrency: str,
) -> ConversionOptions:
    target_kind = TargetKind.LEROBOT if target.lower() == "lerobot" else TargetKind.ROSBAG
    fps_value = int(fps) if fps.strip().isdigit() else 30
    conc_value = int(concurrency) if concurrency.strip().isdigit() else 4
    return ConversionOptions(
        input_path=Path(input_path),
        output_path=Path(output_path),
        target=target_kind,
        lerobot_version=version,
        fps=fps_value,
        bag_type=bag_type,
        concurrency=conc_value,
    )
