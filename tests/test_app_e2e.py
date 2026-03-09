import json
import subprocess
import tempfile
import unittest
from pathlib import Path


class AppE2ETest(unittest.TestCase):
    def test_generate_then_replay(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            gen_dir = root / "session_generate"
            rep_dir = root / "session_replay"

            subprocess.run(
                [
                    "python",
                    "app.py",
                    "generate",
                    "--out-dir",
                    str(gen_dir),
                    "--num-points",
                    "3",
                    "--radius",
                    "0.1",
                ],
                check=True,
            )

            poses_path = gen_dir / "poses.txt"
            self.assertTrue(poses_path.exists())
            rows = [json.loads(line) for line in poses_path.read_text(encoding="utf-8").splitlines() if line.strip()]
            self.assertEqual(len(rows), 3)

            subprocess.run(
                [
                    "python",
                    "app.py",
                    "replay",
                    "--poses-txt",
                    str(poses_path),
                    "--out-dir",
                    str(rep_dir),
                ],
                check=True,
            )

            replay_poses = rep_dir / "poses.txt"
            self.assertTrue(replay_poses.exists())
            replay_rows = [json.loads(line) for line in replay_poses.read_text(encoding="utf-8").splitlines() if line.strip()]
            self.assertEqual(len(replay_rows), 3)


if __name__ == "__main__":
    unittest.main()
