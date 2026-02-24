"""AgiBot converter UI shell using downloader-like proportions."""

from __future__ import annotations

import argparse
import importlib.util
import sys

import flet as ft

try:
    from .any4lerobot_bridge import run_any4lerobot_cli
    from .backend import ConversionBackend, build_options
    from .models import TaskStatus
except ImportError:
    from agibot_converter.any4lerobot_bridge import run_any4lerobot_cli
    from agibot_converter.backend import ConversionBackend, build_options
    from agibot_converter.models import TaskStatus

BG = "#f5f5f7"
PANEL = "#FFFFFF"
BORDER = "#E5E5E7"
TEXT = "#1D1D1F"
MUTED = "#86868B"
PRIMARY = "#007AFF"
SUCCESS = "#34C759"
ERROR = "#FF3B30"

TITLE_SIZE = 15
BODY_SIZE = 13
SUB_SIZE = 12
BADGE_SIZE = 11
FONT_FAMILY = "Microsoft YaHei UI"
WIDTH_S = 96
WIDTH_M = 146
WIDTH_L = 146

CTRL_HEIGHT = 34
BTN_HEIGHT = 34
RADIUS = 6


def _card(content: ft.Control) -> ft.Container:
    return ft.Container(
        bgcolor=PANEL,
        border_radius=8,
        border=ft.border.all(1, BORDER),
        padding=ft.padding.symmetric(horizontal=12, vertical=10),
        content=content,
    )


def _badge(label: str, color: str, bg: str) -> ft.Container:
    return ft.Container(
        bgcolor=bg,
        border_radius=10,
        padding=ft.padding.symmetric(horizontal=8, vertical=2),
        content=ft.Text(label, size=BADGE_SIZE, color=color, weight=ft.FontWeight.W_500),
    )


def _button(label: str, on_click=None, primary: bool = False) -> ft.ElevatedButton:
    return ft.ElevatedButton(
        label,
        height=BTN_HEIGHT,
        on_click=on_click,
        style=ft.ButtonStyle(
            bgcolor=PRIMARY if primary else "#E5E5E7",
            color="#FFFFFF" if primary else TEXT,
            padding=ft.padding.symmetric(horizontal=14, vertical=7),
            shape=ft.RoundedRectangleBorder(radius=RADIUS),
            text_style=ft.TextStyle(size=BODY_SIZE, weight=ft.FontWeight.W_500, font_family=FONT_FAMILY),
            side=ft.BorderSide(1, PRIMARY if primary else "#D1D1D3"),
        ),
    )


def _path_selector(title: str, value_field: ft.TextField, on_pick=None) -> ft.Column:
    return ft.Column(
        spacing=6,
        controls=[
            ft.Text(title, size=BODY_SIZE, color=TEXT, weight=ft.FontWeight.W_500),
            ft.Container(
                bgcolor=BG,
                border_radius=RADIUS,
                padding=ft.padding.symmetric(horizontal=12, vertical=8),
                content=ft.Row(
                    spacing=8,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=[
                        ft.Text("📁", size=14),
                        value_field,
                        _button("选择", on_pick),
                    ],
                ),
            ),
        ],
    )


def _task_row(
    name: str,
    status: str,
    progress: float,
    color: str,
    detail: str = "",
    expanded: bool = False,
    on_toggle=None,
) -> ft.Container:
    detail_view = (
        ft.Text(
            detail,
            size=SUB_SIZE,
            color=ERROR if status == "失败" else MUTED,
            selectable=True,
        )
        if expanded and detail
        else None
    )
    title_suffix = " ▲" if expanded and detail else (" ▼" if detail else "")
    return ft.Container(
        bgcolor=BG,
        border_radius=RADIUS,
        padding=ft.padding.symmetric(horizontal=10, vertical=8),
        on_click=on_toggle if detail else None,
        content=ft.Column(
            spacing=6,
            controls=[
                ft.Row(
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    controls=[
                        ft.Text(f"{name}{title_suffix}", size=BODY_SIZE, color=TEXT, weight=ft.FontWeight.W_500),
                        ft.Text(status, size=SUB_SIZE, color=color, weight=ft.FontWeight.W_500),
                    ],
                ),
                ft.ProgressBar(value=progress, color=PRIMARY, bgcolor="#DADCE0", bar_height=6),
                detail_view if detail_view is not None else ft.Container(visible=False),
            ],
        ),
    )


