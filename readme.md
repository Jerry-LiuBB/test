# D435 + Canon + 机械臂扫描系统

这是一个**可直接运行**的头皮扫描模板，支持：

- **Canon相机**：拍摄RGB图像（.png）
- **RealSense D435**：采集深度图（.zip.tiff）
- **睿尔曼机械臂**：自动扫描轨迹

> 默认使用模拟机械臂；安装依赖后可连接真机

---

## 1. 目录结构

```
.
├─ app.py                 # 主程序入口
├─ config.py              # 配置文件（IP、路径等）
├─ requirements.txt       # Python依赖
├─ readme.md              # 本说明文档
├─ robot/
│   └─ driver.py          # 机械臂驱动（Mock + RealMan）
├─ camera/
│   ├─ realsense.py       # RealSense D435驱动
│   ├─ canon.py           # Canon相机驱动
│   └─ __init__.py        # 双相机统一接口
├─ scanner/
│   ├─ planner.py         # 轨迹规划
│   └─ executor.py        # 扫描执行
├─ dataio/
│   ├─ pose_io.py         # 姿态数据读写
│   └─ image_io.py        # 图像数据读写
└─ output/                # 输出目录
```

---

## 2. 快速开始

### 2.1 安装依赖

```bash
pip install pyrealsense2 numpy opencv-python tifffile requests
```

### 2.2 运行扫描

**生成模式**（自动生成环形轨迹）：
```bash
python app.py generate
```

**回放模式**（从已有轨迹文件扫描）：
```bash
python app.py replay --poses-txt output/session_xxx/poses.txt
```

---

## 3. 配置说明

编辑 `config.py` 文件：

### 3.1 Canon相机配置

```python
@dataclass
class CanonConfig:
    enabled: bool = True              # 启用Canon相机
    camera_ip: str = "192.168.1.2"   # Canon相机IP地址
    port: int = 8080                  # 端口
    save_dir: str = r"C:\Users\dell\canon_test"  # 图片保存目录
```

### 3.2 机械臂配置

```python
@dataclass
class RobotConfig:
    enabled: bool = False             # 改为True启用真实机械臂
    ip: str = "192.168.1.18"         # 机械臂IP地址
    port: int = 8080                  # TCP端口
    timeout: float = 5.0              # 超时时间(秒)
    dof: int = 6                      # 自由度(6或7)
```

### 3.3 输出配置

```python
@dataclass
class OutputConfig:
    root_dir: Path = Path("output")   # 输出根目录
    unique_session: bool = True        # 创建唯一会话目录
    canon_subdir: str = "canon"       # Canon图片子目录
    depth_subdir: str = "depth"       # 深度图子目录
```

---

## 4. 运行参数

### generate 模式

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `--out-dir` | output | 输出目录 |
| `--center-x` | 0.30 | 圆心X坐标(米) |
| `--center-y` | 0.00 | 圆心Y坐标(米) |
| `--z` | 0.45 | 扫描高度(米) |
| `--radius` | 0.15 | 扫描半径(米) |
| `--num-points` | 8 | 扫描点数 |
| `--speed` | 0.05 | 移动速度(0-1) |
| `--no-unique-out-dir` | - | 禁用唯一会话目录 |

### replay 模式

| 参数 | 说明 |
|------|------|
| `--poses-txt` | 轨迹文件路径(必需) |
| `--out-dir` | 输出目录 |
| `--speed` | 移动速度(0-1) |

---

## 5. 输出格式

### 5.1 目录结构

```
output/session_generate_20260331_143000_abc123/
├── poses.txt
├── canon/
│   ├── 0000.png
│   ├── 0001.png
│   └── ...
├── depth/
│   ├── 0000.zip.tiff
│   ├── 0001.zip.tiff
│   └── ...
└── trigger.json
```

### 5.2 poses.txt 格式

每行一个JSON：

```json
{"idx":0,"timestamp":"2026-03-31T14:30:00.123","xyz":[0.45,0.0,0.45],"rpy":[180.0,0.0,180.0],"joints":[0.55,0.65,0.75,0.85,0.95,1.05],"canon":"canon/0000.png","depth":"depth/0000.zip.tiff"}
```

字段说明：
- `idx`: 序号
- `timestamp`: 时间戳
- `xyz`: 末端位置(米)
- `rpy`: 末端姿态(度)
- `joints`: 关节角度(弧度)
- `canon`: Canon图片相对路径
- `depth`: 深度图相对路径

### 5.3 trigger.json 协议

扫描完成后自动生成：

```json
{
  "event": "scan_completed",
  "timestamp": "2026-03-31T14:30:05.789",
  "out_dir": "C:/Users/dell/OneDrive/文档/test/output/session_generate_20260331_143000_abc123",
  "poses_file": "C:/Users/dell/OneDrive/文档/test/output/session_generate_20260331_143000_abc123/poses.txt",
  "records": 8,
  "status": "ok"
}
```

---

## 6. 硬件连接

### 6.1 Canon相机
- 通过WiFi连接相机IP地址
- 确保相机和电脑在同一网络
- 相机需开启持久连接模式

### 6.2 RealSense D435
- 通过USB连接电脑
- 安装 RealSense SDK：`pip install pyrealsense2`

### 6.3 睿尔曼机械臂
- 通过网线连接机械臂控制器
- 确保机械臂IP与配置一致（默认 `192.168.1.18`）
- 机械臂控制器端口：`8080`

---

## 7. 图像格式说明

| 类型 | 格式 | 说明 |
|------|------|------|
| Canon图片 | .png | RGB彩色图像 |
| 深度图 | .zip.tiff | 16bit深度数据，zlib压缩 |

---

## 8. 安全提示

- 人头周围扫描必须限速、限加速度
- 必做碰撞检测、软限位与急停
- 上真人前请先空载验证全流程

---

## 9. 本地自测

```bash
python -m unittest discover -s tests -v
```
