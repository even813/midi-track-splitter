"""
gui_app.py
────────────────────────────────────────────────────────────
MIDI 钢琴分轨工具 - 精美 tkinter GUI

设计要点：
  · 现代深色主题，精致配色
  · 拖拽上传 / 点击上传双支持
  · 实时轨道分析表格（带评分进度条视觉效果）
  · 可手动勾选/取消钢琴轨道
  · 阈值调节滑块
  · 输出路径自定义
  · 进度提示 + 状态栏

作者：资深开发工程师 / 高质量代码示范
"""

from __future__ import annotations

import os
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import List, Optional

# 确保导入路径正确（支持直接运行或作为模块）
_THIS_DIR = Path(__file__).parent
if str(_THIS_DIR) not in sys.path:
    sys.path.insert(0, str(_THIS_DIR))

from piano_analyzer import TrackInfo
from piano_extractor import PianoExtractor


# ────────────────────────────────────────────────────────────
# 颜色主题（深色现代风）
# ────────────────────────────────────────────────────────────
COLORS = {
    "bg":           "#1a1b2e",   # 深蓝背景
    "bg_card":      "#16213e",   # 卡片背景
    "bg_input":     "#0f3460",   # 输入区背景
    "accent":       "#e94560",   # 强调色（玫红）
    "accent2":      "#533483",   # 次要强调色（紫）
    "success":      "#00d4aa",   # 成功绿
    "warning":      "#f7b731",   # 警告黄
    "text":         "#eaeaea",   # 主文字
    "text_dim":     "#8892b0",   # 次文字
    "border":       "#2d3561",   # 边框
    "row_even":     "#1a2744",   # 表格偶数行
    "row_odd":      "#16213e",   # 表格奇数行
    "piano_row":    "#1a3a2e",   # 钢琴轨道行（绿色调）
    "score_high":   "#00d4aa",
    "score_mid":    "#f7b731",
    "score_low":    "#e94560",
}

FONTS = {
    "title":    ("Segoe UI", 18, "bold"),
    "heading":  ("Segoe UI", 11, "bold"),
    "body":     ("Segoe UI", 10),
    "small":    ("Segoe UI", 9),
    "mono":     ("Consolas", 10),
    "icon":     ("Segoe UI Emoji", 14),
}


