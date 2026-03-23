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
                    "--no-unique-out-dir",
                ],
                check=True,
            )

            poses_path = gen_dir / "poses.txt"
            self.assertTrue(poses_path.exists())
            rows = [json.loads(line) for line in poses_path.read_text(encoding="utf-8").splitlines() if line.strip()]
            self.assertEqual(len(rows), 3)

            gen_trigger_path = gen_dir / "trigger.json"
            self.assertTrue(gen_trigger_path.exists())
            gen_trigger = json.loads(gen_trigger_path.read_text(encoding="utf-8"))
            self.assertEqual(gen_trigger["event"], "scan_completed")
            self.assertEqual(gen_trigger["records"], 3)

            subprocess.run(
                [
                    "python",
                    "app.py",
                    "replay",
                    "--poses-txt",
                    str(poses_path),
                    "--out-dir",
                    str(rep_dir),
                    "--no-unique-out-dir",
                ],
                check=True,
            )

            replay_poses = rep_dir / "poses.txt"
            self.assertTrue(replay_poses.exists())
            replay_rows = [json.loads(line) for line in replay_poses.read_text(encoding="utf-8").splitlines() if line.strip()]
            self.assertEqual(len(replay_rows), 3)

            rep_trigger_path = rep_dir / "trigger.json"
            self.assertTrue(rep_trigger_path.exists())
            rep_trigger = json.loads(rep_trigger_path.read_text(encoding="utf-8"))
            self.assertEqual(rep_trigger["event"], "scan_completed")
            self.assertEqual(rep_trigger["records"], 3)

    def test_generate_creates_unique_session_dir_by_default(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            out_root = Path(d) / "sessions"

            subprocess.run(
                [
                    "python",
                    "app.py",
                    "generate",
                    "--out-dir",
                    str(out_root),
                    "--num-points",
                    "3",
                    "--radius",
                    "0.1",
                ],
                check=True,
            )

            session_dirs = [p for p in out_root.iterdir() if p.is_dir() and p.name.startswith("session_generate_")]
            self.assertEqual(len(session_dirs), 1)
            session_dir = session_dirs[0]
            self.assertTrue((session_dir / "poses.txt").exists())
            self.assertTrue((session_dir / "trigger.json").exists())


if __name__ == "__main__":
    unittest.main()