def _field(label: str, control: ft.Control) -> ft.Column:
    return ft.Column(
        spacing=6,
        expand=True,
        controls=[ft.Text(label, size=BODY_SIZE, color=TEXT, weight=ft.FontWeight.W_500), control],
    )


def _inline_labeled_field(label: str, control: ft.Control) -> ft.Row:
    return ft.Row(
        spacing=8,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
        controls=[
            ft.Text(label, size=BODY_SIZE, color=TEXT, weight=ft.FontWeight.W_500),
            control,
        ],
    )


def _uniform_input_shell(control: ft.Control, width: int) -> ft.Container:
    return ft.Container(
        width=width,
        height=CTRL_HEIGHT,
        bgcolor="#FFFFFF",
        border=ft.border.all(1, "#D1D1D3"),
        border_radius=RADIUS,
        padding=ft.padding.only(left=8, right=8, top=0, bottom=0),
        alignment=ft.Alignment(-1, 0),
        content=control,
    )


def _build(page: ft.Page) -> ft.Control:
    backend = ConversionBackend()
    state = {"target": "LeRobot", "plans": [], "expanded": set(), "show_failed_only": False}
    task_total_text = ft.Text("总进度 0%", size=SUB_SIZE, color=MUTED)
    task_rows = ft.Column(spacing=6)
    badge_text = ft.Text("0 个任务", size=BADGE_SIZE, color=MUTED, weight=ft.FontWeight.W_500)
    failed_filter_btn = ft.TextButton(
        "仅看失败: 关",
        style=ft.ButtonStyle(
            color=PRIMARY,
            text_style=ft.TextStyle(size=SUB_SIZE, weight=ft.FontWeight.W_500),
            padding=ft.padding.symmetric(horizontal=6, vertical=0),
        ),
    )
    picker = ft.FilePicker()
    page.services.append(picker)

    source = ft.TextField(
        value="",
        hint_text="未选择输入路径",
        dense=True,
        border_width=0,
        text_size=SUB_SIZE,
        read_only=True,
        expand=True,
        content_padding=ft.padding.only(left=0, right=0, top=8, bottom=8),
    )
    output = ft.TextField(
        value="",
        hint_text="未选择输出路径",
        dense=True,
        border_width=0,
        text_size=SUB_SIZE,
        read_only=True,
        expand=True,
        content_padding=ft.padding.only(left=0, right=0, top=8, bottom=8),
    )
    detect = ft.Text("待识别", size=SUB_SIZE, color=MUTED)
    preflight = ft.Text("未预检", size=SUB_SIZE, color=MUTED, weight=ft.FontWeight.W_500)

    version = ft.DropdownM2(
        value="v3.0",
        dense=True,
        height=CTRL_HEIGHT - 2,
        width=88,
        text_size=BODY_SIZE,
        border_width=0,
        content_padding=ft.padding.only(left=0, right=0, top=8, bottom=8),
        options=[
            ft.dropdownm2.Option("v3.0"),
            ft.dropdownm2.Option("v2.1"),
            ft.dropdownm2.Option("v2.0"),
            ft.dropdownm2.Option("HDF5"),
        ],
    )
    fps = ft.TextField(
        value="30",
        dense=True,
        height=CTRL_HEIGHT - 2,
        width=88,
        text_size=BODY_SIZE,
        border_width=0,
        content_padding=ft.padding.only(left=0, right=0, top=8, bottom=8),
    )
    version_shell = _uniform_input_shell(version, WIDTH_M)
    fps_shell = _uniform_input_shell(fps, WIDTH_S)

    bag_type = ft.DropdownM2(
        value="MCAP",
        dense=True,
        height=CTRL_HEIGHT - 2,
        width=112,
        text_size=BODY_SIZE,
        border_width=0,
        content_padding=ft.padding.only(left=0, right=0, top=8, bottom=8),
        options=[
            ft.dropdownm2.Option("MCAP"),
            ft.dropdownm2.Option("ROS2 .db3"),
            ft.dropdownm2.Option("ROS1 .bag"),
        ],
    )
    bag_type_shell = _uniform_input_shell(bag_type, WIDTH_M)
    bag_type.visible = False

    concurrent = ft.TextField(value="4", width=120, dense=True, height=CTRL_HEIGHT, text_size=BODY_SIZE, border_color="#D1D1D3")

    seg_left = ft.Container(width=WIDTH_L, border_radius=RADIUS, padding=ft.padding.symmetric(horizontal=14, vertical=7), alignment=ft.Alignment(0, 0))
    seg_right = ft.Container(width=WIDTH_L, border_radius=RADIUS, padding=ft.padding.symmetric(horizontal=14, vertical=7), alignment=ft.Alignment(0, 0))

    row_le = ft.Row(
        spacing=10,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
        controls=[
            _inline_labeled_field("版本", version_shell),
            _inline_labeled_field("FPS", fps_shell),
        ],
    )
    row_rb = ft.Row(spacing=10, vertical_alignment=ft.CrossAxisAlignment.CENTER, controls=[_inline_labeled_field("类型", bag_type_shell)])
    row_rb.visible = False

    def _status_view(status: TaskStatus) -> tuple[str, float, str]:
        if status is TaskStatus.RUNNING:
            return "运行中", 0.5, PRIMARY
        if status is TaskStatus.SUCCESS:
            return "完成", 1.0, SUCCESS
        if status is TaskStatus.FAILED:
            return "失败", 1.0, ERROR
        if status is TaskStatus.SKIPPED:
            return "跳过", 1.0, MUTED
        if status is TaskStatus.BLOCKED:
            return "阻断", 1.0, ERROR
        return "待执行", 0.0, MUTED

    def _refresh_task_panel() -> None:
        plans = state["plans"]
        badge_text.value = f"{len(plans)} 个任务"
        if not plans:
            task_total_text.value = "总进度 0%"
            task_rows.controls = [ft.Text("暂无任务", size=BODY_SIZE, color=MUTED, text_align=ft.TextAlign.CENTER)]
            return

        rows = []
        progress_sum = 0.0
        visible_count = 0
        for p in plans:
            if state["show_failed_only"] and p.status is not TaskStatus.FAILED:
                continue
            status_label, progress_value, status_color = _status_view(p.status)
            progress_sum += progress_value
            visible_count += 1
            detail = "; ".join(p.reasons).strip()
            is_expanded = p.task_id in state["expanded"]

            def _toggle(_: ft.ControlEvent, task_id: str = p.task_id) -> None:
                expanded = state["expanded"]
                if task_id in expanded:
                    expanded.remove(task_id)
                else:
                    expanded.add(task_id)
                _refresh_task_panel()
                page.update()

            rows.append(
                _task_row(
                    f"{p.source.name} -> {p.output_dir.name}",
                    status_label,
                    progress_value,
                    status_color,
                    detail=detail,
                    expanded=is_expanded,
                    on_toggle=_toggle,
                )
            )

        task_rows.controls = rows if rows else [ft.Text("暂无失败任务", size=BODY_SIZE, color=MUTED, text_align=ft.TextAlign.CENTER)]
        if state["show_failed_only"]:
            task_total_text.value = f"失败视图 {visible_count} 项"
        else:
            total = int((progress_sum / max(visible_count, 1)) * 100)
            task_total_text.value = f"总进度 {total}%"

    def _on_task_progress(_: object) -> None:
        _refresh_task_panel()
        page.update()

    def _toggle_failed_filter(_: ft.ControlEvent) -> None:
        state["show_failed_only"] = not state["show_failed_only"]
        failed_filter_btn.text = f"仅看失败: {'开' if state['show_failed_only'] else '关'}"
        _refresh_task_panel()
        page.update()

    failed_filter_btn.on_click = _toggle_failed_filter

    async def _pick_source(_: ft.ControlEvent) -> None:
        selected = await picker.get_directory_path(dialog_title="选择输入路径", initial_directory=source.value or None)
        if selected:
            source.value = selected
            page.update()

    async def _pick_output(_: ft.ControlEvent) -> None:
        selected = await picker.get_directory_path(dialog_title="选择输出路径", initial_directory=output.value or None)
        if selected:
            output.value = selected
            page.update()

    def _sync_target() -> None:
        is_le = state["target"] == "LeRobot"
        seg_left.bgcolor = "#EAF3FF" if is_le else PANEL
        seg_left.border = ft.border.all(1, PRIMARY if is_le else "#D1D1D3")
        seg_right.bgcolor = "#EAF3FF" if not is_le else PANEL
        seg_right.border = ft.border.all(1, PRIMARY if not is_le else "#D1D1D3")
        row_le.visible = is_le
        row_rb.visible = not is_le
        bag_type.visible = not is_le

    def _precheck(_: ft.ControlEvent) -> None:
        if not source.value.strip() or not output.value.strip():
            preflight.value = "预检失败：请先选择输入路径和输出路径"
            preflight.color = ERROR
            page.update()
            return
        preflight.value = "预检中..."
        preflight.color = PRIMARY
        page.update()

        def _work() -> None:
            opts = build_options(
                input_path=source.value,
                output_path=output.value,
                target=state["target"],
                version=version.value or "v3.0",
                fps=fps.value or "30",
                bag_type=bag_type.value or "MCAP",
                concurrency=concurrent.value or "4",
            )
            result = backend.precheck(opts)
            state["plans"] = result.tasks
            detect.value = f"识别: 就绪 {result.ready}, 跳过 {result.skipped}, 阻断 {result.blocked}"
            _refresh_task_panel()
            if result.ok:
                preflight.value = "预检通过"
                preflight.color = SUCCESS
            else:
                reason = result.global_errors[0] if result.global_errors else "无可执行任务"
                preflight.value = f"预检失败：{reason}"
                preflight.color = ERROR
            page.update()

        page.run_thread(_work)

    def _start_convert(_: ft.ControlEvent) -> None:
        if not state["plans"]:
            preflight.value = "请先预检"
            preflight.color = ERROR
            page.update()
            return
        opts = build_options(
            input_path=source.value,
            output_path=output.value,
            target=state["target"],
            version=version.value or "v3.0",
            fps=fps.value or "30",
            bag_type=bag_type.value or "MCAP",
            concurrency=concurrent.value or "4",
        )
        preflight.value = "转换中..."
        preflight.color = PRIMARY
        page.update()

        def _work() -> None:
            summary = backend.run(opts, state["plans"], on_progress=_on_task_progress)
            if summary.failed > 0:
                preflight.value = f"完成：成功 {summary.success}，失败 {summary.failed}，跳过 {summary.skipped}"
                preflight.color = ERROR
            else:
                preflight.value = f"完成：成功 {summary.success}，跳过 {summary.skipped}"
                preflight.color = SUCCESS
            _refresh_task_panel()
            page.update()

        page.run_thread(_work)

    def _choose_l(_: ft.ControlEvent) -> None:
        state["target"] = "LeRobot"
        _sync_target()
        page.update()

    def _choose_r(_: ft.ControlEvent) -> None:
        state["target"] = "Rosbag"
        _sync_target()
        page.update()

    start_btn = _button("开始转换", primary=True)
    start_btn.width = WIDTH_L
    start_btn.on_click = _start_convert
    precheck_btn = _button("预检", _precheck)
    retry_btn = _button("重试失败项")

    def _retry_failed(_: ft.ControlEvent) -> None:
        failed = [p for p in state["plans"] if p.status is TaskStatus.FAILED]
        if not failed:
            preflight.value = "无失败任务可重试"
            preflight.color = MUTED
            page.update()
            return
        for p in failed:
            p.status = TaskStatus.PENDING
            p.reasons.clear()
            p.attempts = 0
        _refresh_task_panel()
        _start_convert(_)

    retry_btn.on_click = _retry_failed

    def _close_settings() -> None:
        dlg.open = False
        page.update()

    dlg = ft.AlertDialog(
        modal=True,
        title=ft.Text("配置", size=TITLE_SIZE, color=TEXT, weight=ft.FontWeight.W_600),
        content=ft.Column(tight=True, spacing=8, controls=[ft.Text("并发任务数", size=BODY_SIZE, color=TEXT), concurrent]),
        actions=[_button("取消", lambda _: _close_settings()), _button("保存", lambda _: _close_settings(), primary=True)],
        actions_alignment=ft.MainAxisAlignment.END,
    )

    def _open_settings(_: ft.ControlEvent) -> None:
        page.dialog = dlg
        dlg.open = True
        page.update()

    seg_left.content = ft.Text("LeRobot", size=BODY_SIZE, color=TEXT, weight=ft.FontWeight.W_500)
    seg_left.on_click = _choose_l
    seg_right.content = ft.Text("Rosbag", size=BODY_SIZE, color=TEXT, weight=ft.FontWeight.W_500)
    seg_right.on_click = _choose_r
    _sync_target()

    header = ft.Container(
        bgcolor="#FFFFFF",
        border=ft.border.only(bottom=ft.BorderSide(1, BORDER)),
        padding=ft.padding.symmetric(horizontal=16, vertical=10),
        content=ft.Row(
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                ft.Row(
                    spacing=10,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=[ft.Text("文件转换器", size=TITLE_SIZE, color=TEXT, weight=ft.FontWeight.W_600), _badge_text_container(badge_text)],
                ),
                ft.IconButton(icon=ft.Icons.SETTINGS_OUTLINED, icon_size=18, on_click=_open_settings),
            ],
        ),
    )

    task_panel = _card(
        ft.Column(
            spacing=8,
            controls=[
                ft.Row(
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    controls=[
                        ft.Text("任务列表", size=BODY_SIZE, color=TEXT, weight=ft.FontWeight.W_600),
                        ft.Row(spacing=8, controls=[task_total_text, failed_filter_btn]),
                    ],
                ),
                task_rows,
            ],
        )
    )
    config_panel = _card(
        ft.Column(
            spacing=10,
            controls=[
                ft.Row(alignment=ft.MainAxisAlignment.SPACE_BETWEEN, controls=[ft.Text("转换配置", size=BODY_SIZE, color=TEXT, weight=ft.FontWeight.W_600), detect]),
                _path_selector("输入路径", source, _pick_source),
                _path_selector("输出路径", output, _pick_output),
                ft.Row(spacing=8, controls=[seg_left, seg_right]),
                row_le,
                row_rb,
                ft.Row(
                    spacing=10,
                    controls=[start_btn, precheck_btn, retry_btn],
                ),
                preflight,
            ],
        )
    )

    main_area = ft.Container(
        expand=True,
        padding=12,
        content=ft.Column(
            spacing=10,
            scroll=ft.ScrollMode.AUTO,
            controls=[config_panel, task_panel],
        ),
    )

    return ft.Column(expand=True, spacing=0, controls=[header, main_area])


