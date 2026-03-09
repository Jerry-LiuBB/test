from __future__ import annotations

from typing import Dict, List
import math


def generate_circle_waypoints(
    center_xyz: List[float],
    radius: float,
    z_height: float,
    num_points: int,
    yaw_start_deg: float = 0.0,
) -> List[Dict]:
    """Generate waypoints on a horizontal circle around head center."""
    if num_points < 3:
        raise ValueError("num_points must be >= 3")

    cx, cy, _ = center_xyz
    points: List[Dict] = []
    for i in range(num_points):
        theta = math.radians(yaw_start_deg + i * (360.0 / num_points))
        x = cx + radius * math.cos(theta)
        y = cy + radius * math.sin(theta)
        z = z_height

        # Keep camera facing inward roughly by yawing towards center.
        inward_yaw = (math.degrees(theta) + 180.0) % 360.0
        points.append({"idx": i, "xyz": [round(x, 4), round(y, 4), round(z, 4)], "rpy": [180.0, 0.0, round(inward_yaw, 2)]})
    return points
