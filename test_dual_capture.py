"""
Dual Camera Capture: Canon + RealSense D435
Canon images saved to config.py save_dir
RealSense depth saved as colored PNG (848x480)
"""

import pyrealsense2 as rs
import numpy as np
import cv2
import os
import time
from pathlib import Path
from config import CanonConfig, OutputConfig


def main():
    canon_config = CanonConfig()
    output_config = OutputConfig()

    save_dir = Path(canon_config.save_dir)
    save_dir.mkdir(parents=True, exist_ok=True)

    pipeline = rs.pipeline()
    config = rs.config()
    config.enable_stream(rs.stream.depth, 848, 480, rs.format.z16, 30)
    config.enable_stream(rs.stream.color, 1280, 720, rs.format.bgr8, 30)

    profile = pipeline.start(config)
    device = profile.get_device()
    depth_sensor = device.first_depth_sensor()
    depth_sensor.set_option(rs.option.visual_preset, 2)

    align_to = rs.stream.color
    align = rs.align(align_to)

    colorizer = rs.colorizer()
    colorizer.set_option(rs.option.color_scheme, 0)

    canon_camera = None
    if canon_config.enabled:
        from camera.canon import CanonEOSR100CCAPI
        canon_camera = CanonEOSR100CCAPI(camera_ip=canon_config.camera_ip, port=canon_config.port)

    print(f"Canon enabled: {canon_config.enabled}")
    print(f"Save directory: {save_dir}")
    print(f"Starting 5 captures...")

    try:
        for i in range(5):
            print(f"\n--- Capture {i+1}/5 ---")

            if canon_camera:
                canon_camera.capture_image()
                time.sleep(1)
                canon_path = canon_camera.get_latest_photo(str(save_dir))
                if canon_path:
                    print(f"Canon image saved: {canon_path}")

            frames = pipeline.wait_for_frames()
            frames = align.process(frames)
            depth_frame = frames.get_depth_frame()

            depth_colormap = np.asanyarray(colorizer.colorize(depth_frame).get_data())
            depth_path = save_dir / f"{i:04d}.png"
            cv2.imwrite(str(depth_path), depth_colormap)
            print(f"RealSense depth saved: {depth_path}")

    finally:
        pipeline.stop()
        print("\nDone.")


if __name__ == "__main__":
    main()
