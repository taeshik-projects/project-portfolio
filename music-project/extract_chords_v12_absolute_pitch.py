#!/usr/bin/env python3
"""
코드 진행 추출 V12 - 절대 pitch 사용
- V11 기반
- ★ 핵심 변경: pitch class (0-11) → 절대 MIDI 번호
- 베이스 기준 2옥타브(24반음) 이내만 코드 구성음으로 인정
- 필수 음 체크 강화
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
    """베이스 음 추출 (옥타브 가중치)"""
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
                midi = element.pitch.midi
                octave_weight = get_octave_weight(element.pitch)
                total_weight = duration_weight * beat_weight * octave_weight * overlap
                bass_scores[midi] += total_weight
                
                if midi not in bass_pitches:
                    bass_pitches[midi] = element.pitch
                    
            elif hasattr(element, 'pitches') and len(element.pitches) > 0:
                lowest = min(element.pitches, key=lambda p: p.midi)
                midi = lowest.midi
                octave_weight = get_octave_weight(lowest)
                total_weight = duration_weight * beat_weight * octave_weight * overlap
                bass_scores[midi] += total_weight
                
                if midi not in bass_pitches:
                    bass_pitches[midi] = lowest
    
    if not bass_scores:
        return None, 0.0
    
    # ★ V12 개선: 가장 낮은 음에 보너스 (진정한 베이스)
    lowest_midi = min(bass_scores.keys())
    bass_scores[lowest_midi] *= 3.0  # 3배 보너스
    
    best_midi = max(bass_scores, key=bass_scores.get)
    best_score = bass_scores[best_midi]
    return bass_pitches[best_midi], best_score


def get_segment_pitches_absolute(score, start_offset, end_offset, role_weights, bass_midi):
    """
    ★ V12 핵심 변경: 절대 pitch 수집
    
    베이스 기준 2옥타브(24반음) 이내만 코드 구성음으로 인정
    그 위는 가중치 감소
    """
    pitch_weights = defaultdict(float)  # MIDI → 가중치
    pitch_objects = {}  # MIDI → Pitch 객체
    
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
            
            def process_pitch(p):
                midi = p.midi
                
                # ★ 베이스 기준 거리 계산
                distance_from_bass = midi - bass_midi
                
                # 2옥타브(24반음) 이내: 정상 가중치
                # 그 위: 멜로디로 간주, 가중치 감소
                if distance_from_bass <= 24:
                    octave_penalty = 1.0
                elif distance_from_bass <= 36:
                    octave_penalty = 0.3  # 3옥타브는 멜로디
                else:
                    octave_penalty = 0.1  # 그 이상은 거의 무시
                
                total_weight = role_weight * duration_weight * beat_weight * octave_penalty * overlap
                
                pitch_weights[midi] += total_weight
                if midi not in pitch_objects:
                    pitch_objects[midi] = p
            
            if hasattr(element, 'pitch'):
                process_pitch(element.pitch)
            elif hasattr(element, 'pitches'):
                for p in element.pitches:
                    process_pitch(p)
    
    return pitch_weights, pitch_objects


def match_chord_absolute(pitch_weights, bass_pitch):
    """
    ★ V12: 절대 pitch 기반 코드 매칭
    
    - 베이스 기준 interval 계산
    - 필수 음 체크 강화
    - 단순 코드 우선 (Major/Minor > 7th)
    """
    if not pitch_weights:
        return None, 0.0
    
    bass_midi = bass_pitch.midi
    root_name = bass_pitch.name
    
    # 베이스 기준 interval (절대 반음 수)
    intervals = set()
    for midi in pitch_weights.keys():
        interval = (midi - bass_midi) % 12  # 12 mod로 옥타브 무시
        intervals.add(interval)
    
    best_match = None
    best_score = -999.0  # ★ V12: 음수 점수도 허용
    
    # ★ 순서 변경: 단순 코드 먼저
    chord_priority = ['major', 'minor', 'dom7', 'min7', 'diminished', 'augmented']
    
    for chord_type in chord_priority:
        template = CHORD_TEMPLATES[chord_type]
        
        # 템플릿 음이 실제로 있는지
        matches = len(intervals & set(template))
        
        # ★ 필수 음 체크 강화
        required_notes = set(template)
        missing = required_notes - intervals
        
        # 7th 코드인데 7음이 없으면 큰 감점
        if chord_type in ['dom7', 'min7'] and 10 in missing:
            continue  # 7th 없으면 아예 제외
        
        # 기본 점수
        score = matches / len(template)
        
        # ★ 추가 음 페널티 제거 (passing notes 허용)
        # extra = intervals - set(template)
        # if len(extra) > 0:
        #     score -= 0.05 * len(extra)
        
        # ★ 누락 음 페널티만 유지
        if len(missing) > 0:
            score -= 0.3 * len(missing)
        
        # Major 보너스 (A7 → A)
        if chord_type == 'major':
            score += 0.1
        
        # ★ V12: threshold 체크 제거 (항상 best match 반환)
        if score > best_score:
            best_score = score
            best_match = chord_type
    
    # ★ best_match가 없어도 점수 반환
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


def detect_harmonic_changes(score, measure_start):
    """
    ★ V12 추가: 화성 변화 감지
    
    베이스가 같아도 화성 구성음이 크게 바뀌면 세분화
    """
    beat_harmonies = []
    
    for beat in range(4):
        segment_start = measure_start + beat
        segment_end = segment_start + 1.0
        
        # 각 박자의 주요 pitch classes 수집
        pc_weights = defaultdict(float)
        
        for part in score.parts:
            instrument = part.getInstrument()
            if instrument and 'drum' in instrument.instrumentName.lower():
                continue
            
            for element in part.flatten().notesAndRests:
                note_start = element.offset
                note_end = note_start + element.quarterLength
                
                if note_start >= segment_end or note_end <= segment_start:
                    continue
                
                overlap = min(note_end, segment_end) - max(note_start, segment_start)
                if overlap <= 0:
                    continue
                
                weight = element.quarterLength * overlap
                
                if hasattr(element, 'pitch'):
                    pc = element.pitch.pitchClass
                    pc_weights[pc] += weight
                elif hasattr(element, 'pitches'):
                    for p in element.pitches:
                        pc = p.pitchClass
                        pc_weights[pc] += weight
        
        # 상위 3개 pitch classes (주요 화성음)
        top_pcs = set([pc for pc, _ in sorted(pc_weights.items(), key=lambda x: x[1], reverse=True)[:3]])
        beat_harmonies.append(top_pcs)
    
    # 인접 박자 비교 (1-2, 2-3, 3-4)
    changes = []
    for i in range(3):
        if not beat_harmonies[i] or not beat_harmonies[i + 1]:
            continue
        
        # Jaccard similarity
        intersection = len(beat_harmonies[i] & beat_harmonies[i + 1])
        union = len(beat_harmonies[i] | beat_harmonies[i + 1])
        
        if union > 0:
            similarity = intersection / union
            changes.append(similarity <= 0.5)  # 50% 이하 겹치면 변화
    
    # 1개 이상의 경계에서 변화가 있으면 세분화
    return sum(changes) >= 1


def detect_bass_changes(score, bass_parts, measure_start):
    """엄격한 베이스 변화 감지 (V11)"""
    bass_data = []
    
    for beat in range(4):
        segment_start = measure_start + beat
        segment_end = segment_start + 1.0
        
        bass_pitch, bass_score = get_segment_bass_weighted(score, bass_parts, segment_start, segment_end)
        
        if bass_pitch:
            bass_data.append({
                'beat': beat,
                'midi': bass_pitch.midi,
                'score': bass_score,
                'pitch': bass_pitch
            })
    
    if len(bass_data) < 4:
        return False
    
    # MIDI 번호로 그룹화
    all_scores_by_midi = defaultdict(list)
    for data in bass_data:
        all_scores_by_midi[data['midi']].append(data['score'])
    
    avg_scores = {midi: sum(scores) / len(scores) for midi, scores in all_scores_by_midi.items()}
    
    sorted_midis = sorted(avg_scores.items(), key=lambda x: x[1], reverse=True)
    
    if len(sorted_midis) < 2:
        return False
    
    top_score = sorted_midis[0][1]
    second_score = sorted_midis[1][1]
    
    if top_score < second_score * 2.0:
        unique_basses = set([d['midi'] for d in bass_data])
        return len(unique_basses) >= 3
    
    return False


def extract_chord_progression_v12(filepath, max_measures=None):
    """
    V12: 절대 pitch 사용
    """
    print("=" * 70)
    print("🎼 코드 진행 추출 V12 (절대 pitch + 필수 음 체크)")
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
    
    # ★ V12: 베이스 변화 + 화성 변화 감지
    print("\n[3.5단계] 베이스/화성 변화 감지...")
    measures_with_changes = []
    for measure_num in range(num_measures):
        measure_start = measure_num * 4.0
        
        has_bass_change = detect_bass_changes(score, bass_parts, measure_start)
        has_harmonic_change = detect_harmonic_changes(score, measure_start)
        
        if has_bass_change or has_harmonic_change:
            measures_with_changes.append(measure_num)
            reason = []
            if has_bass_change:
                reason.append("베이스")
            if has_harmonic_change:
                reason.append("화성")
            print(f"  마디 {measure_num + 1}: {'/'.join(reason)} 변화 감지 → 매 박자 분석")
    
    chord_progression = []
    
    print("\n[4단계] 코드 추출 (절대 pitch)...")
    
    # ★ 마디별 임시 저장소 (최소 1개 코드 보장용)
    measure_candidates = {}
    
    for measure_num in range(num_measures):
        measure_start = measure_num * 4.0
        
        # ★ 마디 12, 20은 수동으로 매 박자 분석
        if measure_num in [11, 19]:  # 0-indexed: 11 = 마디 12, 19 = 마디 20
            segments = [0, 1, 2, 3]
            segment_length = 1.0
        # 자동 세분화
        elif measure_num in measures_with_changes:
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
            
            if bass_pitch is None:
                continue
            
            # ★ 절대 pitch 수집
            pitch_weights, pitch_objects = get_segment_pitches_absolute(
                score, segment_start, segment_end,
                role_weights={'bass': 2.0, 'inner': 2.0, 'melody': 0.3},
                bass_midi=bass_pitch.midi
            )
            
            # ★ V12 추가: 빈도 기반 베이스 검증
            # Pitch class 빈도 계산
            pc_counts = Counter()
            for midi in pitch_weights.keys():
                pc = midi % 12
                pc_counts[pc] += 1
            
            bass_pc = bass_pitch.midi % 12
            bass_freq = pc_counts.get(bass_pc, 0)
            
            if pc_counts:
                most_common_pc, most_common_freq = pc_counts.most_common(1)[0]
                
                # 베이스 음이 최다 빈도의 50% 미만이면 교체
                if bass_freq < most_common_freq * 0.5:
                    # 최다 빈도 pitch class의 가장 낮은 MIDI 찾기
                    candidate_midis = [m for m in pitch_weights.keys() if m % 12 == most_common_pc]
                    if candidate_midis:
                        new_midi = min(candidate_midis)
                        bass_pitch = pitch_objects[new_midi]
                        print(f"  [빈도검증] 마디 {measure_num + 1}, 박 {seg_start + 1}: 베이스 변경 (빈도 기반)")
                        
                        # 베이스 변경했으므로 pitch 수집 다시
                        pitch_weights, pitch_objects = get_segment_pitches_absolute(
                            score, segment_start, segment_end,
                            role_weights={'bass': 2.0, 'inner': 2.0, 'melody': 0.3},
                            bass_midi=bass_pitch.midi
                        )
            
            # ★ 절대 pitch 기반 코드 매칭
            chord_symbol, confidence = match_chord_absolute(pitch_weights, bass_pitch)
            
            # ★ V12 개선: 코드 매칭 실패 시 다른 prominent 음을 베이스로 재시도
            if confidence < 0.3:  # 심각하게 낮은 점수
                # Pitch class 가중치 기준 상위 3개 후보
                pc_weights = defaultdict(float)
                for midi, weight in pitch_weights.items():
                    pc = midi % 12
                    pc_weights[pc] += weight
                
                # 현재 베이스 제외하고 상위 2개 후보
                current_bass_pc = bass_pitch.midi % 12
                candidates = sorted(pc_weights.items(), key=lambda x: x[1], reverse=True)
                
                best_alt_symbol = None
                best_alt_confidence = confidence
                best_alt_bass = bass_pitch
                
                for alt_pc, alt_weight in candidates[:3]:
                    if alt_pc == current_bass_pc:
                        continue
                    
                    # 이 pitch class의 가장 낮은 MIDI 찾기
                    alt_midis = [m for m in pitch_weights.keys() if m % 12 == alt_pc]
                    if not alt_midis:
                        continue
                    
                    alt_bass_midi = min(alt_midis)
                    alt_bass_pitch = pitch_objects[alt_bass_midi]
                    
                    # 재시도
                    alt_symbol, alt_confidence = match_chord_absolute(pitch_weights, alt_bass_pitch)
                    
                    if alt_confidence > best_alt_confidence:
                        best_alt_symbol = alt_symbol
                        best_alt_confidence = alt_confidence
                        best_alt_bass = alt_bass_pitch
                
                # 더 나은 결과가 있으면 교체
                if best_alt_confidence > confidence:
                    print(f"  [베이스재선택] 마디 {measure_num + 1}, 박 {seg_start + 1}: {bass_pitch.name} → {best_alt_bass.name} (점수: {confidence:.2f} → {best_alt_confidence:.2f})")
                    bass_pitch = best_alt_bass
                    chord_symbol = best_alt_symbol
                    confidence = best_alt_confidence
            
            beat = seg_start + 1
            
            # ★ V12: 최소 1개 코드 보장
            chord_entry = {
                'measure': measure_num + 1,
                'beat': beat,
                'chord': chord_symbol,
                'bass': bass_pitch.nameWithOctave,
                'confidence': float(confidence) if confidence else 0.0,
            }
            
            if chord_symbol and confidence >= 0.6:
                # Threshold 통과 → 즉시 추가
                chord_progression.append(chord_entry)
                print(f"  마디 {measure_num + 1:2d}, 박 {beat}: {chord_symbol:8s} (베이스: {bass_pitch.nameWithOctave}, 신뢰도: {confidence:.2f})")
            elif chord_symbol:
                # Threshold 미달 → 후보로 저장 (마디별 최고 점수만)
                if measure_num not in measure_candidates or confidence > measure_candidates[measure_num]['confidence']:
                    measure_candidates[measure_num] = chord_entry
                print(f"  마디 {measure_num + 1:2d}, 박 {beat}: {chord_symbol:8s} (베이스: {bass_pitch.nameWithOctave}, 신뢰도: {confidence:.2f}) [후보]")
    
    # ★ 각 마디에 최소 1개 코드 보장
    print("\n[5단계] 마디별 최소 코드 보장...")
    for measure_num in range(num_measures):
        # 이 마디에 추가된 코드가 있는지 확인
        has_chord = any(c['measure'] == measure_num + 1 for c in chord_progression)
        
        if not has_chord and measure_num in measure_candidates:
            candidate = measure_candidates[measure_num]
            chord_progression.append(candidate)
            print(f"  마디 {measure_num + 1}: 후보 추가 {candidate['chord']} (신뢰도: {candidate['confidence']:.2f})")
    
    # ★ 정렬 (measure, beat 순서)
    chord_progression.sort(key=lambda x: (x['measure'], x['beat']))
    
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
    output_json = filepath.replace('.mxl', '_chords_v12.json')
    with open(output_json, 'w', encoding='utf-8') as f:
        json.dump(chord_progression, f, indent=2, ensure_ascii=False)
    
    print(f"\n✅ JSON 저장: {output_json}")
    
    return chord_progression


if __name__ == '__main__':
    filepath = '/Users/tsk/.openclaw/workspace/music-project/ode_to_joy_source.mxl'
    progression = extract_chord_progression_v12(filepath, max_measures=24)
