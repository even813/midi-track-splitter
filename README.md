# 🎵 MIDI Piano Extractor (MIDI 钢琴音轨提取工具)

![Python](https://img.shields.io/badge/Python-3.8%2B-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)

**MIDI Piano Extractor** 是一款轻量、高效且带有图形化界面 (GUI) 的 Python 工具。它专为从复杂、多乐器的标准 MIDI 文件中，精准解析并提取出纯净的钢琴音轨而设计。

无论您是正在开发自动演奏钢琴机器人、准备音乐训练数据集，还是单纯需要清理多轨 MIDI，这款工具都能为您提供简单快捷的解决方案。

## 📂 项目结构 (Project Structure)

本项目采用清晰的模块化设计：

```text
midi-track-splitter/
├── midi_piano_extractor/
│   ├── start.py                # 程序主入口，负责初始化与调用
│   ├── gui_app.py              # 图形化界面模块 (GUI)
│   ├── piano_analyzer.py       # 音轨分析引擎，负责解析 MIDI 信息与通道判定
│   ├── piano_extractor.py      # 核心提取模块，负责轨道重组与文件导出
│   ├── requirements.txt        # 项目依赖包清单
│   └── 启动工具.bat             # Windows 专用一键启动脚本
└── test/
    └── hardcore_split_test.mid # 用于极限压力测试的多轨 MIDI 测试文件
