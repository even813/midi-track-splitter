# 🎹 MIDI 钢琴分轨工具

> 智能识别并提取 MIDI 文件中的钢琴声部，本地运行，无需联网。

---

## ✨ 功能特性

| 功能 | 说明 |
|------|------|
| **智能识别** | 多维度加权评分：轨道名称 + GM音色 + 音域 + 复音密度 + 速度分布 |
| **精美 GUI** | 深色现代主题，轨道分析表格，实时评分可视化 |
| **手动调整** | 可勾选/取消任意轨道，灵敏度滑块调节 |
| **Type 0/1** | 支持单轨多Channel和多轨两种MIDI格式 |
| **Meta保留** | 自动保留BPM、时间签名等全局信息 |
| **批量CLI** | 命令行模式支持批量处理 |

---

## 🚀 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 启动 GUI

```bash
# Windows 双击运行（推荐）
python start.py

# 或直接运行 GUI
python gui_app.py
```

### 3. 使用步骤

1. 点击顶部区域 **选择 MIDI 文件**（或拖入文件）
2. 程序自动分析所有轨道，绿色高亮 = 识别为钢琴
3. 可手动勾选/取消轨道
4. 调整 **识别灵敏度** 滑块（默认45，范围20-85）
5. 点击 **🎹 提取钢琴轨道** 生成新文件

---

## 📁 项目结构

```
midi_piano_extractor/
├── gui_app.py          # GUI 主界面（tkinter）
├── piano_analyzer.py   # 智能识别引擎（核心算法）
├── piano_extractor.py  # 分轨提取器
├── start.py            # 一键启动脚本
├── requirements.txt    # 依赖清单
├── README.md           # 本文件
└── output/             # 默认输出目录
```

---

## 🔧 命令行用法

```bash
# 分析 MIDI（查看轨道信息，不提取）
python piano_analyzer.py song.mid

# 提取钢琴轨道
python piano_extractor.py song.mid song_piano.mid

# 指定识别阈值（20=宽松，85=严格）
python piano_extractor.py song.mid song_piano.mid 35
```

---

## 🧠 识别算法说明

程序使用**多维度加权评分**（满分100分）：

| 维度 | 权重 | 说明 |
|------|------|------|
| 轨道名称 | 35% | 匹配 piano/钢琴/grand/rhodes 等关键词 |
| GM 音色 | 30% | Program 0-7 = 钢琴族（满分），8-23 = 键盘族（中分）|
| 音域特征 | 20% | 典型钢琴音域 A0-C8，含左右手分布检测 |
| 复音密度 | 10% | 音符数量和和弦特征 |
| 速度分布 | 5% | 动态范围越大，钢琴可能性越高 |

**默认阈值 45 分**（即总分 ≥ 45 判定为钢琴）

---

## 💡 常见问题

**Q: 识别不准确怎么办？**
- 调低滑块（宽松）可识别更多轨道
- 调高滑块（严格）减少误识
- 直接手动勾选轨道表格中的目标行

**Q: 输出文件没有声音？**
- 确保 MIDI 播放软件已安装音色库
- 部分 DAW 需要重新加载音色

**Q: 支持哪些 MIDI 类型？**
- Type 0（单轨）：自动按 Channel 拆分
- Type 1（多轨）：直接提取目标轨道
- Type 2：部分支持

---

## 📋 系统要求

- Python 3.8+
- tkinter（Python 自带，无需额外安装）
- Windows / macOS / Linux

---

*使用 mido 库处理 MIDI，纯 Python 实现，无需系统 MIDI 驱动*
