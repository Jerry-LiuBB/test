from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Optional

from camera.canon import CanonEOSR100CCAPI
from camera.realsense import CameraFrame, RealSenseOrMockCamera


class DualCamera:
    def __init__(
        self,
        realsense_enabled: bool = True,
        realsense_width: int = 640,
        realsense_height: int = 480,
        realsense_fps: int = 30,
        realsense_serial: str = "",
        canon_enabled: bool = False,
        canon_ip: Optional[str] = None,
        canon_port: int = 8080,
        canon_save_dir: str = "C:/Users/dell/Pictures",
    ):
        self.realsense_enabled = realsense_enabled
        self.canon_enabled = canon_enabled
        self._capture_count = 0
        self._rs_width = realsense_width
        self._rs_height = realsense_height

        if realsense_enabled:
            self.realsense = RealSenseOrMockCamera(
                width=realsense_width,
                height=realsense_height,
                fps=realsense_fps,
                serial_number=realsense_serial,
            )
        else:
            self.realsense = None

        if canon_enabled and canon_ip:
            self.canon = CanonEOSR100CCAPI(camera_ip=canon_ip, port=canon_port)
            self.canon_save_dir = canon_save_dir
        else:
            self.canon = None
            self.canon_save_dir = None

    @property
    def use_mock(self) -> bool:
        return self.realsense.use_mock if self.realsense else True

    def capture(self) -> tuple[Optional[CameraFrame], Optional[str]]:
        frame = None
        canon_path = None

        if self.realsense:
            frame = self.realsense.capture()

        if self.canon:
            self.canon.capture_image(save_path=self.canon_save_dir)

        return frame, canon_path

    def capture_with_save(
        self,
        canon_out_dir: Path,
        frame_index: int,
    ) -> tuple[Optional[CameraFrame], Optional[Path]]:
        frame = None
        canon_path = None

        if self.realsense:
            frame = self.realsense.capture()

        if self.canon:
            self.canon.capture_image(save_path=self.canon_save_dir)
            canon_path = self.canon.get_latest_photo(save_path=str(canon_out_dir))
            if canon_path:
                ext = os.path.splitext(canon_path)[1]
                new_filename = f"{frame_index:04d}{ext}"
                new_path = canon_out_dir / new_filename
                try:
                    os.rename(canon_path, new_path)
                    canon_path = str(new_path)
                except Exception:
                    canon_path = new_path

        return frame, canon_path

    def capture_depth_raw(self, canon_out_dir: Path = None) -> tuple[Optional["np.ndarray"], Optional[str]]:
        import numpy as np
        depth_np = None
        canon_path = None

        if self.realsense and not self.realsense._use_mock:
            import pyrealsense2 as rs
            frames = self.realsense.pipeline.wait_for_frames()
            aligned = self.realsense.align.process(frames)
            depth_frame = aligned.get_depth_frame()
            if depth_frame:
                depth_np = np.asanyarray(depth_frame.get_data())

        if self.canon:
            self.canon.capture_image(save_path=self.canon_save_dir)
            time.sleep(1)
            if canon_out_dir:
                canon_path = self.canon.get_latest_photo(str(canon_out_dir))

        return depth_np, canon_path

    def close(self) -> None:
        if self.realsense:
            self.realsense.close()
