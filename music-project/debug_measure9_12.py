#!/usr/bin/env python3
"""
마디 9 (C#m 오류)와 마디 12 박자 2 (G#dim 오류) 디버깅
"""

from music21 import converter
from collections import Counter, defaultdict

filepath = '/Users/tsk/.openclaw/workspace/music-project/ode_to_joy_source.mxl'

print("=" * 70)
print("🔍 코드 인식 오류 디버깅")
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
    elif any(kw in name for kw in ['violin', 'flute', 'soprano', 'oboe', 'clarinet']):
        return 'melody'
    else:
        return 'inner'

def analyze_segment(score, segment_name, start_offset, end_offset):
    """특정 구간의 음들 분석"""
    print(f"\n{'='*70}")
    print(f"📊 {segment_name} (오프셋 {start_offset} ~ {end_offset})")
    print('='*70)
    
    # 베이스 파트
    bass_parts = [p for p in score.parts if classify_role(p) == 'bass']
    
    print("\n[베이스 음들]")
    bass_pitches = []
    
    for part in bass_parts:
        part_name = part.partName
        for element in part.flatten().notesAndRests:
            note_start = element.offset
            note_end = note_start + element.quarterLength
            
            if note_start >= end_offset or note_end <= start_offset:
                continue
            
            overlap = min(note_end, end_offset) - max(note_start, start_offset)
            if overlap <= 0:
                continue
            
            if hasattr(element, 'pitch'):
                print(f"  {part_name:20s}: {element.pitch.nameWithOctave:6s} (길이 {element.quarterLength:.2f}, 겹침 {overlap:.2f})")
                bass_pitches.append({
                    'pitch': element.pitch.name,
                    'pc': element.pitch.pitchClass,
                    'duration': element.quarterLength,
                    'overlap': overlap
                })
            elif hasattr(element, 'pitches') and len(element.pitches) > 0:
                lowest = min(element.pitches, key=lambda p: p.midi)
                print(f"  {part_name:20s}: {lowest.nameWithOctave:6s} (코드, 길이 {element.quarterLength:.2f}, 겹침 {overlap:.2f})")
                bass_pitches.append({
                    'pitch': lowest.name,
                    'pc': lowest.pitchClass,
                    'duration': element.quarterLength,
                    'overlap': overlap
                })
    
    # 베이스 가중치 계산
    bass_scores = defaultdict(float)
    for b in bass_pitches:
        duration_weight = 0.1 if b['duration'] < 0.5 else (1.0 if b['duration'] < 1.0 else 2.0)
        score = duration_weight * b['overlap']
        bass_scores[b['pc']] += score
    
    if bass_scores:
        best_pc = max(bass_scores, key=bass_scores.get)
        pc_names = {0:'C', 1:'C#', 2:'D', 3:'Eb', 4:'E', 5:'F', 6:'F#', 7:'G', 8:'G#', 9:'A', 10:'Bb', 11:'B'}
        print(f"\n→ 베이스 가중치: {dict(bass_scores)}")
        print(f"→ 선택된 베이스: PC={best_pc} ({pc_names[best_pc]})")
    
    # 전체 음들
    print("\n[전체 악기의 음들 (가중치 적용)]")
    
    pitch_class_weights = defaultdict(float)
    all_pitches_raw = []
    
    for part in score.parts:
        role = classify_role(part)
        role_weight = {'bass': 2.0, 'inner': 2.0, 'melody': 0.3}.get(role, 1.0)
        
        instrument = part.getInstrument()
        if instrument and 'drum' in instrument.instrumentName.lower():
            continue
        
        for element in part.flatten().notesAndRests:
            note_start = element.offset
            note_end = note_start + element.quarterLength
            
            if note_start >= end_offset or note_end <= start_offset:
                continue
            
            overlap = min(note_end, end_offset) - max(note_start, start_offset)
            if overlap <= 0:
                continue
            
            # Duration 가중치
            if element.quarterLength < 0.5:
                duration_weight = 0.2
            elif element.quarterLength < 1.0:
                duration_weight = 1.0
            else:
                duration_weight = 2.0
            
            # 강박 보너스
            beat_pos = note_start % 4.0
            if beat_pos in [0.0, 2.0]:
                beat_weight = 1.5
            else:
                beat_weight = 1.0
            
            total_weight = role_weight * duration_weight * beat_weight * overlap
            
            if hasattr(element, 'pitch'):
                pc = element.pitch.pitchClass
                pitch_class_weights[pc] += total_weight
                all_pitches_raw.append(element.pitch.name)
            elif hasattr(element, 'pitches'):
                for p in element.pitches:
                    pc = p.pitchClass
                    pitch_class_weights[pc] += total_weight
                    all_pitches_raw.append(p.name)
    
    # 피치 클래스 출력
    pc_names = {0:'C', 1:'C#', 2:'D', 3:'Eb', 4:'E', 5:'F', 6:'F#', 7:'G', 8:'G#', 9:'A', 10:'Bb', 11:'B'}
    
    print("\n피치 클래스 가중치:")
    for pc in sorted(pitch_class_weights.keys()):
        print(f"  {pc:2d} ({pc_names[pc]:3s}): {pitch_class_weights[pc]:.2f}")
    
    # 실제 음 카운트 (가중치 없음)
    pitch_counter = Counter(all_pitches_raw)
    print("\n실제 음 빈도 (가중치 전):")
    for pitch, count in sorted(pitch_counter.items()):
        print(f"  {pitch}: {count}회")
    
    # 코드 매칭 시뮬레이션
    if bass_scores:
        best_bass_pc = max(bass_scores, key=bass_scores.get)
        print(f"\n[코드 매칭 시뮬레이션]")
        print(f"베이스: {pc_names[best_bass_pc]}")
        
        intervals = set()
        for pc in pitch_class_weights.keys():
            interval = (pc - best_bass_pc) % 12
            intervals.add(interval)
        
        print(f"근음 대비 간격: {sorted(intervals)}")
        
        # 템플릿 매칭
        CHORD_TEMPLATES = {
            'major': [0, 4, 7],
            'minor': [0, 3, 7],
            'dom7': [0, 4, 7, 10],
            'diminished': [0, 3, 6],
        }
        
        print("\n템플릿 매칭 결과:")
        for chord_type, template in CHORD_TEMPLATES.items():
            matches = len(intervals & set(template))
            match_score = matches / len(template)
            print(f"  {chord_type:12s}: {matches}/{len(template)} = {match_score:.2f}")

# 마디 9, 첫 반마디 (박 1-2) = 오프셋 32.0 ~ 34.0
analyze_segment(score, "마디 9 (박 1-2) - C#m 오류", 32.0, 34.0)

# 마디 12, 두 번째 박자 = 오프셋 45.0 ~ 46.0
analyze_segment(score, "마디 12 (박 2) - G#dim 오류", 45.0, 46.0)
