import mido
from mido import Message, MidiFile, MidiTrack, MetaMessage

def create_test_midi():
    # 创建一個多轨 MIDI 文件 (type=1 代表多轨道同步)
    mid = MidiFile(type=1)

    # ==========================================
    # 轨道 0：全局控制轨 (通常用来放速度、拍号等全局信息)
    # ==========================================
    track0 = MidiTrack()
    mid.tracks.append(track0)
    track0.append(MetaMessage('track_name', name='Global Settings', time=0))
    track0.append(MetaMessage('set_tempo', tempo=mido.bpm2tempo(120), time=0))

    # ==========================================
    # 轨道 1：主旋律 (钢琴 - 通道 0)
    # ==========================================
    track1 = MidiTrack()
    mid.tracks.append(track1)
    track1.append(MetaMessage('track_name', name='Piano Melody', time=0))
    track1.append(Message('program_change', program=0, channel=0, time=0)) # 0 代表大鋼琴
    
    # 彈奏一個 C 大調和弦 (C4, E4, G4)，同時按下！
    track1.append(Message('note_on', note=60, velocity=80, channel=0, time=0))
    track1.append(Message('note_on', note=64, velocity=80, channel=0, time=0))
    track1.append(Message('note_on', note=67, velocity=80, channel=0, time=0))
    
    # 经过 480 个 ticks (通常是一拍) 侯，同时松开
    track1.append(Message('note_off', note=60, velocity=64, channel=0, time=480))
    track1.append(Message('note_off', note=64, velocity=64, channel=0, time=0))
    track1.append(Message('note_off', note=67, velocity=64, channel=0, time=0))

    # ==========================================
    # 軌道 2：低音伴奏 (電貝斯 - 通道 1)
    # ==========================================
    track2 = MidiTrack()
    mid.tracks.append(track2)
    track2.append(MetaMessage('track_name', name='Electric Bass', time=0))
    track2.append(Message('program_change', program=33, channel=1, time=0)) # 33 代表電貝斯
    
    # 貝斯在同一個時間點彈奏低音 C2
    track2.append(Message('note_on', note=36, velocity=100, channel=1, time=0))
    track2.append(Message('note_off', note=36, velocity=64, channel=1, time=480))

    # ==========================================
    # 軌道 3：打擊樂 (架子鼓 - 專屬通道 9)
    # ==========================================
    track3 = MidiTrack()
    mid.tracks.append(track3)
    track3.append(MetaMessage('track_name', name='Drum Kit', time=0))
    # 注意：通道 9 不需要發送 program_change，它默認就是鼓
    
    # 咚 (底鼓 Bass Drum)
    track3.append(Message('note_on', note=35, velocity=127, channel=9, time=0))
    track3.append(Message('note_off', note=35, velocity=64, channel=9, time=240))
    # 次 (軍鼓 Snare)
    track3.append(Message('note_on', note=38, velocity=127, channel=9, time=0))
    track3.append(Message('note_off', note=38, velocity=64, channel=9, time=240))

    # 保存文件
    file_name = 'hardcore_split_test.mid'
    mid.save(file_name)
    print(f"完成喵！測試文件已保存為：{file_name} ( ^ω^ )")

if __name__ == '__main__':
    create_test_midi()
