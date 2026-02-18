#!/usr/bin/env python3
"""
마디 9, 마디 12-2 디버깅 (간소화)
"""

from music21 import converter
from collections import Counter

filepath = '/Users/tsk/.openclaw/workspace/music-project/ode_to_joy_source.mxl'

print("=" * 70)
print("🔍 코드 인식 오류 디버깅")
print("=" * 70)

music_score = converter.parse(filepath)
music_score = music_score.toSoundingPitch()

def get_bass_parts(music_score):
    """베이스 파트 필터"""
    bass_result = []
    for p in music_score.parts:
        inst = p.getInstrument()
        if inst and any(kw in inst.instrumentName.lower() for kw in ['bass', 'cello', 'tuba', 'bassoon']):
            bass_result.append(p)
    return bass_result

bass_parts_list = get_bass_parts(music_score)

def debug_segment(name, start, end):
    """구간 디버깅"""
    print(f"\n{'='*70}")
    print(f"📊 {name} (오프셋 {start} ~ {end})")
    print('='*70)
    
    print("\n[베이스 음들]")
    bass_notes = []
    
    for part in bass_parts_list:
        for elem in part.flatten().notesAndRests:
            ns = elem.offset
            ne = ns + elem.quarterLength
            
            if ns >= end or ne <= start:
                continue
            
            overlap = min(ne, end) - max(ns, start)
            
            if hasattr(elem, 'pitch'):
                print(f"  {part.partName:20s}: {elem.pitch.nameWithOctave:6s} (길이 {elem.quarterLength:.2f})")
                bass_notes.append({'name': elem.pitch.name, 'pc': elem.pitch.pitchClass, 'dur': elem.quarterLength})
            elif hasattr(elem, 'pitches') and len(elem.pitches) > 0:
                lowest = min(elem.pitches, key=lambda p: p.midi)
                print(f"  {part.partName:20s}: {lowest.nameWithOctave:6s} (코드, 길이 {elem.quarterLength:.2f})")
                bass_notes.append({'name': lowest.name, 'pc': lowest.pitchClass, 'dur': elem.quarterLength})
    
    # 빈도
    pc_counter = Counter([b['pc'] for b in bass_notes])
    pc_names = {0:'C', 1:'C#', 2:'D', 3:'Eb', 4:'E', 5:'F', 6:'F#', 7:'G', 8:'G#', 9:'A', 10:'Bb', 11:'B'}
    
    print(f"\n베이스 피치 클래스 빈도:")
    for pc, count in pc_counter.most_common():
        print(f"  {pc:2d} ({pc_names[pc]:3s}): {count}회")
    
    # 전체 음들
    all_pitches = []
    for part in music_score.parts:
        inst = part.getInstrument()
        if inst and 'drum' in inst.instrumentName.lower():
            continue
        
        for elem in part.flatten().notesAndRests:
            ns = elem.offset
            ne = ns + elem.quarterLength
            
            if ns >= end or ne <= start:
                continue
            
            if hasattr(elem, 'pitch'):
                all_pitches.append(elem.pitch.name)
            elif hasattr(elem, 'pitches'):
                for p in elem.pitches:
                    all_pitches.append(p.name)
    
    pitch_counter = Counter(all_pitches)
    print(f"\n전체 음 빈도:")
    for pitch, count in pitch_counter.most_common(10):
        print(f"  {pitch}: {count}회")
    
    # 피치 클래스
    pc_map = {'C':0, 'C#':1, 'D':2, 'Eb':3, 'E':4, 'F':5, 'F#':6, 'G':7, 'G#':8, 'A':9, 'Bb':10, 'B':11}
    pcs = sorted(set([pc_map.get(p, -1) for p in all_pitches if p in pc_map]))
    print(f"\n피치 클래스: {pcs}")
    print(f"음 이름: {sorted(set(all_pitches))}")

# 마디 9 (박 1-2)
debug_segment("마디 9 (박 1-2) - C#m 오류", 32.0, 34.0)

# 마디 12 (박 2)
debug_segment("마디 12 (박 2) - G#dim 오류", 45.0, 46.0)