def _badge_text_container(text_control: ft.Text) -> ft.Container:
    return ft.Container(
        bgcolor="#E5E5E7",
        border_radius=10,
        padding=ft.padding.symmetric(horizontal=8, vertical=2),
        content=text_control,
    )


def main(page: ft.Page) -> None:
    page.title = "AgiBot Converter"
    page.window.width = 560
    page.window.height = 800
    page.window.min_width = 480
    page.window.min_height = 600
    page.padding = 0
    page.bgcolor = BG
    page.theme_mode = ft.ThemeMode.LIGHT
    page.theme = ft.Theme(font_family=FONT_FAMILY)
    page.add(_build(page))


def _run_internal_conversion_cli(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="agibot-converter-internal")
    parser.add_argument("--input-path", required=True)
    parser.add_argument("--output-path", required=True)
    parser.add_argument("--target", default="lerobot", choices=["lerobot", "rosbag"])
    parser.add_argument("--version", default="v3.0")
    parser.add_argument("--fps", default="30")
    parser.add_argument("--bag-type", default="MCAP")
    parser.add_argument("--concurrency", default="4")
    args = parser.parse_args(argv)

    backend = ConversionBackend()
    options = build_options(
        input_path=args.input_path,
        output_path=args.output_path,
        target=args.target,
        version=args.version,
        fps=args.fps,
        bag_type=args.bag_type,
        concurrency=args.concurrency,
    )
    result = backend.precheck(options)
    if not result.ok:
        print("PRECHECK_FAILED")
        for err in result.global_errors:
            print(err)
        return 2

    summary = backend.run(options, result.tasks, on_progress=None)
    print(
        "RUN_SUMMARY",
        f"total={summary.total}",
        f"success={summary.success}",
        f"failed={summary.failed}",
        f"skipped={summary.skipped}",
    )
    return 0 if summary.failed == 0 else 1