# ────────────────────────────────────────────────────────────
# 主窗口
# ────────────────────────────────────────────────────────────
class MidiPianoApp(tk.Tk):
    APP_TITLE = "🎹 MIDI 钢琴分轨工具"
    APP_VERSION = "v1.0"
    WIN_W, WIN_H = 900, 680

    def __init__(self):
        super().__init__()
        self.title(f"{self.APP_TITLE}  {self.APP_VERSION}")
        self.geometry(f"{self.WIN_W}x{self.WIN_H}")
        self.minsize(780, 560)
        self.configure(bg=COLORS["bg"])
        self.resizable(True, True)

        # 状态变量
        self.input_path: Optional[Path] = None
        self.output_path: Optional[Path] = None
        self.track_infos: List[TrackInfo] = []
        self.track_vars: List[tk.BooleanVar] = []   # 勾选框状态
        self._busy = False

        self._setup_styles()
        self._build_ui()
        self._bind_events()

    # ── 样式配置 ────────────────────────────────────────────

    def _setup_styles(self):
        style = ttk.Style(self)
        style.theme_use("clam")

        style.configure(
            "TFrame", background=COLORS["bg"]
        )
        style.configure(
            "Card.TFrame", background=COLORS["bg_card"]
        )
        style.configure(
            "TLabel",
            background=COLORS["bg"],
            foreground=COLORS["text"],
            font=FONTS["body"],
        )
        style.configure(
            "Title.TLabel",
            background=COLORS["bg"],
            foreground=COLORS["text"],
            font=FONTS["title"],
        )
        style.configure(
            "Dim.TLabel",
            background=COLORS["bg"],
            foreground=COLORS["text_dim"],
            font=FONTS["small"],
        )
        style.configure(
            "Card.TLabel",
            background=COLORS["bg_card"],
            foreground=COLORS["text"],
            font=FONTS["body"],
        )
        # 主按钮
        style.configure(
            "Accent.TButton",
            background=COLORS["accent"],
            foreground="white",
            font=FONTS["heading"],
            borderwidth=0,
            relief="flat",
            padding=(20, 10),
        )
        style.map(
            "Accent.TButton",
            background=[("active", "#c73652"), ("disabled", "#444")],
            foreground=[("disabled", "#888")],
        )
        # 次要按钮
        style.configure(
            "Secondary.TButton",
            background=COLORS["bg_input"],
            foreground=COLORS["text"],
            font=FONTS["body"],
            borderwidth=0,
            relief="flat",
            padding=(12, 8),
        )
        style.map(
            "Secondary.TButton",
            background=[("active", COLORS["accent2"])],
        )
        # Treeview（轨道列表）
        style.configure(
            "Tracks.Treeview",
            background=COLORS["bg_card"],
            foreground=COLORS["text"],
            fieldbackground=COLORS["bg_card"],
            rowheight=30,
            font=FONTS["body"],
            borderwidth=0,
        )
        style.configure(
            "Tracks.Treeview.Heading",
            background=COLORS["bg_input"],
            foreground=COLORS["text_dim"],
            font=FONTS["small"],
            relief="flat",
        )
        style.map(
            "Tracks.Treeview",
            background=[("selected", COLORS["accent2"])],
            foreground=[("selected", "white")],
        )
        # 进度条
        style.configure(
            "Accent.Horizontal.TProgressbar",
            troughcolor=COLORS["border"],
            background=COLORS["accent"],
            borderwidth=0,
        )
        # 滑块
        style.configure(
            "TScale",
            background=COLORS["bg"],
            troughcolor=COLORS["border"],
        )

    # ── UI 构建 ─────────────────────────────────────────────

    def _build_ui(self):
        # ── 顶部标题栏 ──────────────────────────────────────
        header = ttk.Frame(self, style="TFrame", padding=(20, 16, 20, 8))
        header.pack(fill="x")

        ttk.Label(header, text="🎹 MIDI 钢琴分轨工具", style="Title.TLabel").pack(side="left")
        ttk.Label(
            header,
            text="智能识别并提取 MIDI 中的钢琴声部",
            style="Dim.TLabel",
        ).pack(side="left", padx=(14, 0), pady=(4, 0))

        # ── 主体区域 ────────────────────────────────────────
        body = ttk.Frame(self, padding=(20, 0, 20, 0))
        body.pack(fill="both", expand=True)
        body.columnconfigure(0, weight=1)
        body.rowconfigure(2, weight=1)

        # 第一行：文件输入区
        self._build_drop_zone(body)

        # 第二行：设置区（阈值 + 输出路径）
        self._build_settings(body)

        # 第三行：轨道分析表格
        self._build_track_table(body)

        # 第四行：操作按钮
        self._build_action_bar(body)

        # ── 底部状态栏 ──────────────────────────────────────
        self._build_status_bar()

    def _build_drop_zone(self, parent):
        """文件拖放/选择区域"""
        frame = tk.Frame(
            parent,
            bg=COLORS["bg_input"],
            cursor="hand2",
            bd=2,
            relief="flat",
            highlightbackground=COLORS["border"],
            highlightthickness=1,
        )
        frame.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        frame.columnconfigure(1, weight=1)

        # 图标
        tk.Label(
            frame, text="📂", font=FONTS["icon"],
            bg=COLORS["bg_input"], fg=COLORS["text"],
        ).grid(row=0, column=0, rowspan=2, padx=(16, 8), pady=14)

        # 主文字
        self.drop_label = tk.Label(
            frame,
            text="点击选择 MIDI 文件  或将文件拖到此处",
            font=FONTS["heading"],
            bg=COLORS["bg_input"],
            fg=COLORS["text"],
            cursor="hand2",
        )
        self.drop_label.grid(row=0, column=1, sticky="w", pady=(12, 2))

        # 副文字
        self.drop_sub = tk.Label(
            frame,
            text="支持 .mid / .midi 格式",
            font=FONTS["small"],
            bg=COLORS["bg_input"],
            fg=COLORS["text_dim"],
        )
        self.drop_sub.grid(row=1, column=1, sticky="w", pady=(0, 12))

        # 绑定点击
        for w in (frame, self.drop_label, self.drop_sub):
            w.bind("<Button-1>", lambda e: self._open_file())
            w.bind("<Enter>", lambda e, f=frame: f.config(bg=COLORS["bg_card"]) or
                   self.drop_label.config(fg=COLORS["accent"]))
            w.bind("<Leave>", lambda e, f=frame: f.config(bg=COLORS["bg_input"]) or
                   self.drop_label.config(fg=COLORS["text"]))

        self.drop_zone = frame

    def _build_settings(self, parent):
        """阈值 + 输出路径设置行"""
        frame = ttk.Frame(parent)
        frame.grid(row=1, column=0, sticky="ew", pady=(0, 10))
        frame.columnconfigure(0, weight=1)
        frame.columnconfigure(1, weight=0)

        # ── 左：阈值 ──────────────────────────────────────
        left = tk.Frame(frame, bg=COLORS["bg_card"], padx=12, pady=10)
        left.grid(row=0, column=0, sticky="ew", padx=(0, 6))
        left.columnconfigure(1, weight=1)

        tk.Label(left, text="识别灵敏度", font=FONTS["body"],
                 bg=COLORS["bg_card"], fg=COLORS["text_dim"]).grid(
            row=0, column=0, padx=(0, 10))

        self.threshold_var = tk.DoubleVar(value=45.0)
        scale = tk.Scale(
            left, from_=20, to=85,
            orient="horizontal",
            variable=self.threshold_var,
            bg=COLORS["bg_card"], fg=COLORS["text"],
            troughcolor=COLORS["border"],
            highlightthickness=0,
            sliderrelief="flat",
            command=self._on_threshold_change,
        )
        scale.grid(row=0, column=1, sticky="ew")

        self.threshold_label = tk.Label(
            left, text="45", width=3,
            font=FONTS["mono"], bg=COLORS["bg_card"], fg=COLORS["accent"],
        )
        self.threshold_label.grid(row=0, column=2, padx=(8, 0))

        tk.Label(left, text="← 宽松   严格 →",
                 font=FONTS["small"], bg=COLORS["bg_card"],
                 fg=COLORS["text_dim"]).grid(row=1, column=1, sticky="w")

        # ── 右：输出路径 ───────────────────────────────────
        right = tk.Frame(frame, bg=COLORS["bg_card"], padx=12, pady=10)
        right.grid(row=0, column=1, sticky="ew", padx=(6, 0))
        right.columnconfigure(0, weight=0)

        tk.Label(right, text="输出目录", font=FONTS["body"],
                 bg=COLORS["bg_card"], fg=COLORS["text_dim"]).grid(
            row=0, column=0, sticky="w")

        self.output_dir_var = tk.StringVar(value="（与源文件相同目录）")
        out_entry = tk.Entry(
            right, textvariable=self.output_dir_var, width=28,
            bg=COLORS["bg_input"], fg=COLORS["text"],
            insertbackground=COLORS["accent"],
            relief="flat", font=FONTS["small"],
        )
        out_entry.grid(row=1, column=0, padx=(0, 6), pady=(2, 0))

        tk.Button(
            right, text="浏览",
            bg=COLORS["accent2"], fg="white",
            relief="flat", font=FONTS["small"],
            cursor="hand2", padx=8,
            command=self._browse_output,
        ).grid(row=1, column=1, pady=(2, 0))

    def _build_track_table(self, parent):
        """轨道分析结果表格"""
        outer = tk.Frame(parent, bg=COLORS["bg_card"], bd=0)
        outer.grid(row=2, column=0, sticky="nsew", pady=(0, 10))
        outer.columnconfigure(0, weight=1)
        outer.rowconfigure(1, weight=1)

        # 标题行
        hdr = tk.Frame(outer, bg=COLORS["bg_input"], padx=12, pady=8)
        hdr.grid(row=0, column=0, sticky="ew")

        tk.Label(
            hdr, text="🎼 轨道分析",
            font=FONTS["heading"], bg=COLORS["bg_input"], fg=COLORS["text"],
        ).pack(side="left")

        self.track_count_label = tk.Label(
            hdr, text="",
            font=FONTS["small"], bg=COLORS["bg_input"], fg=COLORS["text_dim"],
        )
        self.track_count_label.pack(side="left", padx=(10, 0))

        tk.Label(
            hdr,
            text="✅ 绿色行 = 识别为钢琴   勾选框可手动调整",
            font=FONTS["small"], bg=COLORS["bg_input"], fg=COLORS["text_dim"],
        ).pack(side="right")

        # Treeview
        tree_frame = tk.Frame(outer, bg=COLORS["bg_card"])
        tree_frame.grid(row=1, column=0, sticky="nsew", padx=2, pady=2)
        tree_frame.columnconfigure(0, weight=1)
        tree_frame.rowconfigure(0, weight=1)

        cols = ("check", "idx", "name", "program", "notes", "range", "score", "conf")
        self.tree = ttk.Treeview(
            tree_frame,
            columns=cols,
            show="headings",
            style="Tracks.Treeview",
        )

        # 列定义
        self.tree.heading("check",   text="✓")
        self.tree.heading("idx",     text="轨道#")
        self.tree.heading("name",    text="轨道名称")
        self.tree.heading("program", text="GM音色")
        self.tree.heading("notes",   text="音符数")
        self.tree.heading("range",   text="音域")
        self.tree.heading("score",   text="钢琴评分")
        self.tree.heading("conf",    text="置信度")

        self.tree.column("check",   width=36,  minwidth=36,  anchor="center", stretch=False)
        self.tree.column("idx",     width=54,  minwidth=54,  anchor="center", stretch=False)
        self.tree.column("name",    width=180, minwidth=100, anchor="w")
        self.tree.column("program", width=130, minwidth=80,  anchor="center")
        self.tree.column("notes",   width=70,  minwidth=60,  anchor="center")
        self.tree.column("range",   width=110, minwidth=80,  anchor="center")
        self.tree.column("score",   width=120, minwidth=80,  anchor="center")
        self.tree.column("conf",    width=80,  minwidth=60,  anchor="center")

        # 滚动条
        vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)

        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")

        # 行标签颜色
        self.tree.tag_configure("piano",    background=COLORS["piano_row"])
        self.tree.tag_configure("non_piano", background=COLORS["row_odd"])
        self.tree.tag_configure("even",      background=COLORS["row_even"])

        # 点击行切换勾选
        self.tree.bind("<ButtonRelease-1>", self._on_tree_click)

        # 空状态提示
        self.empty_label = tk.Label(
            tree_frame,
            text="请先选择一个 MIDI 文件，分析结果将显示在此处",
            font=FONTS["body"], bg=COLORS["bg_card"], fg=COLORS["text_dim"],
        )
        self.empty_label.place(relx=0.5, rely=0.5, anchor="center")

    def _build_action_bar(self, parent):
        """底部操作按钮行"""
        bar = tk.Frame(parent, bg=COLORS["bg"])
        bar.grid(row=3, column=0, sticky="ew", pady=(0, 8))

        # 全选 / 全不选
        tk.Button(
            bar, text="全选", bg=COLORS["bg_card"], fg=COLORS["text_dim"],
            relief="flat", font=FONTS["small"], cursor="hand2", padx=10,
            command=self._select_all,
        ).pack(side="left", padx=(0, 6))

        tk.Button(
            bar, text="仅钢琴", bg=COLORS["bg_card"], fg=COLORS["text_dim"],
            relief="flat", font=FONTS["small"], cursor="hand2", padx=10,
            command=self._select_piano_only,
        ).pack(side="left", padx=(0, 6))

        tk.Button(
            bar, text="全不选", bg=COLORS["bg_card"], fg=COLORS["text_dim"],
            relief="flat", font=FONTS["small"], cursor="hand2", padx=10,
            command=self._deselect_all,
        ).pack(side="left")

        # 分析 + 提取按钮
        self.analyze_btn = tk.Button(
            bar, text="🔍  重新分析",
            bg=COLORS["accent2"], fg="white",
            relief="flat", font=FONTS["heading"],
            cursor="hand2", padx=18, pady=8,
            command=self._run_analyze,
        )
        self.analyze_btn.pack(side="right", padx=(8, 0))

        self.extract_btn = tk.Button(
            bar, text="🎹  提取钢琴轨道",
            bg=COLORS["accent"], fg="white",
            relief="flat", font=FONTS["heading"],
            cursor="hand2", padx=18, pady=8,
            state="disabled",
            command=self._run_extract,
        )
        self.extract_btn.pack(side="right")

    def _build_status_bar(self):
        """底部状态栏"""
        bar = tk.Frame(self, bg=COLORS["bg_input"], height=28)
        bar.pack(fill="x", side="bottom")
        bar.pack_propagate(False)

        self.status_var = tk.StringVar(value="就绪  |  请选择 MIDI 文件开始")
        tk.Label(
            bar, textvariable=self.status_var,
            font=FONTS["small"], bg=COLORS["bg_input"], fg=COLORS["text_dim"],
            anchor="w",
        ).pack(side="left", padx=12, fill="both")

        # 进度条（平时隐藏）
        self.progress = ttk.Progressbar(
            bar, mode="indeterminate", length=120,
            style="Accent.Horizontal.TProgressbar",
        )
        self.progress.pack(side="right", padx=12, pady=4)
        self.progress.pack_forget()  # 初始隐藏

    # ── 事件绑定 ────────────────────────────────────────────

    def _bind_events(self):
        # 拖放支持（Windows tkinterdnd2 可选，这里提供降级方案）
        try:
            from tkinterdnd2 import DND_FILES, TkinterDnD  # type: ignore
            self.drop_zone.drop_target_register(DND_FILES)
            self.drop_zone.dnd_bind("<<Drop>>", self._on_drop)
        except ImportError:
            pass  # 没有拖放库时，只用点击

    def _on_drop(self, event):
        path = event.data.strip().strip("{}")
        self._load_file(Path(path))

    def _on_threshold_change(self, val):
        v = int(float(val))
        self.threshold_label.config(text=str(v))
        # 如果已有分析结果，自动重新分析
        if self.track_infos:
            self._run_analyze()

    def _on_tree_click(self, event):
        """点击表格行切换勾选状态"""
        item = self.tree.identify_row(event.y)
        if not item:
            return
        idx = int(item)  # 我们用 track index 作 iid
        var = self.track_vars[idx]
        var.set(not var.get())
        self._refresh_row(idx)

    # ── 核心操作 ────────────────────────────────────────────

    def _open_file(self):
        path = filedialog.askopenfilename(
            title="选择 MIDI 文件",
            filetypes=[("MIDI 文件", "*.mid *.midi"), ("所有文件", "*.*")],
        )
        if path:
            self._load_file(Path(path))

    def _browse_output(self):
        d = filedialog.askdirectory(title="选择输出目录")
        if d:
            self.output_dir_var.set(d)

    def _load_file(self, path: Path):
        if not path.exists():
            messagebox.showerror("错误", f"文件不存在：{path}")
            return
        if path.suffix.lower() not in (".mid", ".midi"):
            messagebox.showerror("格式错误", "请选择 .mid 或 .midi 格式的文件")
            return

        self.input_path = path
        self.drop_label.config(text=f"📄  {path.name}")
        self.drop_sub.config(text=str(path))
        self._set_status(f"已加载：{path.name}  |  正在分析轨道…")
        self._run_analyze()

    def _run_analyze(self):
        if not self.input_path or self._busy:
            return
        self._set_busy(True)
        self._set_status("正在分析 MIDI 轨道，请稍候…")

        def task():
            try:
                thr = self.threshold_var.get()
                extractor = PianoExtractor(threshold=thr)
                tracks = extractor.get_track_analysis(str(self.input_path))
                self.after(0, self._on_analyze_done, tracks)
            except Exception as e:
                self.after(0, self._on_analyze_error, str(e))

        threading.Thread(target=task, daemon=True).start()

    def _on_analyze_done(self, tracks: List[TrackInfo]):
        self.track_infos = tracks
        self._rebuild_track_vars()
        self._refresh_table()
        piano_count = sum(1 for t in tracks if t.is_piano)
        self._set_status(
            f"分析完成  |  共 {len(tracks)} 条轨道，识别到 {piano_count} 条钢琴轨道"
        )
        self.extract_btn.config(state="normal" if piano_count > 0 else "disabled")
        self._set_busy(False)
        self.empty_label.place_forget()

    def _on_analyze_error(self, msg: str):
        self._set_busy(False)
        self._set_status(f"❌ 分析失败：{msg}")
        messagebox.showerror("分析失败", msg)

    def _run_extract(self):
        if not self.input_path or self._busy:
            return

        # 获取手动勾选的轨道
        selected = [
            info.index
            for i, info in enumerate(self.track_infos)
            if i < len(self.track_vars) and self.track_vars[i].get()
        ]
        if not selected:
            messagebox.showwarning("未选择轨道", "请至少勾选一条钢琴轨道")
            return

        # 确定输出路径
        out_dir_str = self.output_dir_var.get()
        if out_dir_str == "（与源文件相同目录）" or not out_dir_str:
            out_dir = self.input_path.parent
        else:
            out_dir = Path(out_dir_str)

        out_path = out_dir / f"{self.input_path.stem}_piano.mid"

        self._set_busy(True)
        self._set_status(f"正在提取 {len(selected)} 条轨道，请稍候…")

        def task():
            try:
                thr = self.threshold_var.get()
                extractor = PianoExtractor(threshold=thr)
                result = extractor.extract(
                    str(self.input_path),
                    str(out_path),
                    manual_track_indices=selected,
                )
                self.after(0, self._on_extract_done, result, out_path)
            except Exception as e:
                self.after(0, self._on_extract_error, str(e))

        threading.Thread(target=task, daemon=True).start()

    def _on_extract_done(self, result, out_path):
        self._set_busy(False)
        if result.success:
            self._set_status(
                f"✅ 提取成功  |  {result.message}  |  {out_path.name}"
            )
            ans = messagebox.askyesno(
                "提取成功 🎉",
                f"{result.message}\n\n输出文件：\n{out_path}\n\n是否打开所在文件夹？",
            )
            if ans:
                os.startfile(str(out_path.parent))
        else:
            self._set_status(f"❌ 提取失败：{result.message}")
            messagebox.showerror("提取失败", result.message)

    def _on_extract_error(self, msg: str):
        self._set_busy(False)
        self._set_status(f"❌ 提取失败：{msg}")
        messagebox.showerror("提取失败", msg)

    # ── 表格刷新 ────────────────────────────────────────────

    def _rebuild_track_vars(self):
        self.track_vars = [
            tk.BooleanVar(value=t.is_piano)
            for t in self.track_infos
        ]

    def _refresh_table(self):
        self.tree.delete(*self.tree.get_children())

        piano_count = 0
        for i, info in enumerate(self.track_infos):
            if info.is_piano:
                piano_count += 1

        self.track_count_label.config(
            text=f"共 {len(self.track_infos)} 轨  ·  钢琴 {piano_count} 轨"
        )

        for i, info in enumerate(self.track_infos):
            self._insert_row(i, info)

    def _insert_row(self, list_idx: int, info: TrackInfo):
        checked = "☑" if self.track_vars[list_idx].get() else "☐"
        lo, hi = info.note_range
        range_str = f"{lo}–{hi}" if info.note_count > 0 else "—"
        score_str = f"{info.piano_score:.1f}"
        conf_map = {"high": "★★★ 高", "medium": "★★☆ 中", "low": "★☆☆ 低"}
        conf_str = conf_map.get(info.confidence, info.confidence)

        prog_str = self._program_name(info.program) if info.program is not None else "未知"
        if info.is_drum:
            prog_str = "🥁 打击乐"

        tag = "piano" if info.is_piano else ("even" if list_idx % 2 == 0 else "non_piano")

        self.tree.insert(
            "", "end",
            iid=str(list_idx),   # 用 list_idx 作为 iid
            values=(
                checked,
                f"#{info.index:02d}",
                info.name or "（未命名）",
                prog_str,
                str(info.note_count),
                range_str,
                score_str,
                conf_str,
            ),
            tags=(tag,),
        )

    def _refresh_row(self, list_idx: int):
        """更新单行勾选状态"""
        checked = "☑" if self.track_vars[list_idx].get() else "☐"
        values = list(self.tree.item(str(list_idx), "values"))
        values[0] = checked
        self.tree.item(str(list_idx), values=values)

    @staticmethod
    def _program_name(program: Optional[int]) -> str:
        """GM 音色名称（只列出常见的）"""
        gm_names = {
            0: "🎹 大三角钢琴",
            1: "🎹 明亮三角钢琴",
            2: "🎹 电钢琴（电）",
            3: "🎹 酒吧钢琴",
            4: "🎹 击弦琴",
            5: "🎹 调音琴",
            6: "🎹 羽管键琴",
            7: "🎹 古钢琴",
            8: "🎸 管风琴",
            16: "🎸 簧风琴",
            24: "🎸 尼龙弦吉他",
            32: "🎸 古典贝斯",
            40: "🎻 小提琴",
            48: "🎺 弦乐合奏1",
            56: "🎺 小号",
            73: "🎷 长笛",
        }
        if program in gm_names:
            return gm_names[program]
        return f"GM #{program}"

    # ── 快捷选择 ────────────────────────────────────────────

    def _select_all(self):
        for i, var in enumerate(self.track_vars):
            var.set(True)
            self._refresh_row(i)

    def _deselect_all(self):
        for i, var in enumerate(self.track_vars):
            var.set(False)
            self._refresh_row(i)

    def _select_piano_only(self):
        for i, (var, info) in enumerate(zip(self.track_vars, self.track_infos)):
            var.set(info.is_piano)
            self._refresh_row(i)

    # ── 辅助 ────────────────────────────────────────────────

    def _set_status(self, msg: str):
        self.status_var.set(msg)

    def _set_busy(self, busy: bool):
        self._busy = busy
        if busy:
            self.progress.pack(side="right", padx=12, pady=4)
            self.progress.start(12)
            self.extract_btn.config(state="disabled")
            self.analyze_btn.config(state="disabled")
        else:
            self.progress.stop()
            self.progress.pack_forget()
            self.analyze_btn.config(state="normal")


# ────────────────────────────────────────────────────────────
# 入口
# ────────────────────────────────────────────────────────────
def main():
    app = MidiPianoApp()
    app.mainloop()


if __name__ == "__main__":
    main()
