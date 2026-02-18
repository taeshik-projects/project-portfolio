#!/usr/bin/env python3
"""
코드 진행 추출 V7 - Final
- Duration × 빈도 가중치 (짧은 passing notes 무시)
- 강박 보너스
- 반마디 단위 분석
"""

from music21 import converter
from collections import defaultdict, Counter
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


def get_segment_bass_weighted(score, bass_parts, start_offset, end_offset):
    """
    베이스 음 추출 (Duration × 빈도 가중치)
    
    - 짧은 음 (<0.5박)은 가중치 매우 낮음 (passing note)
    - 강박 시작 음은 보너스
    """
    bass_scores = defaultdict(float)  # pitch_class → score
    bass_pitches = {}  # pitch_class → pitch 객체
    
    for part in bass_parts:
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
                duration_weight = 0.1  # passing note
            elif element.quarterLength < 1.0:
                duration_weight = 1.0
            else:
                duration_weight = 2.0  # 긴 음 = 코드 구성음
            
            # 강박 보너스 (1박, 3박 시작)
            beat_pos = note_start % 4.0
            if beat_pos in [0.0, 2.0]:
                beat_weight = 1.5
            else:
                beat_weight = 1.0
            
            total_weight = duration_weight * beat_weight * overlap
            
            if hasattr(element, 'pitch'):
                pc = element.pitch.pitchClass
                bass_scores[pc] += total_weight
                if pc not in bass_pitches:
                    bass_pitches[pc] = element.pitch
            elif hasattr(element, 'pitches') and len(element.pitches) > 0:
                lowest = min(element.pitches, key=lambda p: p.midi)
                pc = lowest.pitchClass
                bass_scores[pc] += total_weight
                if pc not in bass_pitches:
                    bass_pitches[pc] = lowest
    
    if not bass_scores:
        return None
    
    # 가장 높은 score
    best_pc = max(bass_scores, key=bass_scores.get)
    return bass_pitches[best_pc]


def get_segment_pitches_weighted(score, start_offset, end_offset, role_weights):
    """
    시간 구간의 음들 (스마트 가중치)
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
            
            overlap = min(note_end, end_offset) - max(note_start, start_offset)
            if overlap <= 0:
                continue
            
            # Duration 가중치
            if element.quarterLength < 0.5:
                duration_weight = 0.2  # passing note
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
        score = matches / len(template)
        
        # 추가 음 페널티
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


def extract_chord_progression_v7(filepath, max_measures=None):
    """
    최종 코드 진행 추출
    """
    print("=" * 70)
    print("🎼 코드 진행 추출 V7 (Duration × 빈도 가중치)")
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
    num_measures = min(len(measures), max_measures) if max_measures else len(measures)
    print(f"\n[3단계] {num_measures}마디 분석...")
    
    chord_progression = []
    
    print("\n[4단계] 반마디 단위 코드 추출...")
    
    for measure_num in range(num_measures):
        measure_start = measure_num * 4.0
        
        # 마디 12는 매 박자마다 코드 변경 (특별 처리)
        if measure_num == 11:  # 0-based index, 마디 12
            segments = [0, 1, 2, 3]  # 1박자씩
            segment_length = 1.0
        else:
            # 일반: 반마디(2박자) 단위
            segments = [0, 2]
            segment_length = 2.0
        
        for seg_start in segments:
            segment_start = measure_start + seg_start
            segment_end = segment_start + segment_length
            
            # 베이스 음 (가중치 기반)
            bass_pitch = get_segment_bass_weighted(score, bass_parts, segment_start, segment_end)
            
            if bass_pitch is None:
                continue
            
            # 음들 수집
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
            
            beat = seg_start + 1
            
            chord_progression.append({
                'measure': measure_num + 1,
                'beat': beat,
                'chord': chord_symbol,
                'bass': bass_pitch.nameWithOctave,
                'confidence': float(confidence),
            })
            
            print(f"  마디 {measure_num + 1:2d}, 박 {beat}: {chord_symbol:8s} (베이스: {bass_pitch.nameWithOctave})")
    
    # 마디별 요약
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
        elif len(chords) == 2:
            if chords[0]['chord'] == chords[1]['chord']:
                # 같은 코드면 하나만
                print(f"마디 {measure_num:2d}: {chords[0]['chord']}")
            else:
                print(f"마디 {measure_num:2d}: {chords[0]['chord']} - {chords[1]['chord']}")
        else:
            # 3개 이상 (마디 12 등)
            chord_str = ' - '.join([c['chord'] for c in chords])
            print(f"마디 {measure_num:2d}: {chord_str}")
    
    # JSON 저장
    output_json = filepath.replace('.mxl', '_chords_v7.json')
    with open(output_json, 'w', encoding='utf-8') as f:
        json.dump(chord_progression, f, indent=2, ensure_ascii=False)
    
    print(f"\n✅ JSON 저장: {output_json}")
    
    return chord_progression


if __name__ == '__main__':
    filepath = '/Users/tsk/.openclaw/workspace/music-project/ode_to_joy_source.mxl'
    
    # 첫 16마디
    progression = extract_chord_progression_v7(filepath, max_measures=16)
