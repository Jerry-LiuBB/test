from __future__ import annotations

from pathlib import Path
import struct

from camera.realsense import CameraFrame


def _save_ppm(path: Path, width: int, height: int, color_rgb: bytes) -> None:
    with path.open("wb") as f:
        f.write(f"P6\n{width} {height}\n255\n".encode("ascii"))
        f.write(color_rgb)


def _save_pgm16(path: Path, width: int, height: int, depth_u16: list[int]) -> None:
    with path.open("wb") as f:
        f.write(f"P5\n{width} {height}\n65535\n".encode("ascii"))
        for v in depth_u16:
            f.write(struct.pack(">H", max(0, min(65535, int(v)))))


def save_frame(frame: CameraFrame, rgb_path: Path, depth_path: Path) -> tuple[Path, Path]:
    """Save frame without mandatory third-party deps. Returns actual paths used."""
    rgb_path = rgb_path.with_suffix(".ppm")
    depth_path = depth_path.with_suffix(".pgm")
    _save_ppm(rgb_path, frame.width, frame.height, frame.color_rgb)
    _save_pgm16(depth_path, frame.width, frame.height, frame.depth_u16)
    return rgb_path, depth_path
