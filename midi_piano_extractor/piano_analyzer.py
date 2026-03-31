"""
piano_analyzer.py
────────────────────────────────────────────────────────────
MIDI 钢琴轨道智能识别引擎

识别策略（多维度加权评分）：
  1. 轨道名称匹配（权重最高）
  2. GM 音色编号（Program Number）
  3. 音符音域分析
  4. 复音密度与和弦特征
  5. 速度（velocity）分布特征

"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

try:
    import mido
except ImportError:
    raise ImportError("请先安装 mido：pip install mido")


# ────────────────────────────────────────────────────────────
# GM 音色分组（GM Standard Program Numbers, 0-indexed）
# ────────────────────────────────────────────────────────────
# 钢琴族：0-7
PIANO_PROGRAMS = set(range(0, 8))

# 可能混淆的键盘乐器
KEYBOARD_PROGRAMS = set(range(8, 24))   # 色风琴、管风琴等

# 明确不是钢琴的音色
NON_PIANO_PROGRAMS = set(range(24, 128)) - KEYBOARD_PROGRAMS - PIANO_PROGRAMS

# 钢琴惯用音域（MIDI note number）
PIANO_NOTE_MIN = 21   # A0
PIANO_NOTE_MAX = 108  # C8
PIANO_TYPICAL_MIN = 36  # C2（常用低端）
PIANO_TYPICAL_MAX = 96  # C7（常用高端）

# 钢琴名称关键词（支持中英文）
PIANO_NAME_PATTERNS = [
    r"piano", r"pno", r"grand", r"upright",
    r"钢琴", r"钢", r"pianoforte", r"forte",
    r"acoustic\s*piano", r"electric\s*piano", r"ep\b",
    r"keys?\b", r"keyboard",
    r"steinway", r"yamaha\s*p", r"rhodes", r"wurlitzer",
]

# 编译正则（忽略大小写）
_PIANO_RE = re.compile(
    "|".join(f"(?:{p})" for p in PIANO_NAME_PATTERNS),
    re.IGNORECASE
)

# 明确排除的名称（打击乐等）
EXCLUDE_NAME_PATTERNS = [
    r"drum", r"perc", r"bass", r"guitar", r"violin",
    r"鼓", r"打击", r"贝斯", r"吉他",
]
_EXCLUDE_RE = re.compile(
    "|".join(f"(?:{p})" for p in EXCLUDE_NAME_PATTERNS),
    re.IGNORECASE
)


# ────────────────────────────────────────────────────────────
# 数据结构
# ────────────────────────────────────────────────────────────
@dataclass
class TrackInfo:
    """存储单条 MIDI 轨道的分析结果"""
    index: int
    name: str = ""
    channel: Optional[int] = None
    program: Optional[int] = None          # GM 音色编号（最后一次设置）
    is_drum: bool = False                  # 是否为打击乐（channel 9）
    note_count: int = 0
    notes: List[int] = field(default_factory=list)     # 所有音符值
    velocities: List[int] = field(default_factory=list)

    # 分析结果
    piano_score: float = 0.0              # 钢琴可能性综合评分 0~100
    score_breakdown: dict = field(default_factory=dict)
    is_piano: bool = False
    confidence: str = "low"               # low / medium / high

    @property
    def note_range(self) -> Tuple[int, int]:
        if not self.notes:
            return (0, 0)
        return (min(self.notes), max(self.notes))

    @property
    def note_span(self) -> int:
        lo, hi = self.note_range
        return hi - lo

    @property
    def avg_velocity(self) -> float:
        if not self.velocities:
            return 0.0
        return sum(self.velocities) / len(self.velocities)

    def summary(self) -> str:
        lo, hi = self.note_range
        prog_str = f"Program={self.program}" if self.program is not None else "Program=未知"
        return (
            f"[Track {self.index:02d}] '{self.name}' | {prog_str} | "
            f"Notes={self.note_count} Range={lo}-{hi}({self.note_span}半音) | "
            f"Score={self.piano_score:.1f} {'✅钢琴' if self.is_piano else '❌非钢琴'}"
        )


# ────────────────────────────────────────────────────────────
# 核心分析器
# ────────────────────────────────────────────────────────────
class PianoAnalyzer:
    """
    多维度加权评分的 MIDI 钢琴轨道识别器。

    用法：
        analyzer = PianoAnalyzer("song.mid")
        results = analyzer.analyze()
        piano_tracks = analyzer.get_piano_tracks()
    """

    # 各维度权重（总计 100 分）
    WEIGHTS = {
        "name":      35,   # 轨道名称
        "program":   30,   # GM 音色
        "range":     20,   # 音域特征
        "polyphony": 10,   # 复音/和弦密度
        "velocity":   5,   # 速度分布
    }

    # 判定为钢琴的最低分数阈值
    PIANO_THRESHOLD = 45.0

    def __init__(self, midi_path: str, threshold: Optional[float] = None):
        self.midi_path = midi_path
        self.threshold = threshold if threshold is not None else self.PIANO_THRESHOLD
        self._mid: Optional[mido.MidiFile] = None
        self.tracks: List[TrackInfo] = []

    # ── 公开方法 ────────────────────────────────────────────

    def analyze(self) -> List[TrackInfo]:
        """解析并分析所有轨道，返回 TrackInfo 列表"""
        self._mid = mido.MidiFile(self.midi_path)
        self.tracks = []

        for i, track in enumerate(self._mid.tracks):
            info = self._parse_track(i, track)
            if info.note_count > 0 or info.name:  # 跳过空轨道
                self._score_track(info)
                self.tracks.append(info)

        return self.tracks

    def get_piano_tracks(self) -> List[TrackInfo]:
        """返回识别为钢琴的轨道列表"""
        if not self.tracks:
            self.analyze()
        return [t for t in self.tracks if t.is_piano]

    def get_piano_track_indices(self) -> List[int]:
        """返回钢琴轨道在原始 MidiFile.tracks 中的索引"""
        return [t.index for t in self.get_piano_tracks()]

    # ── 私有：解析 ──────────────────────────────────────────

    def _parse_track(self, idx: int, track: mido.MidiTrack) -> TrackInfo:
        info = TrackInfo(index=idx)

        # 当前各 channel 的 program（防止多 channel 轨道）
        channel_programs: dict[int, int] = {}
        chord_window: List[int] = []   # 用于检测和弦

        for msg in track:
            if msg.type == "track_name":
                info.name = msg.name.strip()

            elif msg.type == "program_change":
                channel_programs[msg.channel] = msg.program
                # 如果是打击乐通道则标记
                if msg.channel == 9:
                    info.is_drum = True
                # 记录第一个或最常见的 program
                if info.program is None:
                    info.program = msg.program
                    info.channel = msg.channel

            elif msg.type == "note_on" and msg.velocity > 0:
                ch = msg.channel
                if ch == 9:
                    info.is_drum = True
                    continue
                info.note_count += 1
                info.notes.append(msg.note)
                info.velocities.append(msg.velocity)
                # 更新该 channel 当前音色
                if ch in channel_programs and info.program is None:
                    info.program = channel_programs[ch]
                    info.channel = ch

        # 最终 program：取最后一次设置（更可靠）
        if channel_programs and info.channel in channel_programs:
            info.program = channel_programs[info.channel]
        elif channel_programs:
            # 取非打击乐 channel 的第一个
            for ch, prog in channel_programs.items():
                if ch != 9:
                    info.program = prog
                    info.channel = ch
                    break

        return info

    # ── 私有：评分 ──────────────────────────────────────────

    def _score_track(self, info: TrackInfo) -> None:
        """计算综合钢琴评分，并设置 is_piano / confidence"""
        if info.is_drum:
            info.piano_score = 0.0
            info.is_piano = False
            info.confidence = "high"
            info.score_breakdown = {"drum_channel": True}
            return

        bd = {}
        total = 0.0

        # 1. 名称评分
        name_score = self._score_name(info.name)
        bd["name"] = round(name_score, 2)
        total += name_score * self.WEIGHTS["name"] / 100

        # 2. GM 音色评分
        prog_score = self._score_program(info.program)
        bd["program"] = round(prog_score, 2)
        total += prog_score * self.WEIGHTS["program"] / 100

        # 3. 音域评分
        range_score = self._score_range(info)
        bd["range"] = round(range_score, 2)
        total += range_score * self.WEIGHTS["range"] / 100

        # 4. 复音/和弦密度
        poly_score = self._score_polyphony(info)
        bd["polyphony"] = round(poly_score, 2)
        total += poly_score * self.WEIGHTS["polyphony"] / 100

        # 5. 速度分布
        vel_score = self._score_velocity(info)
        bd["velocity"] = round(vel_score, 2)
        total += vel_score * self.WEIGHTS["velocity"] / 100

        info.piano_score = round(total, 2)
        info.score_breakdown = bd
        info.is_piano = total >= self.threshold

        # 置信度
        if total >= 75:
            info.confidence = "high"
        elif total >= 50:
            info.confidence = "medium"
        else:
            info.confidence = "low"

    def _score_name(self, name: str) -> float:
        """名称评分：100=确定是钢琴，0=确定不是"""
        if not name:
            return 50.0   # 无名称，中性分
        if _EXCLUDE_RE.search(name):
            return 0.0
        if _PIANO_RE.search(name):
            return 100.0
        return 40.0  # 有名称但未匹配，略偏低

    def _score_program(self, program: Optional[int]) -> float:
        if program is None:
            return 50.0  # 未知，中性
        if program in PIANO_PROGRAMS:
            return 100.0
        if program in KEYBOARD_PROGRAMS:
            return 55.0
        return 0.0

    def _score_range(self, info: TrackInfo) -> float:
        """音域评分：音域越符合钢琴典型范围，分数越高"""
        if not info.notes:
            return 50.0
        lo, hi = info.note_range
        span = info.note_span

        score = 0.0
        # 音域宽度：钢琴典型跨度 30-70 半音
        if span >= 60:
            score += 40
        elif span >= 40:
            score += 35
        elif span >= 20:
            score += 20
        else:
            score += 5

        # 音域范围是否在钢琴范围内
        in_piano_range = (lo >= PIANO_NOTE_MIN and hi <= PIANO_NOTE_MAX)
        if in_piano_range:
            score += 30
        elif lo >= PIANO_NOTE_MIN - 5 and hi <= PIANO_NOTE_MAX + 5:
            score += 15

        # 是否有典型的低音区音符（左手）
        has_bass = any(n < 60 for n in info.notes)
        has_treble = any(n > 60 for n in info.notes)
        if has_bass and has_treble:
            score += 30  # 左右手并存，强烈钢琴特征

        return min(score, 100.0)

    def _score_polyphony(self, info: TrackInfo) -> float:
        """
        钢琴通常有密集和弦。
        简单估计：音符总数多且音域宽表示复音丰富。
        """
        if info.note_count < 10:
            return 30.0
        if info.note_count >= 200:
            return 80.0
        if info.note_count >= 50:
            return 65.0
        return 50.0

    def _score_velocity(self, info: TrackInfo) -> float:
        """
        钢琴的速度变化范围较大（动态表现丰富）。
        标准差大 → 钢琴可能性高
        """
        if len(info.velocities) < 5:
            return 50.0
        avg = info.avg_velocity
        variance = sum((v - avg) ** 2 for v in info.velocities) / len(info.velocities)
        std = variance ** 0.5

        if std >= 25:
            return 80.0
        elif std >= 15:
            return 60.0
        elif std >= 8:
            return 45.0
        else:
            return 30.0


# ────────────────────────────────────────────────────────────
# CLI 快速测试
# ────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("用法: python piano_analyzer.py <midi文件路径>")
        sys.exit(1)

    analyzer = PianoAnalyzer(sys.argv[1])
    tracks = analyzer.analyze()

    print(f"\n共分析 {len(tracks)} 条轨道：\n")
    for t in tracks:
        print(t.summary())
        print(f"   评分细节: {t.score_breakdown}")
    print()
    piano = analyzer.get_piano_tracks()
    print(f"✅ 识别到 {len(piano)} 条钢琴轨道：{[t.index for t in piano]}")
