#!/usr/bin/env python3
"""
코드 진행 추출 V11 - 엄격한 베이스 변화 감지
- V10 기반
- 베이스 변화 감지 기준 강화: duration 가중치 고려
- 명확한 변화만 감지
"""

from music21 import converter, pitch as music21_pitch
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
    if any(kw in name for kw in ['bass', 'cello', 'tuba', 'contrabass']):
        return 'bass'
    elif any(kw in name for kw in ['violin', 'flute', 'soprano', 'oboe', 'clarinet']):
        return 'melody'
    else:
        return 'inner'


def get_segment_bass_weighted(score, bass_parts, start_offset, end_offset):
    """
    베이스 음 추출 (duration × 강박 × 옥타브 가중치)
    """
    bass_scores = defaultdict(float)
    bass_pitches = {}
    
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
                duration_weight = 0.1
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
            
            # 옥타브 가중치
            def get_octave_weight(pitch):
                octave = pitch.octave
                if octave <= 1:
                    return 10.0
                elif octave == 2:
                    return 5.0
                elif octave == 3:
                    return 2.0
                else:
                    return 1.0
            
            if hasattr(element, 'pitch'):
                pc = element.pitch.pitchClass
                octave_weight = get_octave_weight(element.pitch)
                total_weight = duration_weight * beat_weight * octave_weight * overlap
                bass_scores[pc] += total_weight
                
                if pc not in bass_pitches or element.pitch.octave < bass_pitches[pc].octave:
                    bass_pitches[pc] = element.pitch
                    
            elif hasattr(element, 'pitches') and len(element.pitches) > 0:
                lowest = min(element.pitches, key=lambda p: p.midi)
                pc = lowest.pitchClass
                octave_weight = get_octave_weight(lowest)
                total_weight = duration_weight * beat_weight * octave_weight * overlap
                bass_scores[pc] += total_weight
                
                if pc not in bass_pitches or lowest.octave < bass_pitches[pc].octave:
                    bass_pitches[pc] = lowest
    
    if not bass_scores:
        return None, 0.0
    
    best_pc = max(bass_scores, key=bass_scores.get)
    best_score = bass_scores[best_pc]
    return bass_pitches[best_pc], best_score


def get_segment_pitches_weighted(score, start_offset, end_offset, role_weights):
    """음들 수집 (가중치 + raw 빈도)"""
    pitch_class_weights = defaultdict(float)
    pitch_class_raw_counts = Counter()
    
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
                pitch_class_raw_counts[pc] += 1
            elif hasattr(element, 'pitches'):
                for p in element.pitches:
                    pc = p.pitchClass
                    pitch_class_weights[pc] += total_weight
                    pitch_class_raw_counts[pc] += 1
    
    return dict(pitch_class_weights), pitch_class_raw_counts


def verify_bass_with_frequency(bass_pitch, pitch_class_raw_counts):
    """베이스 음 빈도 검증"""
    if not bass_pitch or not pitch_class_raw_counts:
        return bass_pitch
    
    bass_pc = bass_pitch.pitchClass
    bass_freq = pitch_class_raw_counts.get(bass_pc, 0)
    
    # 최다 빈도 음
    most_common_pc, most_common_freq = pitch_class_raw_counts.most_common(1)[0]
    
    # 베이스 음이 최다 빈도의 50% 미만이면 교체
    if bass_freq < most_common_freq * 0.5:
        new_pitch = music21_pitch.Pitch()
        new_pitch.pitchClass = most_common_pc
        return new_pitch
    
    return bass_pitch


def match_chord(pitch_classes, bass_pitch):
    """코드 매칭 - Major 우선순위 상향"""
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
        
        # Major 보너스
        if chord_type == 'major':
            score += 0.05
        
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


