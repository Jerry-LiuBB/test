"""
RealSense D435 高精度深度采集
依赖：
  pip install pyrealsense2 numpy opencv-python tifffile
"""

import pyrealsense2 as rs
import numpy as np
import cv2
import tifffile
import datetime
import os


def main():
    pipeline = rs.pipeline()
    config = rs.config()
    config.enable_stream(rs.stream.depth, 848, 480, rs.format.z16, 30)
    config.enable_stream(rs.stream.color, 1280, 720, rs.format.bgr8, 30)

    output_dir = "depth_captures"
    os.makedirs(output_dir, exist_ok=True)

    profile = pipeline.start(config)
    device = profile.get_device()

    depth_sensor = device.first_depth_sensor()
    depth_sensor.set_option(rs.option.visual_preset, 2)
    print("[精度] 已设置为 High Accuracy 模式")

    align_to = rs.stream.color
    align = rs.align(align_to)

    colorizer = rs.colorizer()
    colorizer.set_option(rs.option.color_scheme, 0)

    print("\n相机已启动！")
    print("操作说明:")
    print("  [空格] 拍摄保存")
    print("  [q]    退出")
    print("-" * 50)

    capture_count = 0

    try:
        while True:
            frames = pipeline.wait_for_frames()
            frames = align.process(frames)

            depth_frame = frames.get_depth_frame()
            color_frame = frames.get_color_frame()

            if not depth_frame or not color_frame:
                continue

            depth_colormap = np.asanyarray(colorizer.colorize(depth_frame).get_data())
            color_image = np.asanyarray(color_frame.get_data())

            combined = np.hstack((color_image, depth_colormap))
            cv2.imshow("D435 RGB + Depth", combined)

            key = cv2.waitKey(1) & 0xFF

            if key == ord('q'):
                break

            elif key == ord(' '):
                capture_count += 1
                timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f")

                depth_data = np.asanyarray(depth_frame.get_data())
                tiff_path = os.path.join(output_dir, f"depth_{timestamp}.tiff")
                tifffile.imwrite(tiff_path, depth_data)

                valid = depth_data[depth_data > 0]
                if len(valid) > 0:
                    print(f"[{capture_count}] 保存: {tiff_path}")
                    print(f"       深度范围: {valid.min()}mm ~ {valid.max()}mm")
                else:
                    print(f"[{capture_count}] 保存: {tiff_path} (警告: 全部为0)")

    finally:
        pipeline.stop()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