def _run_internal_rosbag_health_cli(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="agibot-converter-rosbag-health")
    parser.add_argument("--bag-type", default="MCAP", choices=["MCAP", "ROS2 .db3", "ROS1 .bag"])
    args = parser.parse_args(argv)

    required = ["rosbags.rosbag2", "rosbags.serde.primitives"]
    if args.bag_type in {"MCAP", "ROS2 .db3"}:
        required.append("rosbags.typesys.stores.ros2_humble")
    else:
        required.append("rosbags.typesys.stores.ros1_noetic")

    missing = [name for name in required if importlib.util.find_spec(name) is None]
    if missing:
        print("ROSBAG_HEALTH_FAIL")
        print(",".join(missing))
        return 1

    print("ROSBAG_HEALTH_OK")
    print(args.bag_type)
    return 0


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--internal-run-any4lerobot":
        raise SystemExit(run_any4lerobot_cli(sys.argv[2:]))
    if len(sys.argv) > 1 and sys.argv[1] == "--internal-run-conversion":
        raise SystemExit(_run_internal_conversion_cli(sys.argv[2:]))
    if len(sys.argv) > 1 and sys.argv[1] == "--internal-run-rosbag-health":
        raise SystemExit(_run_internal_rosbag_health_cli(sys.argv[2:]))
    ft.app(target=main)
