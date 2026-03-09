from __future__ import annotations

from dataclasses import dataclass
from typing import List, Sequence, Tuple
import math
import time


@dataclass
class Pose:
    xyz: List[float]
    rpy: List[float]


class RobotDriverBase:
    """Abstract robot driver interface."""

    def connect(self) -> None:
        raise NotImplementedError

    def disconnect(self) -> None:
        raise NotImplementedError

    def move_pose(self, xyz: Sequence[float], rpy: Sequence[float], speed: float = 0.05) -> None:
        raise NotImplementedError

    def get_current_pose(self) -> Tuple[List[float], List[float]]:
        raise NotImplementedError

    def get_current_joints(self) -> List[float]:
        raise NotImplementedError

    def wait_until_reached(self, timeout: float = 10.0, pos_tol: float = 1.0, ang_tol: float = 1.0) -> bool:
        raise NotImplementedError


class MockRobotDriver(RobotDriverBase):
    """A runnable simulator for development without real hardware."""

    def __init__(self, dof: int = 6):
        self._connected = False
        self._pose = Pose(xyz=[0.3, 0.0, 0.45], rpy=[180.0, 0.0, 0.0])
        self._joints = [0.0] * dof

    def connect(self) -> None:
        self._connected = True

    def disconnect(self) -> None:
        self._connected = False

    def move_pose(self, xyz: Sequence[float], rpy: Sequence[float], speed: float = 0.05) -> None:
        if not self._connected:
            raise RuntimeError("Robot is not connected")

        start_xyz = self._pose.xyz
        dist = math.sqrt(sum((float(a) - float(b)) ** 2 for a, b in zip(xyz, start_xyz)))
        sleep_s = min(max(dist / max(speed, 1e-4), 0.05), 0.5)
        time.sleep(sleep_s)

        self._pose = Pose(xyz=[float(v) for v in xyz], rpy=[float(v) for v in rpy])
        self._joints = [round((i + 1) * 0.1 + self._pose.xyz[0], 4) for i in range(len(self._joints))]

    def get_current_pose(self) -> Tuple[List[float], List[float]]:
        return list(self._pose.xyz), list(self._pose.rpy)

    def get_current_joints(self) -> List[float]:
        return list(self._joints)

    def wait_until_reached(self, timeout: float = 10.0, pos_tol: float = 1.0, ang_tol: float = 1.0) -> bool:
        if not self._connected:
            return False
        _ = timeout, pos_tol, ang_tol
        return True
