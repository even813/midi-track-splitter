"""
piano_extractor.py
────────────────────────────────────────────────────────────
MIDI 钢琴分轨提取器

支持两种模式：
  - 轨道模式（Type 1 MIDI）：直接提取钢琴轨道
  - 通道模式（Type 0 MIDI）：按 channel 过滤，重组为新 MIDI

输出选项：
  - 仅钢琴（默认）
  - 钢琴 + 全局 Meta 轨道（保留 BPM/时间签名等）
  - 原始文件去掉非钢琴轨道

"""

from __future__ import annotations

import os
from pathlib import Path
from typing import List, Optional, Union

try:
    import mido
except ImportError:
    raise ImportError("请先安装 mido：pip install mido")

from piano_analyzer import PianoAnalyzer, TrackInfo


class ExtractionResult:
    """分轨操作结果"""
    def __init__(self):
        self.success: bool = False
        self.output_path: str = ""
        self.piano_track_count: int = 0
        self.total_track_count: int = 0
        self.piano_note_count: int = 0
        self.message: str = ""
        self.piano_tracks: List[TrackInfo] = []

    def __repr__(self):
        return (
            f"ExtractionResult(success={self.success}, "
            f"piano={self.piano_track_count}/{self.total_track_count} tracks, "
            f"notes={self.piano_note_count}, output='{self.output_path}')"
        )


class PianoExtractor:
    """
    MIDI 钢琴分轨提取器

    用法示例：
        extractor = PianoExtractor()
        result = extractor.extract("input.mid", "output_piano.mid")
        print(result)
    """

    def __init__(
        self,
        threshold: float = 45.0,
        keep_meta_track: bool = True,
        preserve_tempo: bool = True,
    ):
        """
        Args:
            threshold: 钢琴判定阈值（0-100），越高越严格
            keep_meta_track: 是否保留全局 Meta 轨道（含 BPM/时间签名）
            preserve_tempo: 是否确保输出包含速度信息
        """
        self.threshold = threshold
        self.keep_meta_track = keep_meta_track
        self.preserve_tempo = preserve_tempo

    # ── 公开接口 ────────────────────────────────────────────

    def extract(
        self,
        input_path: Union[str, Path],
        output_path: Union[str, Path],
        manual_track_indices: Optional[List[int]] = None,
    ) -> ExtractionResult:
        """
        从 MIDI 文件提取钢琴轨道并保存

        Args:
            input_path: 输入 MIDI 文件路径
            output_path: 输出 MIDI 文件路径
            manual_track_indices: 手动指定轨道索引（None = 自动识别）

        Returns:
            ExtractionResult 对象
        """
        result = ExtractionResult()
        input_path = Path(input_path)
        output_path = Path(output_path)

        # ── 读取并分析 ──────────────────────────────────────
        try:
            mid = mido.MidiFile(str(input_path))
        except Exception as e:
            result.message = f"无法读取 MIDI 文件：{e}"
            return result

        analyzer = PianoAnalyzer(str(input_path), threshold=self.threshold)
        all_tracks = analyzer.analyze()
        result.total_track_count = len(mid.tracks)

        # ── 确定要提取的轨道 ───────────────────────────────
        if manual_track_indices is not None:
            piano_infos = [t for t in all_tracks if t.index in manual_track_indices]
        else:
            piano_infos = analyzer.get_piano_tracks()

        result.piano_tracks = piano_infos
        result.piano_track_count = len(piano_infos)

        if not piano_infos:
            result.message = "未检测到钢琴轨道，请尝试降低识别阈值或手动指定轨道"
            return result

        # ── 构建输出 MIDI ──────────────────────────────────
        piano_indices = {t.index for t in piano_infos}

        if mid.type == 0:
            # Type 0：单轨多 channel，需要 channel 过滤
            new_mid = self._extract_type0(mid, piano_infos)
        else:
            # Type 1/2：多轨
            new_mid = self._extract_type1(mid, piano_indices)

        # ── 统计音符 ────────────────────────────────────────
        result.piano_note_count = sum(t.note_count for t in piano_infos)

        # ── 保存 ────────────────────────────────────────────
        output_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            new_mid.save(str(output_path))
        except Exception as e:
            result.message = f"保存失败：{e}"
            return result

        result.success = True
        result.output_path = str(output_path)
        result.message = (
            f"成功提取 {len(piano_infos)} 条钢琴轨道，"
            f"共 {result.piano_note_count} 个音符"
        )
        return result

    def get_track_analysis(self, input_path: Union[str, Path]) -> List[TrackInfo]:
        """仅分析，不提取，返回所有轨道信息"""
        analyzer = PianoAnalyzer(str(input_path), threshold=self.threshold)
        return analyzer.analyze()

    # ── 私有：Type 0 处理 ────────────────────────────────────

    def _extract_type0(
        self, mid: mido.MidiFile, piano_infos: List[TrackInfo]
    ) -> mido.MidiFile:
        """
        Type 0 MIDI（单轨）：过滤出钢琴 channel 的消息，
        转换为 Type 1 多轨输出。
        """
        piano_channels = {t.channel for t in piano_infos if t.channel is not None}

        new_mid = mido.MidiFile(type=1, ticks_per_beat=mid.ticks_per_beat)

        # Meta 轨道：保留所有非 note 消息
        meta_track = mido.MidiTrack()
        meta_track.name = "Meta"
        piano_track = mido.MidiTrack()
        piano_track.name = "Piano"

        source_track = mid.tracks[0]

        for msg in source_track:
            if msg.is_meta:
                meta_track.append(msg.copy())
            elif hasattr(msg, "channel"):
                if msg.channel in piano_channels:
                    piano_track.append(msg.copy())
            else:
                meta_track.append(msg.copy())

        if self.keep_meta_track:
            new_mid.tracks.append(meta_track)
        new_mid.tracks.append(piano_track)

        return new_mid

    # ── 私有：Type 1 处理 ────────────────────────────────────

    def _extract_type1(
        self, mid: mido.MidiFile, piano_indices: set
    ) -> mido.MidiFile:
        """
        Type 1 MIDI（多轨）：提取钢琴轨道，可选保留 Meta 轨道。
        """
        new_mid = mido.MidiFile(type=1, ticks_per_beat=mid.ticks_per_beat)

        for i, track in enumerate(mid.tracks):
            if i == 0 and self.keep_meta_track:
                # 第 0 轨通常是全局 Meta（BPM/时间签名）
                # 检查是否为纯 Meta 轨道
                if self._is_meta_only_track(track):
                    new_mid.tracks.append(track)
                    continue

            if i in piano_indices:
                new_mid.tracks.append(track)
            elif self.keep_meta_track and self._is_meta_only_track(track):
                # 其他纯 Meta 轨道也保留（如时间签名轨）
                new_mid.tracks.append(track)

        # 若 Meta 轨道未被加入，但 preserve_tempo 要求保留 BPM，
        # 则从原文件扫描并注入
        if self.preserve_tempo and len(new_mid.tracks) > 0:
            self._ensure_tempo(mid, new_mid)

        return new_mid

    @staticmethod
    def _is_meta_only_track(track: mido.MidiTrack) -> bool:
        """判断轨道是否只含 Meta 消息（无音符）"""
        for msg in track:
            if not msg.is_meta and msg.type not in ("sysex",):
                return False
        return True

    @staticmethod
    def _ensure_tempo(
        source: mido.MidiFile, target: mido.MidiFile
    ) -> None:
        """
        确保目标 MIDI 包含速度（tempo）信息。
        如果目标第一轨没有 set_tempo，则从源文件提取并注入。
        """
        if not target.tracks:
            return

        # 检查目标是否已有 tempo
        has_tempo = any(
            msg.type == "set_tempo"
            for track in target.tracks
            for msg in track
            if msg.is_meta
        )
        if has_tempo:
            return

        # 从源文件收集 tempo 消息
        tempo_msgs = []
        for track in source.tracks:
            for msg in track:
                if msg.is_meta and msg.type == "set_tempo":
                    tempo_msgs.append(msg.copy())
                    break
            if tempo_msgs:
                break

        if tempo_msgs:
            # 注入到第一条轨道的开头
            target.tracks[0].insert(0, tempo_msgs[0])


