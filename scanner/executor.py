from __future__ import annotations

import threading
import time
from datetime import datetime
import json
import numpy as np
import tifffile
import os
from pathlib import Path
from typing import Dict, Iterable, List, Optional

from camera import DualCamera
from dataio.pose_io import append_pose_row
from robot.driver import RobotDriverBase


def _write_trigger_file(trigger_path: Path, payload: Dict) -> None:
    trigger_path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = trigger_path.with_suffix(trigger_path.suffix + ".tmp")
    temp_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    temp_path.replace(trigger_path)


class AsyncImageTransfer:
    def __init__(self, camera: DualCamera, canon_dir: Optional[Path], out_dir: Path):
        self.camera = camera
        self.canon_dir = canon_dir
        self.out_dir = out_dir
        self._pending_download: Optional[tuple] = None
        self._download_thread: Optional[threading.Thread] = None
        self._download_complete = threading.Event()
        self._current_result: Optional[str] = None
        self._lock = threading.Lock()

    def start_async_download(self, canon_index: int) -> None:
        with self._lock:
            self._download_complete.clear()
            self._current_result = None

        def download_task():
            if self.canon_dir and self.camera.canon_enabled:
                canon_path = self.camera.canon.get_latest_photo(str(self.canon_dir))
                if canon_path:
                    ext = os.path.splitext(canon_path)[1]
                    new_filename = f"{canon_index:04d}{ext}"
                    new_path = self.canon_dir / new_filename
                    try:
                        if os.path.exists(canon_path):
                            os.rename(canon_path, new_path)
                            with self._lock:
                                self._current_result = str(new_path)
                    except Exception:
                        with self._lock:
                            self._current_result = canon_path
            with self._lock:
                self._download_complete.set()

        self._download_thread = threading.Thread(target=download_task, daemon=True)
        self._download_thread.start()

    def wait_for_download(self, timeout: float = 10.0) -> Optional[str]:
        self._download_complete.wait(timeout=timeout)
        with self._lock:
            return self._current_result

    def is_downloading(self) -> bool:
        return self._download_thread is not None and self._download_thread.is_alive()


def execute_scan(
    robot: RobotDriverBase,
    camera: DualCamera,
    waypoints: Iterable[Dict],
    out_dir: Path,
    speed: float = 0.05,
    settle_frames: int = 3,
    trigger_path: Path | None = None,
    canon_subdir: str = "canon",
) -> List[Dict]:
    out_dir.mkdir(parents=True, exist_ok=True)
    depth_dir = out_dir / "depth"
    depth_dir.mkdir(parents=True, exist_ok=True)

    canon_dir = None
    if camera.canon_enabled:
        canon_dir = out_dir / canon_subdir
        canon_dir.mkdir(parents=True, exist_ok=True)

    txt_path = out_dir / "poses.txt"
    if txt_path.exists():
        txt_path.unlink()

    async_transfer = AsyncImageTransfer(camera, canon_dir, out_dir)

    records: List[Dict] = []
    waypoint_list = list(waypoints)
    n = len(waypoint_list)

    prev_download_index = -1

    for i, p in enumerate(waypoint_list):
        xyz = p["xyz"]
        rpy = p["rpy"]

        robot.move_pose(xyz, rpy, speed=speed)

        if i > 0:
            prev_canon_path = async_transfer.wait_for_download(timeout=15.0)
            if prev_canon_path and prev_download_index >= 0:
                ext = os.path.splitext(prev_canon_path)[1]
                new_filename = f"{prev_download_index:04d}{ext}"
                new_path = canon_dir / new_filename
                try:
                    if os.path.exists(prev_canon_path) and prev_canon_path != str(new_path):
                        os.rename(prev_canon_path, new_path)
                        prev_canon_path = str(new_path)
                except Exception:
                    pass
                for rec in records:
                    if rec["idx"] == prev_download_index and "canon" not in rec:
                        rec["canon"] = str(Path(prev_canon_path).relative_to(out_dir)).replace("\\", "/")
                        break

        robot.wait_until_reached(timeout=20.0, pos_tol=1.0, ang_tol=1.0)

        if camera.canon_enabled and canon_dir:
            camera.canon.capture_image()

        if i < n - 1:
            async_transfer.start_async_download(i)

        canon_path = None
        if camera.canon_enabled and canon_dir:
            if i == n - 1:
                time.sleep(1)
                canon_path = camera.canon.get_latest_photo(str(canon_dir))
                if canon_path:
                    ext = os.path.splitext(canon_path)[1]
                    new_filename = f"{i:04d}{ext}"
                    new_path = canon_dir / new_filename
                    try:
                        os.rename(canon_path, new_path)
                        canon_path = str(new_path)
                    except Exception:
                        pass
            else:
                canon_path = None

        if camera.realsense_enabled and camera.realsense and not camera.realsense._use_mock:
            frames = camera.realsense.pipeline.wait_for_frames()
            aligned = camera.realsense.align.process(frames)
            depth_frame = aligned.get_depth_frame()

            depth_np = np.asanyarray(depth_frame.get_data())
            depth_path = depth_dir / f"{i:04d}.zip.tiff"
            tifffile.imwrite(depth_path, depth_np, compression="zlib")
        else:
            depth_path = None

        cur_xyz, cur_rpy = robot.get_current_pose()
        joints = robot.get_current_joints()

        row: Dict[str, object] = {
            "idx": i,
            "timestamp": datetime.now().isoformat(timespec="milliseconds"),
            "xyz": cur_xyz,
            "rpy": cur_rpy,
            "joints": joints,
        }
        if canon_path:
            row["canon"] = str(Path(canon_path).relative_to(out_dir)).replace("\\", "/")
        if depth_path:
            row["depth"] = str(depth_path.relative_to(out_dir)).replace("\\", "/")

        append_pose_row(txt_path, row)
        records.append(row)

    if trigger_path is not None:
        payload = {
            "event": "scan_completed",
            "timestamp": datetime.now().isoformat(timespec="milliseconds"),
            "out_dir": str(out_dir.resolve()),
            "poses_file": str(txt_path.resolve()),
            "records": len(records),
            "status": "ok",
        }
        _write_trigger_file(trigger_path, payload)

    return records
