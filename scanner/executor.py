from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List

from camera.realsense import RealSenseOrMockCamera
from dataio.image_io import save_frame
from dataio.pose_io import append_pose_row
from robot.driver import RobotDriverBase


def execute_scan(
    robot: RobotDriverBase,
    camera: RealSenseOrMockCamera,
    waypoints: Iterable[Dict],
    out_dir: Path,
    speed: float = 0.05,
    settle_frames: int = 3,
) -> List[Dict]:
    out_dir.mkdir(parents=True, exist_ok=True)
    rgb_dir = out_dir / "rgb"
    depth_dir = out_dir / "depth"
    rgb_dir.mkdir(parents=True, exist_ok=True)
    depth_dir.mkdir(parents=True, exist_ok=True)

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

        frame = None
        for _ in range(max(settle_frames, 1)):
            frame = camera.capture()

        assert frame is not None
        rgb_rel = Path("rgb") / f"{i:04d}.ppm"
        depth_rel = Path("depth") / f"{i:04d}.pgm"
        rgb_real, depth_real = save_frame(frame, out_dir / rgb_rel, out_dir / depth_rel)

        cur_xyz, cur_rpy = robot.get_current_pose()
        joints = robot.get_current_joints()

        row = {
            "idx": i,
            "timestamp": datetime.now().isoformat(timespec="milliseconds"),
            "xyz": cur_xyz,
            "rpy": cur_rpy,
            "joints": joints,
            "rgb": str(rgb_real.relative_to(out_dir)).replace("\\", "/"),
            "depth": str(depth_real.relative_to(out_dir)).replace("\\", "/"),
        }
        append_pose_row(txt_path, row)
        records.append(row)

    return records
