from __future__ import annotations

from dataclasses import dataclass
from dataclasses import field
from typing import Any

import numpy as np


@dataclass(slots=True)
class RosMessageMapper:
    typestore: Any
    frame_prefix: str = "agibot"
    _header: Any = field(init=False, repr=False)
    _time: Any = field(init=False, repr=False)
    _joint: Any = field(init=False, repr=False)
    _image: Any = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self._header = self.typestore.types["std_msgs/msg/Header"]
        self._time = self.typestore.types["builtin_interfaces/msg/Time"]
        self._joint = self.typestore.types["sensor_msgs/msg/JointState"]
        self._image = self.typestore.types["sensor_msgs/msg/Image"]

    def build_joint_state(
        self,
        timestamp_ns: int,
        sequence: int,
        joint_names: list[str],
        position: np.ndarray,
        velocity: np.ndarray,
        effort: np.ndarray,
    ) -> Any:
        header = self._build_header(timestamp_ns, f"{self.frame_prefix}_base", sequence)
        return self._joint(
            header=header,
            name=joint_names,
            position=np.asarray(position, dtype=np.float64),
            velocity=np.asarray(velocity, dtype=np.float64),
            effort=np.asarray(effort, dtype=np.float64),
        )

    def build_image(self, timestamp_ns: int, sequence: int, camera_name: str, frame_bgr: np.ndarray) -> Any:
        if frame_bgr.ndim != 3 or frame_bgr.shape[2] != 3:
            raise ValueError(f"图像帧格式错误: {frame_bgr.shape}")
        height, width, channels = frame_bgr.shape
        header = self._build_header(timestamp_ns, f"{self.frame_prefix}_cam_{camera_name}", sequence)
        return self._image(
            header=header,
            height=int(height),
            width=int(width),
            encoding="bgr8",
            is_bigendian=0,
            step=int(width * channels),
            data=np.asarray(frame_bgr, dtype=np.uint8).reshape(-1),
        )

    @staticmethod
    def joint_topic(prefix: str = "agibot") -> str:
        return f"/{prefix}/joint_states"

    @staticmethod
    def image_topic(camera_name: str, prefix: str = "agibot") -> str:
        return f"/{prefix}/camera/{camera_name}/image_raw"

    def _to_time(self, timestamp_ns: int) -> Any:
        sec = int(timestamp_ns // 1_000_000_000)
        nanosec = int(timestamp_ns % 1_000_000_000)
        return self._time(sec=sec, nanosec=nanosec)

    def _build_header(self, timestamp_ns: int, frame_id: str, sequence: int) -> Any:
        stamp = self._to_time(timestamp_ns)
        try:
            return self._header(seq=int(sequence), stamp=stamp, frame_id=frame_id)
        except TypeError:
            return self._header(stamp=stamp, frame_id=frame_id)
