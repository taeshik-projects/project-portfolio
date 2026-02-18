#!/usr/bin/env python3
"""
코드 진행 추출 V6 - 스마트 분석
- 반마디(2박자) 단위로 분석 (중간 코드 전환 감지)
- Duration 가중치 (긴 음 = 코드 구성음, 짧은 음 = passing note)
- 강박 가중치 (1박, 3박 > 2박, 4박)
"""

from music21 import converter
from collections import defaultdict
import json

CHORD_TEMPLATES = {
    'major': [0, 4, 7],
    'minor': [0, 3, 7],
    'dom7': [0, 4, 7, 10],
    'min7': [0, 3, 7, 10],
    'diminished': [0, 3, 6],
    'augmented': [0, 4, 8],
}

def classify_role(part):
    """악기 역할"""
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


def get_segment_bass(score, bass_parts, start_offset, end_offset):
    """
    특정 시간 구간의 베이스 음 추출
    - 가장 많은 악기가 연주하는 pitch class 선택
    - 그 중에서 가장 긴 duration
    """
    from collections import Counter
    
    bass_candidates = []
    
    for part in bass_parts:
        for element in part.flatten().notesAndRests:
            note_start = element.offset
            note_end = note_start + element.quarterLength
            
            # 구간과 겹치는지
            if note_start >= end_offset or note_end <= start_offset:
                continue
            
            # 겹치는 시간 계산
            overlap_start = max(note_start, start_offset)
            overlap_end = min(note_end, end_offset)
            overlap_duration = overlap_end - overlap_start
            
            if overlap_duration <= 0:
                continue
            
            if hasattr(element, 'pitch'):
                bass_candidates.append({
                    'pitch': element.pitch,
                    'duration': overlap_duration,
                    'start': note_start
                })
            elif hasattr(element, 'pitches') and len(element.pitches) > 0:
                lowest = min(element.pitches, key=lambda p: p.midi)
                bass_candidates.append({
                    'pitch': lowest,
                    'duration': overlap_duration,
                    'start': note_start
                })
    
    if not bass_candidates:
        return None
    
    # 가장 흔한 pitch class 찾기
    pc_counter = Counter([b['pitch'].pitchClass for b in bass_candidates])
    most_common_pc = pc_counter.most_common(1)[0][0]
    
    # 해당 PC의 음들 중 가장 긴 duration
    candidates_of_pc = [b for b in bass_candidates if b['pitch'].pitchClass == most_common_pc]
    candidates_of_pc.sort(key=lambda x: x['duration'], reverse=True)
    
    return candidates_of_pc[0]['pitch']


def get_segment_pitches_weighted(score, start_offset, end_offset, role_weights):
    """
    시간 구간의 음들 수집 (스마트 가중치)
    
    가중치:
    - 역할별 (bass > inner > melody)
    - Duration (긴 음 > 짧은 음)
    - 강박 보너스 (정수 박자 시작 = 강박)
    """
    pitch_class_weights = defaultdict(float)
    
    for part in score.parts:
        role = classify_role(part)
        role_weight = role_weights.get(role, 1.0)
        
        instrument = part.getInstrument()
        if instrument and 'drum' in instrument.instrumentName.lower():
            continue
        
        for element in part.flatten().notesAndRests:
            note_start = element.offset
            note_end = note_start + element.quarterLength
            
            if note_start >= end_offset or note_end <= start_offset:
                continue
            
            # 겹치는 구간
            overlap_start = max(note_start, start_offset)
            overlap_end = min(note_end, end_offset)
            overlap_duration = overlap_end - overlap_start
            
            if overlap_duration <= 0:
                continue
            
            # Duration 가중치 (0.25박 = 0.5x, 0.5박 = 1x, 1박 = 2x, 2박+ = 3x)
            if element.quarterLength < 0.5:
                duration_weight = 0.3  # passing note
            elif element.quarterLength < 1.0:
                duration_weight = 1.0
            elif element.quarterLength < 2.0:
                duration_weight = 2.0
            else:
                duration_weight = 3.0  # 긴 음표 = 코드 구성음
            
            # 강박 보너스 (1박, 3박 시작 = 강박)
            beat_in_measure = note_start % 4.0
            if beat_in_measure in [0.0, 2.0]:  # 1박, 3박
                beat_weight = 1.5
            else:
                beat_weight = 1.0
            
            total_weight = role_weight * duration_weight * beat_weight * overlap_duration
            
            if hasattr(element, 'pitch'):
                pc = element.pitch.pitchClass
                pitch_class_weights[pc] += total_weight
            elif hasattr(element, 'pitches'):
                for p in element.pitches:
                    pc = p.pitchClass
                    pitch_class_weights[pc] += total_weight
    
    return dict(pitch_class_weights)


