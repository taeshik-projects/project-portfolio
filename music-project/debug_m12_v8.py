#!/usr/bin/env python3
"""
마디 12-2에서 왜 E가 아니라 G#dim이 선택됐는지 확인
"""

from music21 import converter, pitch
from collections import Counter

filepath = '/Users/tsk/.openclaw/workspace/music-project/ode_to_joy_source.mxl'

score = converter.parse(filepath)
score = score.toSoundingPitch()

# 마디 12-2: 오프셋 45.0 ~ 46.0
start = 45.0
end = 46.0

print("=" * 70)
print("🔍 마디 12-2 근음 후보 디버깅")
print("=" * 70)

# 전체 음들의 raw 빈도
all_pcs = []
for part in score.parts:
    inst = part.getInstrument()
    if inst and 'drum' in inst.instrumentName.lower():
        continue
    
    for elem in part.flatten().notesAndRests:
        ns = elem.offset
        ne = ns + elem.quarterLength
        
        if ns >= end or ne <= start:
            continue
        
        if hasattr(elem, 'pitch'):
            all_pcs.append(elem.pitch.pitchClass)
        elif hasattr(elem, 'pitches'):
            for p in elem.pitches:
                all_pcs.append(p.pitchClass)

pc_counter = Counter(all_pcs)
pc_names = {0:'C', 1:'C#', 2:'D', 3:'Eb', 4:'E', 5:'F', 6:'F#', 7:'G', 8:'G#', 9:'A', 10:'Bb', 11:'B'}

print("\n피치 클래스 빈도:")
for pc, count in pc_counter.most_common():
    print(f"  {pc:2d} ({pc_names[pc]:3s}): {count}회")

print("\n근음 후보 (Top 3):")
most_common = pc_counter.most_common(3)
for pc, count in most_common:
    print(f"  {pc:2d} ({pc_names[pc]:3s}): {count}회")

# 각 근음으로 템플릿 매칭 시뮬레이션
print("\n" + "=" * 70)
print("각 근음 후보로 코드 매칭:")
print("=" * 70)

pcs_set = set(all_pcs)

CHORD_TEMPLATES = {
    'major': [0, 4, 7],
    'minor': [0, 3, 7],
    'dom7': [0, 4, 7, 10],
    'diminished': [0, 3, 6],
}

for pc, count in most_common:
    root_name = pc_names[pc]
    
    print(f"\n근음: {root_name} (PC={pc}, 빈도={count})")
    
    intervals = set()
    for p in pcs_set:
        interval = (p - pc) % 12
        intervals.add(interval)
    
    print(f"  근음 대비 간격: {sorted(intervals)}")
    
    print(f"  템플릿 매칭:")
    for chord_type, template in CHORD_TEMPLATES.items():
        matches = len(intervals & set(template))
        score = matches / len(template)
        
        extra = len(intervals - set(template))
        if extra > 1:
            score -= 0.05 * extra
        
        print(f"    {chord_type:12s}: {matches}/{len(template)} = {score:.2f}")
