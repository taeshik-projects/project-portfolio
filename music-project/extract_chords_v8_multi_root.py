#!/usr/bin/env python3
"""
코드 진행 추출 V8 - 다중 근음 후보
- 베이스 음 + 최다 빈도 음들을 근음 후보로
- 각 후보로 코드 매칭 시도
- 가장 높은 점수 선택
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
    """베이스 음 추출 (가중치)"""
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
    
    best_pc = max(bass_scores, key=bass_scores.get)
    return bass_pitches[best_pc]


def get_segment_pitches_weighted(score, start_offset, end_offset, role_weights):
    """음들 수집 (가중치) + raw 빈도"""
    pitch_class_weights = defaultdict(float)
    pitch_class_raw_counts = Counter()  # 가중치 없는 순수 빈도
    
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
                pitch_class_raw_counts[pc] += 1  # raw 빈도
            elif hasattr(element, 'pitches'):
                for p in element.pitches:
                    pc = p.pitchClass
                    pitch_class_weights[pc] += total_weight
                    pitch_class_raw_counts[pc] += 1
    
    return dict(pitch_class_weights), pitch_class_raw_counts


def match_chord_with_root(pitch_classes, pitch_class_raw_counts, root_pc, root_name):
    """특정 근음으로 코드 매칭 (빈도 기반)"""
    if not pitch_classes:
        return None, 0.0
    
    intervals = set()
    for pc in pitch_classes:
        interval = (pc - root_pc) % 12
        intervals.add(interval)
    
    best_match = None
    best_score = 0.0
    
    for chord_type, template in CHORD_TEMPLATES.items():
        # 템플릿 일치도
        template_set = set(template)
        matches = len(intervals & template_set)
        match_ratio = matches / len(template)
        
        # 빈도 기반 설명력
        template_pcs = set((root_pc + t) % 12 for t in template)
        
        template_freq = sum(pitch_class_raw_counts.get(pc, 0) for pc in template_pcs if pc in pitch_classes)
        non_template_freq = sum(pitch_class_raw_counts.get(pc, 0) for pc in pitch_classes if pc not in template_pcs)
        total_freq = template_freq + non_template_freq
        
        if total_freq > 0:
            explanation_power = template_freq / total_freq
        else:
            explanation_power = 0.0
        
        # 최종 점수: 템플릿 일치도 × 설명력
        score = match_ratio * explanation_power
        
        if score > best_score:
            best_score = score
            best_match = chord_type
    
    if best_match and best_score >= 0.5:  # 설명력 곱하면 점수 낮아지므로 threshold 낮춤
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


def get_root_candidates(bass_pitch, pitch_class_raw_counts, pitch_class_weights):
    """
    근음 후보 생성
    1. 베이스 음
    2. 최다 빈도 1위
    3. 최다 빈도 2위
    """
    from music21 import pitch
    
    candidates = []
    
    # 1. 베이스 음
    if bass_pitch:
        candidates.append({
            'pc': bass_pitch.pitchClass,
            'name': bass_pitch.name,
            'source': 'bass'
        })
    
    # 2, 3. 최다 빈도 음들
    if pitch_class_raw_counts:
        most_common = pitch_class_raw_counts.most_common(3)
        for pc, count in most_common:
            if not any(c['pc'] == pc for c in candidates):
                p = pitch.Pitch()
                p.pitchClass = pc
                candidates.append({
                    'pc': pc,
                    'name': p.name,
                    'source': f'freq_{count}'
                })
    
    return candidates


def extract_chord_progression_v8(filepath, max_measures=None):
    """
    다중 근음 후보 코드 추출
    """
    print("=" * 70)
    print("🎼 코드 진행 추출 V8 (다중 근음 후보)")
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
    
    print("\n[4단계] 다중 근음 후보로 코드 추출...")
    
    for measure_num in range(num_measures):
        measure_start = measure_num * 4.0
        
        # 마디 12는 매 박자마다
        if measure_num == 11:
            segments = [0, 1, 2, 3]
            segment_length = 1.0
        else:
            segments = [0, 2]
            segment_length = 2.0
        
        for seg_start in segments:
            segment_start = measure_start + seg_start
            segment_end = segment_start + segment_length
            
            # 베이스 음
            bass_pitch = get_segment_bass_weighted(score, bass_parts, segment_start, segment_end)
            
            # 음들 수집
            pitch_class_weights, pitch_class_raw_counts = get_segment_pitches_weighted(
                score, segment_start, segment_end,
                role_weights={'bass': 2.0, 'inner': 2.0, 'melody': 0.3}
            )
            
            # 근음 후보들
            root_candidates = get_root_candidates(bass_pitch, pitch_class_raw_counts, pitch_class_weights)
            
            # 각 후보로 코드 매칭 시도
            best_chord = None
            best_confidence = 0.0
            best_root = None
            best_frequency = 0
            
            for candidate in root_candidates:
                chord_symbol, confidence = match_chord_with_root(
                    pitch_class_weights.keys(),
                    pitch_class_raw_counts,
                    candidate['pc'],
                    candidate['name']
                )
                
                if chord_symbol:
                    # 빈도 추출 (freq_XX 형식에서)
                    freq = 0
                    if candidate['source'].startswith('freq_'):
                        freq = int(candidate['source'].split('_')[1])
                    
                    # 더 좋은 점수 OR (같은 점수 + 더 높은 빈도)
                    if (confidence > best_confidence) or \
                       (confidence == best_confidence and freq > best_frequency):
                        best_chord = chord_symbol
                        best_confidence = confidence
                        best_root = candidate
                        best_frequency = freq
            
            if best_chord is None:
                continue
            
            beat = seg_start + 1
            
            chord_progression.append({
                'measure': measure_num + 1,
                'beat': beat,
                'chord': best_chord,
                'root_source': best_root['source'],
                'confidence': float(best_confidence),
            })
            
            print(f"  마디 {measure_num + 1:2d}, 박 {beat}: {best_chord:8s} (근음: {best_root['name']}, 출처: {best_root['source']})")
    
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
    output_json = filepath.replace('.mxl', '_chords_v8.json')
    with open(output_json, 'w', encoding='utf-8') as f:
        json.dump(chord_progression, f, indent=2, ensure_ascii=False)
    
    print(f"\n✅ JSON 저장: {output_json}")
    
    return chord_progression


if __name__ == '__main__':
    filepath = '/Users/tsk/.openclaw/workspace/music-project/ode_to_joy_source.mxl'
    progression = extract_chord_progression_v8(filepath, max_measures=16)
