from __future__ import annotations

import socket
import json
import time
from dataclasses import dataclass
from typing import List, Sequence, Tuple, Optional
import threading


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


class RealManRobotDriver(RobotDriverBase):
    """
    RealMan robot arm driver using JSON protocol over TCP/IP.

    Communication:
    - All commands must end with \\r\\n
    - Position unit: 0.001mm (multiply meters by 1000)
    - Orientation unit: 0.001rad
    - Joint angle unit: 0.001°
    - Speed range: 0-100
    """

    def __init__(
        self,
        ip: str = "192.168.1.18",
        port: int = 8080,
        timeout: float = 5.0,
        dof: int = 6,
    ):
        self._ip = ip
        self._port = port
        self._timeout = timeout
        self._dof = dof
        self._sock: Optional[socket.socket] = None
        self._lock = threading.Lock()
        self._joints = [0.0] * dof
        self._pose = Pose(xyz=[0.0, 0.0, 0.0], rpy=[0.0, 0.0, 0.0])
        self._is_moving = False

    def _send_command(self, cmd: dict) -> dict:
        """Send JSON command and receive response."""
        if not self._sock:
            raise RuntimeError("Not connected to robot")

        with self._lock:
            data = json.dumps(cmd) + "\r\n"
            self._sock.sendall(data.encode("utf-8"))
            response = self._sock.recv(4096).decode("utf-8")
            if not response:
                raise RuntimeError("No response from robot")
            return json.loads(response.strip())

    def connect(self) -> None:
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._sock.settimeout(self._timeout)
        self._sock.connect((self._ip, self._port))
        time.sleep(0.5)
        self._update_state()

    def disconnect(self) -> None:
        if self._sock:
            self._sock.close()
            self._sock = None

    def _update_state(self) -> None:
        """Update current pose and joints from robot."""
        try:
            state = self._get_arm_state()
            if "pose" in state:
                pose_data = state["pose"]
                self._pose = Pose(
                    xyz=[pose_data[0] / 1000.0, pose_data[1] / 1000.0, pose_data[2] / 1000.0],
                    rpy=[pose_data[3] / 1000.0, pose_data[4] / 1000.0, pose_data[5] / 1000.0],
                )
            if "joint" in state:
                self._joints = [j / 1000.0 for j in state["joint"]]
        except Exception:
            pass

    def _get_arm_state(self) -> dict:
        """Get current arm state."""
        cmd = {"command": "get_current_arm_state", "state": "pose"}
        return self._send_command(cmd)

    def move_pose(self, xyz: Sequence[float], rpy: Sequence[float], speed: float = 0.05) -> None:
        """
        Move robot to target pose using linear motion (movel).

        Args:
            xyz: Target position in meters [x, y, z]
            rpy: Target orientation in radians [roll, pitch, yaw]
            speed: Speed percentage (0-1), will be converted to 0-100
        """
        if not self._sock:
            raise RuntimeError("Robot is not connected")

        pose_values = [
            int(xyz[0] * 1000),
            int(xyz[1] * 1000),
            int(xyz[2] * 1000),
            int(rpy[0] * 1000),
            int(rpy[1] * 1000),
            int(rpy[2] * 1000),
        ]
        speed_percent = max(1, min(100, int(speed * 100)))

        cmd = {
            "command": "movel",
            "pose": pose_values,
            "v": speed_percent,
            "r": 0,
            "trajectory_connect": 0,
        }

        response = self._send_command(cmd)
        if not response.get("receive_state", False):
            raise RuntimeError(f"Failed to send move command: {response}")

        self._is_moving = True

    def get_current_pose(self) -> Tuple[List[float], List[float]]:
        """Get current end-effector pose."""
        self._update_state()
        return list(self._pose.xyz), list(self._pose.rpy)

    def get_current_joints(self) -> List[float]:
        """Get current joint angles in radians."""
        self._update_state()
        return list(self._joints)

    def wait_until_reached(self, timeout: float = 10.0, pos_tol: float = 1.0, ang_tol: float = 1.0) -> bool:
        """
        Wait until robot reaches target position.

        Args:
            timeout: Maximum wait time in seconds
            pos_tol: Position tolerance in mm
            ang_tol: Orientation tolerance in rad (converted to 0.001rad internally)

        Returns:
            True if target reached, False if timeout
        """
        if not self._sock:
            return False

        start_time = time.time()
        ang_tol_int = int(ang_tol * 1000)
        pos_tol_int = int(pos_tol)

        while self._is_moving:
            if time.time() - start_time > timeout:
                return False

            try:
                cmd = {"command": "current_trajectory_state", "trajectory_connect": 1}
                response = self._send_command(cmd)
                if response.get("state") == "current_trajectory_state":
                    if response.get("trajectory_state", False):
                        self._is_moving = False
                        self._update_state()
                        return True
            except Exception:
                pass

            time.sleep(0.05)

        target_xyz = self._pose.xyz
        target_rpy = self._pose.rpy

        while True:
            if time.time() - start_time > timeout:
                return False

            self._update_state()
            curr_xyz, curr_rpy = self._pose.xyz, self._pose.rpy

            pos_diff = sum((a - b) ** 2 for a, b in zip(curr_xyz, target_xyz)) ** 0.5
            ang_diff = sum((a - b) ** 2 for a, b in zip(curr_rpy, target_rpy)) ** 0.5

            if pos_diff <= pos_tol / 1000.0 and ang_diff <= ang_tol:
                return True

            if not self._is_moving:
                return True

            time.sleep(0.05)

        return True

    def is_connected(self) -> bool:
        return self._sock is not None


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

        import math
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
        return True
