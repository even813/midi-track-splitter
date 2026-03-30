# -*- coding: utf-8 -*-
"""test_midi.py - 生成测试MIDI并验证分轨功能"""
import mido
import sys
import io

# 强制UTF-8输出（解决Windows GBK问题）
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# 创建测试MIDI（含钢琴轨 + 弦乐轨 + 鼓轨）
mid = mido.MidiFile(type=1, ticks_per_beat=480)

# 轨道0：Meta
meta = mido.MidiTrack()
meta.append(mido.MetaMessage('set_tempo', tempo=500000, time=0))
meta.append(mido.MetaMessage('time_signature', numerator=4, denominator=4, time=0))
mid.tracks.append(meta)

# 轨道1：钢琴（Program 0, 宽音域含左右手）
piano = mido.MidiTrack()
piano.append(mido.MetaMessage('track_name', name='Piano', time=0))
piano.append(mido.Message('program_change', channel=0, program=0, time=0))
for note in [36, 48, 60, 72, 84, 96, 48, 52, 55, 60, 40, 45]:
    piano.append(mido.Message('note_on', channel=0, note=note, velocity=80, time=0))
    piano.append(mido.Message('note_off', channel=0, note=note, velocity=0, time=240))
mid.tracks.append(piano)

# 轨道2：弦乐（Program 48）
strings = mido.MidiTrack()
strings.append(mido.MetaMessage('track_name', name='Strings', time=0))
strings.append(mido.Message('program_change', channel=1, program=48, time=0))
for note in [60, 64, 67]:
    strings.append(mido.Message('note_on', channel=1, note=note, velocity=60, time=0))
    strings.append(mido.Message('note_off', channel=1, note=note, velocity=0, time=480))
mid.tracks.append(strings)

# 轨道3：鼓（channel 9）
drums = mido.MidiTrack()
drums.append(mido.MetaMessage('track_name', name='Drums', time=0))
for n in [36, 38, 42]:
    drums.append(mido.Message('note_on', channel=9, note=n, velocity=100, time=0))
    drums.append(mido.Message('note_off', channel=9, note=n, velocity=0, time=240))
mid.tracks.append(drums)

mid.save('test_input.mid')
print('TEST MIDI CREATED: test_input.mid (4 tracks: Meta + Piano + Strings + Drums)')

# === 运行分析 ===
from piano_analyzer import PianoAnalyzer
analyzer = PianoAnalyzer('test_input.mid')
tracks = analyzer.analyze()

print(f'\nAnalyzed {len(tracks)} tracks:')
for t in tracks:
    piano_flag = "[PIANO]" if t.is_piano else "[skip]"
    print(f"  {piano_flag} Track#{t.index} '{t.name}' score={t.piano_score:.1f} conf={t.confidence}")

# === 提取 ===
from piano_extractor import extract_piano
result = extract_piano('test_input.mid', 'test_output_piano.mid')

print(f'\nExtract result: {result.message}')
print(f'Success: {result.success}')
if result.success:
    import os
    size = os.path.getsize('test_output_piano.mid')
    print(f'Output file size: {size} bytes')
    print('ALL TESTS PASSED!')
