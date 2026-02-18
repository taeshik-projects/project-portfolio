#!/usr/bin/env python3
"""
V4 알고리즘에서 마디 1의 코드 추론 과정 디버깅
"""

from music21 import converter
from collections import defaultdict

filepath = '/Users/tsk/.openclaw/workspace/music-project/ode_to_joy_source.mxl'

print("=" * 70)
print("🔍 V4 코드 추론 디버깅: 마디 1")
print("=" * 70)

score = converter.parse(filepath)
score = score.toSoundingPitch()

# 베이스 파트 찾기
def classify_role(part):
    instrument = part.getInstrument()
    if not instrument:
        return 'inner'
    name = instrument.instrumentName.lower()
    if any(kw in name for kw in ['bass', 'cello', 'tuba', 'bassoon', 'contrabass']):
        return 'bass'
    return 'other'

bass_parts = [p for p in score.parts if classify_role(p) == 'bass']

print(f"\n베이스 파트 {len(bass_parts)}개:")
for bp in bass_parts:
    print(f"  - {bp.partName}")

# 마디 1의 베이스 음들 (1박자 이상)
print("\n마디 1 베이스 음들 (1박자 이상):")

bass_notes_m1 = []

for part in bass_parts:
    measures = part.getElementsByClass('Measure')
    if len(measures) == 0:
        continue
    
    measure1 = measures[0]
    
    for element in measure1.flatten().notesAndRests:
        if element.quarterLength < 1.0:
            continue
        
        if hasattr(element, 'pitch'):
            bass_notes_m1.append({
                'offset': element.offset,
                'pitch': element.pitch.nameWithOctave,
                'pc': element.pitch.pitchClass,
                'duration': element.quarterLength,
                'part': part.partName
            })
        elif hasattr(element, 'pitches') and len(element.pitches) > 0:
            lowest = min(element.pitches, key=lambda p: p.midi)
            bass_notes_m1.append({
                'offset': element.offset,
                'pitch': lowest.nameWithOctave,
                'pc': lowest.pitchClass,
                'duration': element.quarterLength,
                'part': part.partName
            })

bass_notes_m1.sort(key=lambda x: x['offset'])

for bn in bass_notes_m1:
    print(f"  오프셋 {bn['offset']:.1f}: {bn['pitch']:6s} (길이 {bn['duration']:.1f}박자) - {bn['part']}")

# 베이스 변화 지점
print("\n베이스 변화 지점:")
bass_changes = []
prev_pc = None

for bn in bass_notes_m1:
    pc = bn['pc']
    if prev_pc is None or pc != prev_pc:
        bass_changes.append((bn['offset'], bn['pitch'], bn['pc']))
        prev_pc = pc
        print(f"  오프셋 {bn['offset']:.1f}: {bn['pitch']} (PC={bn['pc']})")

# 각 변화 지점의 코드 추론
print("\n각 구간의 실제 음들:")

def get_pitches(start, end):
    """시간 구간의 모든 음 수집"""
    pitches = []
    for part in score.parts:
        instrument = part.getInstrument()
        if instrument and 'drum' in instrument.instrumentName.lower():
            continue
        
        measures = part.getElementsByClass('Measure')
        if len(measures) == 0:
            continue
        
        measure1 = measures[0]
        
        for element in measure1.flatten().notesAndRests:
            note_start = element.offset
            note_end = note_start + element.quarterLength
            
            if note_start >= end or note_end <= start:
                continue
            
            if hasattr(element, 'pitch'):
                pitches.append(element.pitch.name)
            elif hasattr(element, 'pitches'):
                for p in element.pitches:
                    pitches.append(p.name)
    
    return pitches

for i, (offset, pitch, pc) in enumerate(bass_changes):
    if i < len(bass_changes) - 1:
        next_offset = bass_changes[i + 1][0]
    else:
        next_offset = 4.0  # 마디 끝
    
    pitches = get_pitches(offset, next_offset)
    unique_pitches = sorted(set(pitches))
    pitch_counter = {}
    for p in pitches:
        pitch_counter[p] = pitch_counter.get(p, 0) + 1
    
    print(f"\n구간 오프셋 {offset:.1f} ~ {next_offset:.1f}:")
    print(f"  베이스: {pitch}")
    print(f"  모든 음: {unique_pitches}")
    print(f"  빈도: {pitch_counter}")
    
    # 피치 클래스
    pc_map = {'C':0, 'D':2, 'E':4, 'F':5, 'G':7, 'A':9, 'B':11, 'C#':1, 'D#':3, 'F#':6, 'G#':8, 'A#':10}
    pitch_classes = sorted(set([pc_map.get(p, -1) for p in unique_pitches if p in pc_map]))
    print(f"  피치 클래스: {pitch_classes}")