def match_chord(pitch_classes, bass_pitch):
    """코드 매칭"""
    if not pitch_classes:
        return None, 0.0
    
    root_pc = bass_pitch.pitchClass
    root_name = bass_pitch.name
    
    intervals = set()
    for pc in pitch_classes:
        interval = (pc - root_pc) % 12
        intervals.add(interval)
    
    best_match = None
    best_score = 0.0
    
    for chord_type, template in CHORD_TEMPLATES.items():
        matches = len(intervals & set(template))
        total = len(template)
        score = matches / total
        
        # 추가 음이 너무 많으면 페널티
        extra = len(intervals - set(template))
        if extra > 1:
            score -= 0.1 * extra
        
        if score > best_score and score >= 0.65:
            best_score = score
            best_match = chord_type
    
    if best_match:
        if best_match == 'major':
            return root_name, best_score
        elif best_match == 'minor':
            return f"{root_name}m", best_score
        elif best_match == 'dom7':
            return f"{root_name}7", best_score
        elif best_match == 'min7':
            return f"{root_name}m7", best_score
        elif best_match == 'diminished':
            return f"{root_name}dim", best_score
        elif best_match == 'augmented':
            return f"{root_name}aug", best_score
        else:
            return f"{root_name}{best_match}", best_score
    
    return None, 0.0


def extract_chord_progression_v6(filepath):
    """
    스마트 코드 진행 추출
    """
    print("=" * 70)
    print("🎼 코드 진행 추출 V6 (스마트 가중치)")
    print("=" * 70)
    
    print("\n[1단계] 파일 로딩 및 변환...")
    score = converter.parse(filepath)
    score = score.toSoundingPitch()
    print(f"✅ {len(score.parts)} 파트")
    
    # 베이스 파트
    bass_parts = [p for p in score.parts if classify_role(p) == 'bass']
    print(f"\n[2단계] 베이스 파트 {len(bass_parts)}개")
    
    # 마디 수
    first_part = score.parts[0]
    measures = first_part.getElementsByClass('Measure')
    num_measures = len(measures)
    print(f"\n[3단계] 총 {num_measures}마디 분석...")
    
    chord_progression = []
    
    # 각 마디를 반마디(2박자) 단위로 분할
    print("\n[4단계] 반마디 단위 코드 추출...")
    
    for measure_num in range(num_measures):
        measure_start = measure_num * 4.0
        
        # 전반부 (1-2박), 후반부 (3-4박)
        for half in [0, 2]:
            segment_start = measure_start + half
            segment_end = segment_start + 2.0
            
            # 베이스 음
            bass_pitch = get_segment_bass(score, bass_parts, segment_start, segment_end)
            
            if bass_pitch is None:
                continue
            
            # 음들 수집 (스마트 가중치)
            pitch_class_weights = get_segment_pitches_weighted(
                score, segment_start, segment_end,
                role_weights={'bass': 2.0, 'inner': 2.0, 'melody': 0.3}
            )
            
            # 코드 매칭
            chord_symbol, confidence = match_chord(
                pitch_class_weights.keys(),
                bass_pitch
            )
            
            if chord_symbol is None:
                continue
            
            beat = half + 1  # 1 or 3
            
            chord_progression.append({
                'measure': measure_num + 1,
                'beat': beat,
                'chord': chord_symbol,
                'bass': bass_pitch.nameWithOctave,
                'confidence': float(confidence),
                'pitch_classes': sorted(pitch_class_weights.keys())
            })
            
            print(f"  마디 {measure_num + 1:2d}, 박 {beat}: {chord_symbol:8s} (베이스: {bass_pitch.nameWithOctave}, 신뢰도: {confidence:.2f})")
    
    # 마디별 그룹화
    print("\n" + "=" * 70)
    print("📊 코드 진행 요약:")
    print("=" * 70)
    
    by_measure = defaultdict(list)
    for item in chord_progression:
        by_measure[item['measure']].append(item)
    
    for measure_num in sorted(by_measure.keys()):
        chords = by_measure[measure_num]
        if len(chords) == 1:
            print(f"마디 {measure_num:2d}: {chords[0]['chord']}")
        else:
            chord_str = ' - '.join([f"{c['chord']}(박{c['beat']})" for c in chords])
            print(f"마디 {measure_num:2d}: {chord_str}")
    
    # JSON 저장
    output_json = filepath.replace('.mxl', '_chords_v6.json')
    with open(output_json, 'w', encoding='utf-8') as f:
        json.dump(chord_progression, f, indent=2, ensure_ascii=False)
    
    print(f"\n✅ JSON 저장: {output_json}")
    
    return chord_progression


if __name__ == '__main__':
    filepath = '/Users/tsk/.openclaw/workspace/music-project/ode_to_joy_source.mxl'
    progression = extract_chord_progression_v6(filepath)
