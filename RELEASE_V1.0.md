# Release V1.0

## Scope
V1.0 includes a runnable D435i + robot-arm scan template with:

- CLI modes: `generate` and `replay`
- Mock robot driver and optional RealSense camera integration
- Waypoint planner and scan executor pipeline
- Pose IO (JSON Lines) and image IO (PPM/PGM)
- Automated unit and end-to-end tests

## Quick Start
```bash
python app.py generate --out-dir output/session_generate --num-points 8 --radius 0.15
python app.py replay --poses-txt output/session_generate/poses.txt --out-dir output/session_replay
python -m unittest discover -s tests -v
```
