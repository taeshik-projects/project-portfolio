#!/usr/bin/env python3
"""
마디 4 디버깅: D(1-2박) vs A(3-4박)
"""

from music21 import converter
from collections import Counter

filepath = '/Users/tsk/.openclaw/workspace/music-project/ode_to_joy_source.mxl'

print("=" * 70)
print("🔍 마디 4 디버깅")
print("=" * 70)

score = converter.parse(filepath)
score = score.toSoundingPitch()

def classify_role(part):
    instrument = part.getInstrument()
    if not instrument:
        return 'inner'
    name = instrument.instrumentName.lower()
    if any(kw in name for kw in ['bass', 'cello', 'tuba', 'bassoon', 'contrabass']):
        return 'bass'
    return 'other'

bass_parts = [p for p in score.parts if classify_role(p) == 'bass']

print(f"\n베이스 파트 {len(bass_parts)}개")

# 마디 4 = 오프셋 12.0 ~ 16.0
measure_start = 12.0

for segment_name, seg_start, seg_end in [("전반부(1-2박)", 12.0, 14.0), ("후반부(3-4박)", 14.0, 16.0)]:
    print(f"\n{'='*70}")
    print(f"📊 {segment_name} (오프셋 {seg_start} ~ {seg_end})")
    print('='*70)
    
    # 베이스 음들
    print("\n베이스 파트의 음들:")
    bass_notes = []
    
    for part in bass_parts:
        part_name = part.partName
        for element in part.flatten().notesAndRests:
            note_start = element.offset
            note_end = note_start + element.quarterLength
            
            if note_start >= seg_end or note_end <= seg_start:
                continue
            
            overlap = min(note_end, seg_end) - max(note_start, seg_start)
            
            if hasattr(element, 'pitch'):
                print(f"  {part_name:20s}: {element.pitch.nameWithOctave:6s} (오프셋 {note_start:.1f}, 길이 {element.quarterLength:.1f}, 겹침 {overlap:.1f})")
                bass_notes.append({
                    'pitch': element.pitch.name,
                    'pc': element.pitch.pitchClass,
                    'overlap': overlap
                })
            elif hasattr(element, 'pitches') and len(element.pitches) > 0:
                lowest = min(element.pitches, key=lambda p: p.midi)
                print(f"  {part_name:20s}: {lowest.nameWithOctave:6s} (코드, 오프셋 {note_start:.1f}, 길이 {element.quarterLength:.1f}, 겹침 {overlap:.1f})")
                bass_notes.append({
                    'pitch': lowest.name,
                    'pc': lowest.pitchClass,
                    'overlap': overlap
                })
    
    # Pitch class 빈도
    pc_counter = Counter([b['pc'] for b in bass_notes])
    print(f"\n피치 클래스 빈도:")
    pc_names = {0:'C', 2:'D', 4:'E', 5:'F', 7:'G', 9:'A', 11:'B', 1:'C#', 3:'Eb', 6:'F#', 8:'G#', 10:'Bb'}
    for pc, count in pc_counter.most_common():
        print(f"  {pc:2d} ({pc_names[pc]:3s}): {count}회")
    
    most_common_pc = pc_counter.most_common(1)[0][0] if pc_counter else None
    print(f"\n→ 가장 흔한 PC: {most_common_pc} ({pc_names.get(most_common_pc, '?')})")
    
    # 전체 음들 (모든 악기)
    print(f"\n전체 악기의 음들:")
    all_pitches = []
    
    for part in score.parts:
        instrument = part.getInstrument()
        if instrument and 'drum' in instrument.instrumentName.lower():
            continue
        
        for element in part.flatten().notesAndRests:
            note_start = element.offset
            note_end = note_start + element.quarterLength
            
            if note_start >= seg_end or note_end <= seg_start:
                continue
            
            if hasattr(element, 'pitch'):
                all_pitches.append(element.pitch.name)
            elif hasattr(element, 'pitches'):
                for p in element.pitches:
                    all_pitches.append(p.name)
    
    pitch_counter = Counter(all_pitches)
    print(f"\n음 이름 빈도 (Top 10):")
    for pitch, count in pitch_counter.most_common(10):
        print(f"  {pitch}: {count}회")
    
    # 피치 클래스
    pc_map = {'C':0, 'D':2, 'E':4, 'F':5, 'G':7, 'A':9, 'B':11, 'C#':1, 'D#':3, 'F#':6, 'G#':8, 'A#':10}
    all_pcs = sorted(set([pc_map.get(p, -1) for p in all_pitches if p in pc_map]))
    print(f"\n피치 클래스: {all_pcs}")
    print(f"음 이름: {sorted(set(all_pitches))}")
