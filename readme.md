# D435i + 机械臂扫描（直接可运行工程模板）

这是一个**可直接运行**的最小模板，默认无第三方依赖也能跑通：

- 固定点位扫描流程：`移动 -> 到位 -> 拍照 -> 记录`。
- 保存机械臂位姿/关节角到 `poses.txt`（JSON Lines）。
- 保存图像到固定目录（RGB=`.ppm`，深度=`.pgm`）。
- 支持读取 `poses.txt` 回放点位并再次拍照。
- 扫描结束后输出 `trigger.json` 作为下游软件触发信号。

> 默认使用模拟机械臂与模拟相机；安装 `pyrealsense2 + numpy` 后可自动切换 RealSense 真机采集。

---

## 1. 目录结构

```text
.
├─ app.py
├─ requirements.txt
├─ robot/driver.py
├─ camera/realsense.py
├─ scanner/planner.py
├─ scanner/executor.py
├─ dataio/pose_io.py
├─ dataio/image_io.py
└─ output/
```

---

## 2. 运行方式（无需安装依赖）

### 2.1 生成环绕点位并扫描

> 默认会在 `--out-dir` 下自动创建唯一会话目录：`session_generate_YYYYMMDD_HHMMSS_xxxxxx`。

```bash
python app.py generate --out-dir output --num-points 8 --radius 0.15
```

### 2.2 从 txt 回放扫描

```bash
python app.py replay --poses-txt output/session_generate_xxx/poses.txt --out-dir output
```

输出内容（在每次唯一会话目录下）：

- `output/session_.../poses.txt`
- `output/session_.../rgb/*.ppm`
- `output/session_.../depth/*.pgm`
- `output/session_.../trigger.json`

如果你希望写到固定目录（会覆盖同名文件），可加：`--no-unique-out-dir`。

---

## 3. poses.txt 格式

每行一个 JSON：

```txt
{"idx":0,"timestamp":"2026-01-01T10:00:00.123","xyz":[0.45,0.0,0.45],"rpy":[180.0,0.0,180.0],"joints":[0.55,0.65,0.75,0.85,0.95,1.05],"rgb":"rgb/0000.ppm","depth":"depth/0000.pgm"}
```

---

## 4. trigger.json 协议（给协作者对接）

推荐你把下面这段作为“触发协议”发给联调同事：

- 触发时机：扫描流程完成并成功落盘 `poses.txt/rgb/depth` 后。
- 触发文件：`<session_dir>/trigger.json`
- 写入方式：原子替换（不会出现半写入）。
- 下游动作：监听到文件创建后读取 JSON，并根据 `out_dir` / `poses_file` 开始下一步处理。

示例：

```json
{
  "event": "scan_completed",
  "timestamp": "2026-03-23T12:34:56.789",
  "out_dir": "/abs/path/output/session_generate_20260323_123456_a1b2c3",
  "poses_file": "/abs/path/output/session_generate_20260323_123456_a1b2c3/poses.txt",
  "records": 8,
  "status": "ok"
}
```

字段说明：

- `event`: 固定 `scan_completed`
- `timestamp`: 触发时间
- `out_dir`: 本次唯一会话目录（绝对路径）
- `poses_file`: 轨迹文件绝对路径
- `records`: 成功采集条数
- `status`: 当前为 `ok`

---

## 5. 接入真实机械臂

编辑 `robot/driver.py`，按 `RobotDriverBase` 接口对接你的厂商 SDK：

- `connect / disconnect`
- `move_pose`
- `get_current_pose`
- `get_current_joints`
- `wait_until_reached`

然后在 `app.py` 把 `MockRobotDriver()` 替换为你的驱动类。

---

## 6. 接入真实 D435i

安装依赖后（可选）：

```bash
pip install pyrealsense2 numpy
```

`camera/realsense.py` 会自动优先使用 RealSense；失败则回退 Mock。

---

## 7. 安全提示

- 人头周围扫描必须限速、限加速度。
- 必做碰撞检测、软限位与急停。
- 上真人前请先空载验证全流程。


## 8. 本地自测

```bash
python -m unittest discover -s tests -v
```
