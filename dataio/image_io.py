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


def save_depth_tiff(depth_u16: list[int], width: int, height: int, path: Path) -> Path:
    """Save depth as compressed .zip.tiff format."""
    try:
        import numpy as np
        import tifffile
        depth_np = np.array(depth_u16, dtype=np.uint16).reshape((height, width))
        path = path.with_suffix(".zip.tiff")
        tifffile.imwrite(path, depth_np, compression="zlib")
        return path
    except ImportError:
        import struct
        path = path.with_suffix(".pgm")
        _save_pgm16(path, width, height, depth_u16)
        return path


def _apply_colormap(depth_u16: list[int], width: int, height: int) -> bytes:
    """Apply jet colormap to depth data, return RGB bytes."""
    import numpy as np
    depth_np = np.array(depth_u16, dtype=np.float32)
    valid = depth_np > 0
    if valid.any():
        min_val = depth_np[valid].min()
        max_val = depth_np[valid].max()
        if max_val > min_val:
            normalized = (depth_np - min_val) / (max_val - min_val)
            normalized = np.clip(normalized, 0, 1)
            n = normalized * 4
            r = np.clip(np.abs(n - 3) * 3 - 1, 0, 1)
            g = np.clip(np.abs(n - 2) * 3 - 1, 0, 1)
            b = np.clip(np.abs(n - 1) * 3 - 1, 0, 1)
            r = (r * 255).astype(np.uint8)
            g = (g * 255).astype(np.uint8)
            b = (b * 255).astype(np.uint8)
            rgb = np.stack([r, g, b], axis=-1)
            return rgb.tobytes()
    return bytes(width * height * 3)


def save_depth_rgb(depth_u16: list[int], width: int, height: int, path: Path) -> Path:
    """Save depth as RGB colored image in .zip.tiff format."""
    try:
        import numpy as np
        import tifffile
        rgb_bytes = _apply_colormap(depth_u16, width, height)
        rgb_np = np.frombuffer(rgb_bytes, dtype=np.uint8).reshape((height, width, 3))
        path = path.with_suffix(".zip.tiff")
        tifffile.imwrite(path, rgb_np, compression="zlib")
        return path
    except ImportError:
        path = path.with_suffix(".ppm")
        rgb_bytes = _apply_colormap(depth_u16, width, height)
        _save_ppm(path, width, height, rgb_bytes)
        return path
