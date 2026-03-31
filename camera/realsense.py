from __future__ import annotations

from dataclasses import dataclass
from typing import List


@dataclass
class CameraFrame:
    width: int
    height: int
    color_rgb: bytes  # 8-bit RGB, row-major, 3 channels
    depth_u16: List[int]  # row-major


class RealSenseOrMockCamera:
    """Uses RealSense if available; otherwise generates synthetic frames."""

    def __init__(
        self,
        width: int = 640,
        height: int = 480,
        fps: int = 30,
        serial_number: str = "",
    ):
        self.width = width
        self.height = height
        self.fps = fps
        self._use_mock = False
        self._frame_idx = 0

        try:
            import pyrealsense2 as rs  # type: ignore
            import numpy as np  # type: ignore

            self.rs = rs
            self.np = np
            self.pipeline = rs.pipeline()
            cfg = rs.config()
            if serial_number:
                cfg.enable_device(serial_number)
            cfg.enable_stream(rs.stream.color, width, height, rs.format.rgb8, fps)
            cfg.enable_stream(rs.stream.depth, width, height, rs.format.z16, fps)
            self.pipeline.start(cfg)
            self.align = rs.align(rs.stream.color)
        except Exception:
            self._use_mock = True

    @property
    def use_mock(self) -> bool:
        return self._use_mock

    def capture(self) -> CameraFrame:
        self._frame_idx += 1

        if self._use_mock:
            color = bytearray(self.width * self.height * 3)
            depth: List[int] = [0] * (self.width * self.height)
            idx = 0
            for y in range(self.height):
                for x in range(self.width):
                    r = x % 256
                    g = y % 256
                    b = (x // 2 + y // 2 + self._frame_idx) % 256
                    color[idx] = r
                    color[idx + 1] = g
                    color[idx + 2] = b
                    idx += 3
                    depth[y * self.width + x] = 1000 + x * 2 + self._frame_idx
            return CameraFrame(self.width, self.height, bytes(color), depth)

        frames = self.pipeline.wait_for_frames()
        aligned = self.align.process(frames)
        color_frame = aligned.get_color_frame()
        depth_frame = aligned.get_depth_frame()

        color_np = self.np.asanyarray(color_frame.get_data())
        depth_np = self.np.asanyarray(depth_frame.get_data())
        return CameraFrame(
            width=self.width,
            height=self.height,
            color_rgb=color_np.tobytes(),
            depth_u16=depth_np.astype(self.np.uint16).ravel().tolist(),
        )

    def close(self) -> None:
        if not self._use_mock:
            self.pipeline.stop()
