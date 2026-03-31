from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class CanonConfig:
    enabled: bool = True
    camera_ip: str = "192.168.1.2"
    port: int = 8080
    save_dir: str = r"C:\Users\dell\canon_test"


@dataclass
class RobotConfig:
    enabled: bool = False
    ip: str = "192.168.1.18"
    port: int = 8080
    timeout: float = 5.0
    dof: int = 6


@dataclass
class RealSenseConfig:
    width: int = 640
    height: int = 480
    fps: int = 30
    serial_number: str = ""


@dataclass
class ScannerConfig:
    speed: float = 0.05
    settle_frames: int = 3
    pos_tol: float = 1.0
    ang_tol: float = 1.0
    timeout: float = 20.0


@dataclass
class OutputConfig:
    root_dir: Path = Path("output")
    unique_session: bool = True
    trigger_file: str = "trigger.json"
    write_trigger: bool = True
    rgb_subdir: str = "rgb"
    depth_subdir: str = "depth"
    canon_subdir: str = "canon"