# ────────────────────────────────────────────────────────────
# 便捷函数
# ────────────────────────────────────────────────────────────

def extract_piano(
    input_path: str,
    output_path: Optional[str] = None,
    threshold: float = 45.0,
) -> ExtractionResult:
    """
    一行调用的便捷函数。

    Args:
        input_path: 输入 MIDI 路径
        output_path: 输出路径（None = 自动生成）
        threshold: 识别阈值

    Returns:
        ExtractionResult
    """
    if output_path is None:
        p = Path(input_path)
        output_path = str(p.parent / f"{p.stem}_piano{p.suffix}")

    extractor = PianoExtractor(threshold=threshold)
    return extractor.extract(input_path, output_path)


# ────────────────────────────────────────────────────────────
# CLI 快速使用
# ────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("用法: python piano_extractor.py <input.mid> [output.mid] [threshold]")
        sys.exit(1)

    inp = sys.argv[1]
    out = sys.argv[2] if len(sys.argv) > 2 else None
    thr = float(sys.argv[3]) if len(sys.argv) > 3 else 45.0

    res = extract_piano(inp, out, thr)
    print(f"\n{'✅ 成功' if res.success else '❌ 失败'}：{res.message}")
    if res.success:
        print(f"输出文件：{res.output_path}")
        print(f"钢琴轨道：")
        for t in res.piano_tracks:
            print(f"  {t.summary()}")
