from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path
from uuid import uuid4

from camera.realsense import RealSenseOrMockCamera
from dataio.pose_io import read_pose_rows
from robot.driver import MockRobotDriver
from scanner.executor import execute_scan
from scanner.planner import generate_circle_waypoints


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="D435i + Robot arm scan template")
    sub = parser.add_subparsers(dest="mode", required=True)

    gen = sub.add_parser("generate", help="Generate circular waypoints and scan")
    gen.add_argument("--out-dir", default="output", help="Output root directory")
    gen.add_argument("--center-x", type=float, default=0.30)
    gen.add_argument("--center-y", type=float, default=0.00)
    gen.add_argument("--z", type=float, default=0.45)
    gen.add_argument("--radius", type=float, default=0.15)
    gen.add_argument("--num-points", type=int, default=8)
    gen.add_argument("--speed", type=float, default=0.05)
    gen.add_argument("--trigger-file", default="trigger.json", help="Trigger filename in out-dir")
    gen.add_argument("--no-trigger", action="store_true", help="Disable writing completion trigger file")
    gen.add_argument("--no-unique-out-dir", action="store_true", help="Disable unique session directory generation")

    replay = sub.add_parser("replay", help="Replay waypoints from txt(JSONL)")
    replay.add_argument("--poses-txt", required=True, help="Path to poses.txt (JSON Lines)")
    replay.add_argument("--out-dir", default="output", help="Output root directory")
    replay.add_argument("--speed", type=float, default=0.05)
    replay.add_argument("--trigger-file", default="trigger.json", help="Trigger filename in out-dir")
    replay.add_argument("--no-trigger", action="store_true", help="Disable writing completion trigger file")
    replay.add_argument("--no-unique-out-dir", action="store_true", help="Disable unique session directory generation")
    return parser


def _build_unique_session_dir(out_root: Path, mode: str) -> Path:
    out_root.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    for _ in range(100):
        candidate = out_root / f"session_{mode}_{timestamp}_{uuid4().hex[:6]}"
        if not candidate.exists():
            return candidate
    raise RuntimeError("Failed to allocate a unique output directory")


def main() -> None:
    args = build_parser().parse_args()

    robot = MockRobotDriver()
    camera = RealSenseOrMockCamera()
    robot.connect()

    try:
        out_root = Path(args.out_dir)
        out_dir = out_root if args.no_unique_out_dir else _build_unique_session_dir(out_root, args.mode)
        trigger_path = None if args.no_trigger else (out_dir / args.trigger_file)

        if args.mode == "generate":
            waypoints = generate_circle_waypoints(
                center_xyz=[args.center_x, args.center_y, args.z],
                radius=args.radius,
                z_height=args.z,
                num_points=args.num_points,
            )
            records = execute_scan(robot, camera, waypoints, out_dir, speed=args.speed, trigger_path=trigger_path)
            print(f"Done: generated+captured {len(records)} points into {out_dir}")

        elif args.mode == "replay":
            rows = read_pose_rows(Path(args.poses_txt))
            waypoints = [{"xyz": row["xyz"], "rpy": row["rpy"]} for row in rows]
            records = execute_scan(robot, camera, waypoints, out_dir, speed=args.speed, trigger_path=trigger_path)
            print(f"Done: replay-captured {len(records)} points into {out_dir}")
    finally:
        camera.close()
        robot.disconnect()


if __name__ == "__main__":
    main()