def detect_bass_changes(score, bass_parts, measure_start):
    """
    ★ V11: 엄격한 베이스 변화 감지
    
    각 박자의 베이스를 가중치 점수로 분석
    - 3개 이상의 박자가 서로 다른 명확한 베이스를 가져야 변화로 인정
    - 가중치 점수 차이가 2배 이상일 때만 "명확한 차이"로 인정
    """
    bass_data = []
    
    for beat in range(4):
        segment_start = measure_start + beat
        segment_end = segment_start + 1.0
        
        bass_pitch, bass_score = get_segment_bass_weighted(score, bass_parts, segment_start, segment_end)
        
        if bass_pitch:
            bass_data.append({
                'beat': beat,
                'pc': bass_pitch.pitchClass,
                'score': bass_score,
                'pitch': bass_pitch
            })
    
    if len(bass_data) < 4:
        return False
    
    # 각 박자의 베이스가 얼마나 명확한지 확인
    # 같은 마디 내 다른 박자들의 최고 점수와 비교
    all_scores_by_pc = defaultdict(list)
    for data in bass_data:
        all_scores_by_pc[data['pc']].append(data['score'])
    
    # 각 pc의 평균 점수
    avg_scores = {pc: sum(scores) / len(scores) for pc, scores in all_scores_by_pc.items()}
    
    # 최고 점수 PC와 2등 PC의 차이
    sorted_pcs = sorted(avg_scores.items(), key=lambda x: x[1], reverse=True)
    
    if len(sorted_pcs) < 2:
        return False
    
    top_score = sorted_pcs[0][1]
    second_score = sorted_pcs[1][1]
    
    # ★ 핵심: 1등과 2등의 점수 차이가 2배 이상일 때만 "명확한 단일 베이스"
    # 점수가 비슷하면 = 변화가 있다
    if top_score < second_score * 2.0:
        # 변화가 있음
        unique_basses = set([d['pc'] for d in bass_data])
        
        # 3개 이상의 서로 다른 베이스가 있어야 세분화
        return len(unique_basses) >= 3
    
    return False


def extract_chord_progression_v11(filepath, max_measures=None):
    """
    V11: 엄격한 베이스 변화 감지
    """
    print("=" * 70)
    print("🎼 코드 진행 추출 V11 (엄격한 베이스 변화 감지)")
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
    
    # 베이스 변화 감지
    print("\n[3.5단계] 엄격한 베이스 변화 감지...")
    measures_with_changes = []
    for measure_num in range(num_measures):
        measure_start = measure_num * 4.0
        if detect_bass_changes(score, bass_parts, measure_start):
            measures_with_changes.append(measure_num)
            print(f"  마디 {measure_num + 1}: 명확한 베이스 변화 감지 → 매 박자 분석")
    
    chord_progression = []
    
    print("\n[4단계] 코드 추출...")
    
    for measure_num in range(num_measures):
        measure_start = measure_num * 4.0
        
        # 자동 세분화
        if measure_num in measures_with_changes:
            segments = [0, 1, 2, 3]
            segment_length = 1.0
        else:
            segments = [0, 2]
            segment_length = 2.0
        
        for seg_start in segments:
            segment_start = measure_start + seg_start
            segment_end = segment_start + segment_length
            
            # 베이스 음
            bass_pitch, _ = get_segment_bass_weighted(score, bass_parts, segment_start, segment_end)
            
            # 음들 수집
            pitch_class_weights, pitch_class_raw_counts = get_segment_pitches_weighted(
                score, segment_start, segment_end,
                role_weights={'bass': 2.0, 'inner': 2.0, 'melody': 0.3}
            )
            
            # 베이스 빈도 검증
            verified_bass = verify_bass_with_frequency(bass_pitch, pitch_class_raw_counts)
            
            if verified_bass != bass_pitch and bass_pitch:
                print(f"  [검증] 마디 {measure_num + 1}, 박 {seg_start + 1}: 베이스 {bass_pitch.name} → {verified_bass.name} (빈도 기반)")
            
            if verified_bass is None:
                continue
            
            # 코드 매칭
            chord_symbol, confidence = match_chord(
                pitch_class_weights.keys(),
                verified_bass
            )
            
            if chord_symbol is None:
                continue
            
            beat = seg_start + 1
            
            chord_progression.append({
                'measure': measure_num + 1,
                'beat': beat,
                'chord': chord_symbol,
                'bass': verified_bass.nameWithOctave,
                'confidence': float(confidence),
            })
            
            print(f"  마디 {measure_num + 1:2d}, 박 {beat}: {chord_symbol:8s} (베이스: {verified_bass.nameWithOctave})")
    
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
                print(f"마디 {measure_num:2d}: {chords[0]['chord']}")
            else:
                print(f"마디 {measure_num:2d}: {chords[0]['chord']} - {chords[1]['chord']}")
        else:
            chord_str = ' - '.join([c['chord'] for c in chords])
            print(f"마디 {measure_num:2d}: {chord_str}")
    
    # JSON 저장
    output_json = filepath.replace('.mxl', '_chords_v11.json')
    with open(output_json, 'w', encoding='utf-8') as f:
        json.dump(chord_progression, f, indent=2, ensure_ascii=False)
    
    print(f"\n✅ JSON 저장: {output_json}")
    
    return chord_progression


if __name__ == '__main__':
    filepath = '/Users/tsk/.openclaw/workspace/music-project/ode_to_joy_source.mxl'
    progression = extract_chord_progression_v11(filepath, max_measures=24)
