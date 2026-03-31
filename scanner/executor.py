from __future__ import annotations

from datetime import datetime
import json
import numpy as np
import tifffile
import os
from pathlib import Path
from typing import Dict, Iterable, List

from camera import DualCamera
from dataio.pose_io import append_pose_row
from robot.driver import RobotDriverBase


def _write_trigger_file(trigger_path: Path, payload: Dict) -> None:
    trigger_path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = trigger_path.with_suffix(trigger_path.suffix + ".tmp")
    temp_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    temp_path.replace(trigger_path)


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

    records: List[Dict] = []
    for i, p in enumerate(waypoints):
        xyz = p["xyz"]
        rpy = p["rpy"]
        robot.move_pose(xyz, rpy, speed=speed)
        if not robot.wait_until_reached(timeout=20.0, pos_tol=1.0, ang_tol=1.0):
            continue

        canon_path = None
        if camera.canon_enabled and canon_dir:
            camera.canon.capture_image()
            import time
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
