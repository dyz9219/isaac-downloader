from __future__ import annotations

import shutil
import tempfile
import zipfile
from pathlib import Path

import cv2

from ..models import ConversionOptions, TaskPlan
from ..rosbag import HighLevelRosbagWriter, RosMessageMapper, load_agibot_dataset


def run_rosbag_task(task: TaskPlan, options: ConversionOptions) -> None:
    source_dir, temp_dir = _materialize_source(task)
    try:
        dataset = load_agibot_dataset(source_dir, fps_fallback=float(options.fps))
        frame_count = dataset.joint_position.shape[0]
        mapper: RosMessageMapper

        with HighLevelRosbagWriter(task.output_dir, options.bag_type) as writer:
            mapper = RosMessageMapper(writer.typestore)
            joint_topic = mapper.joint_topic()
            joint_msgtype = "sensor_msgs/msg/JointState"
            joint_conn = writer.add_topic(joint_topic, joint_msgtype)

            camera_conns: dict[str, tuple[object, cv2.VideoCapture]] = {}
            for camera_name, video_path in dataset.camera_videos.items():
                topic = mapper.image_topic(camera_name)
                conn = writer.add_topic(topic, "sensor_msgs/msg/Image")
                cap = cv2.VideoCapture(str(video_path))
                if not cap.isOpened():
                    continue
                camera_conns[camera_name] = (conn, cap)

            try:
                for idx in range(frame_count):
                    ts_ns = _to_unix_ns(float(dataset.timestamps[idx]), idx, dataset.fps)
                    joint_msg = mapper.build_joint_state(
                        timestamp_ns=ts_ns,
                        sequence=idx,
                        joint_names=dataset.joint_names,
                        position=dataset.joint_position[idx],
                        velocity=dataset.joint_velocity[idx],
                        effort=dataset.joint_effort[idx],
                    )
                    writer.write_message(joint_conn, joint_msg, ts_ns, joint_msgtype)

                    for camera_name, (conn, cap) in camera_conns.items():
                        ok, frame = cap.read()
                        if not ok:
                            continue
                        image_msg = mapper.build_image(ts_ns, idx, camera_name, frame)
                        writer.write_message(conn, image_msg, ts_ns, "sensor_msgs/msg/Image")
            finally:
                for _, cap in camera_conns.values():
                    cap.release()
    finally:
        if temp_dir is not None:
            shutil.rmtree(temp_dir, ignore_errors=True)


def _materialize_source(task: TaskPlan) -> tuple[Path, Path | None]:
    if not task.source.is_zip:
        return task.source.source_path, None
    tmp = Path(tempfile.mkdtemp(prefix="agibot_src_"))
    with zipfile.ZipFile(task.source.source_path, "r") as zf:
        zf.extractall(tmp)
    return tmp, tmp


def _to_unix_ns(raw_timestamp: float, index: int, fps: float) -> int:
    if raw_timestamp <= 0:
        return int((index / max(fps, 1.0)) * 1_000_000_000)
    if raw_timestamp >= 1e15:
        return int(raw_timestamp)
    if raw_timestamp >= 1e12:
        return int(raw_timestamp * 1_000)
    if raw_timestamp >= 1e9:
        return int(raw_timestamp * 1_000_000)
    return int(raw_timestamp * 1_000_000_000)
