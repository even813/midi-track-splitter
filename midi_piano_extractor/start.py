"""
start.py
────────────────────────────────────────────────────────────
一键启动脚本

功能：
  1. 检查 Python 版本（需要 3.8+）
  2. 检查并自动安装 mido
  3. 启动 GUI 主程序
"""

import subprocess
import sys
from pathlib import Path


def check_python_version():
    """确保 Python >= 3.8"""
    v = sys.version_info
    if v.major < 3 or (v.major == 3 and v.minor < 8):
        print(f"❌ 需要 Python 3.8 或更高版本，当前版本：{v.major}.{v.minor}")
        input("按回车键退出…")
        sys.exit(1)
    print(f"✅ Python {v.major}.{v.minor}.{v.micro}")


def check_and_install(package: str, import_name: str = None):
    """检查并安装依赖包"""
    import_name = import_name or package
    try:
        __import__(import_name)
        print(f"✅ {package} 已安装")
    except ImportError:
        print(f"📦 正在安装 {package}…")
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", package],
            capture_output=True, text=True,
        )
        if result.returncode == 0:
            print(f"✅ {package} 安装成功")
        else:
            print(f"❌ {package} 安装失败：\n{result.stderr}")
            print("请手动运行：pip install", package)
            input("按回车键退出…")
            sys.exit(1)


def check_tkinter():
    """检查 tkinter 是否可用"""
    try:
        import tkinter  # noqa: F401
        print("✅ tkinter 可用")
    except ImportError:
        print("❌ tkinter 不可用")
        print("   Windows/macOS 用户：重新安装 Python 时勾选 'tcl/tk and IDLE'")
        print("   Linux 用户：sudo apt install python3-tk")
        input("按回车键退出…")
        sys.exit(1)


def main():
    print("=" * 50)
    print("   🎹 MIDI 钢琴分轨工具  启动中…")
    print("=" * 50)

    check_python_version()
    check_tkinter()
    check_and_install("mido")

    print("\n🚀 正在启动界面…\n")

    # 切换到脚本所在目录（确保相对导入正确）
    script_dir = Path(__file__).parent
    sys.path.insert(0, str(script_dir))

    from gui_app import main as run_app
    run_app()


if __name__ == "__main__":
    main()
