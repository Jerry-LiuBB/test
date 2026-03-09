import tempfile
import unittest
from pathlib import Path

from dataio.pose_io import append_pose_row, read_pose_rows, write_pose_rows


class PoseIoTest(unittest.TestCase):
    def test_write_and_read_pose_rows(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "poses.txt"
            rows = [
                {"idx": 0, "xyz": [0.1, 0.2, 0.3], "rpy": [180, 0, 90]},
                {"idx": 1, "xyz": [0.2, 0.3, 0.4], "rpy": [180, 0, 120]},
            ]
            write_pose_rows(path, rows)
            loaded = read_pose_rows(path)
            self.assertEqual(loaded, rows)

    def test_append_pose_row(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "poses.txt"
            append_pose_row(path, {"idx": 0})
            append_pose_row(path, {"idx": 1})
            loaded = read_pose_rows(path)
            self.assertEqual([r["idx"] for r in loaded], [0, 1])


if __name__ == "__main__":
    unittest.main()
