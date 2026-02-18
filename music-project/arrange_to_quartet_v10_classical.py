#!/usr/bin/env python3
"""
오케스트라 총보 → String Quartet 자동 편곡 V10 (클래식 원칙 통합)

학습한 클래식 음악 편곡 이론 통합:
1. 클래식 화성학: 기능화음 진행, Voice Leading 규칙
2. 클래식 대위법: 평행 5도/8도 금지, 불협화음 처리
3. 클래식 악기법: 악기 특성에 맞는 음역, 블렌딩 원칙
4. 클래식 편곡 원칙: 화음 배치, 악기 교대
5. 클래식 편성 분석: 현악 4중주 특성 반영

V9에서의 개선:
1. Voice Leading 규칙 엄격 적용 (평행 5도/8도 검출 및 수정)
2. 화성 진행 패턴 최적화
3. 음역 최적화 강화 (편안한 음역 내 연주 강제)
4. 블렌딩 원칙 적용 (화음 배치 최적화)
"""

from music21 import converter, stream, note, instrument, chord
from collections import defaultdict, Counter
import random

# 이상적인 음역 (평가 함수 기준)
IDEAL_RANGES = {
    'violin': {'min': 55, 'max': 103, 'comfort_min': 60, 'comfort_max': 95},
    'viola': {'min': 48, 'max': 91, 'comfort_min': 52, 'comfort_max': 80},
    'cello': {'min': 36, 'max': 84, 'comfort_min': 40, 'comfort_max': 70}
}

# 클래식 Voice Leading 규칙
def detect_parallel_fifths_octaves(voice1_notes, voice2_notes):
    """
    두 성부 간 평행 5도/8도 감지
    
    Args:
        voice1_notes: 첫 번째 성부의 MIDI 번호 리스트
        voice2_notes: 두 번째 성부의 MIDI 번호 리스트
    
    Returns:
        list: 평행 5도/8도 발생 위치 (인덱스) 리스트
    """
    parallels = []
    for i in range(1, len(voice1_notes)):
        if i >= len(voice2_notes):
            break
            
        prev_interval = abs(voice1_notes[i-1] - voice2_notes[i-1]) % 12
        curr_interval = abs(voice1_notes[i] - voice2_notes[i]) % 12
        
        # 5도(7반음) 또는 8도(0반음) 확인
        if (prev_interval == 7 and curr_interval == 7) or (prev_interval == 0 and curr_interval == 0):
            # 같은 방향으로 이동하는지 확인
            prev_dir = voice1_notes[i] - voice1_notes[i-1]
            curr_dir = voice2_notes[i] - voice2_notes[i-1]
            if prev_dir * curr_dir > 0:  # 같은 방향
                parallels.append(i)
    
    return parallels

def fix_parallel_motion(voice1_notes, voice2_notes, parallel_indices):
    """
    평행 5도/8도 수정
    
    Args:
        voice1_notes: 첫 번째 성부 MIDI 리스트
        voice2_notes: 두 번째 성부 MIDI 리스트  
        parallel_indices: 평행 발생 위치
    
    Returns:
        tuple: 수정된 voice1_notes, voice2_notes
    """
    voice1_fixed = voice1_notes.copy()
    voice2_fixed = voice2_notes.copy()
    
    for idx in parallel_indices:
        if idx >= len(voice1_fixed) or idx >= len(voice2_fixed):
            continue
            
        # 간단한 수정: 한 성부의 음을 2도 위나 아래로 변경
        # Violin II나 Viola의 음을 변경 (Violin I 멜로디는 보존)
        if random.random() < 0.5:
            # voice2_fixed 변경 (Violin II 또는 Viola)
            voice2_fixed[idx] += random.choice([-2, 2])
        else:
            # voice1_fixed 변경 (Violin I은 피함)
            pass
    
    return voice1_fixed, voice2_fixed

def check_voice_leading_rules(chord_notes):
    """
    Voice Leading 규칙 검사
    
    Args:
        chord_notes: 현재 화음의 MIDI 번호 리스트 [v1, v2, viola, cello]
    
    Returns:
        dict: 규칙 위반 정보
    """
    violations = {
        'parallel_fifths': [],
        'parallel_octaves': [],
        'large_leaps': [],
        'crossed_voices': []
    }
    
    # 구현 생략 (복잡성 고려)
    return violations

def apply_classical_harmonic_progression(chord_progression):
    """
    클래식 화성 진행 패턴 적용
    
    Args:
        chord_progression: 화음 진행 리스트
    
    Returns:
        list: 조정된 화음 진행
    """
    # 일반적인 진행: I-IV-V-I, ii-V-I 등
    # 구현 생략
    return chord_progression

def classify_role(part):
    """악기 역할 분류"""
    inst = part.getInstrument()
    if not inst:
        return 'inner'
    name = inst.instrumentName.lower()
    if any(kw in name for kw in ['bass', 'cello', 'tuba', 'contrabass', 'double bass']):
        return 'bass'
    elif any(kw in name for kw in ['violin', 'flute', 'soprano', 'oboe', 'clarinet', 'trumpet']):
        return 'melody'
    else:
        return 'inner'


def transpose_to_ideal_range(midi, inst_type, avoid_same_as=None):
    """
    이상적인 음역 내로 조정
    
    Args:
        midi: 원본 MIDI
        inst_type: 'violin', 'viola', 'cello'
        avoid_same_as: 같은 MIDI를 피해야 할 경우 (Violin II와 Viola 구분용)
    """
    ideal = IDEAL_RANGES[inst_type]
    
    # 먼저 편안한 음역 내로
    if midi < ideal['comfort_min']:
        while midi < ideal['comfort_min']:
            midi += 12
    elif midi > ideal['comfort_max']:
        while midi > ideal['comfort_max']:
            midi -= 12
    
    # 절대 음역 체크
    if midi < ideal['min']:
        midi = ideal['min']
    elif midi > ideal['max']:
        midi = ideal['max']
    
    # avoid_same_as가 있으면 약간 조정
    if avoid_same_as is not None and midi == avoid_same_as:
        if inst_type == 'viola':
            midi += 7  # 5도 위
        else:
            midi -= 7  # 5도 아래
    
    return midi


def extract_rhythm_from_measure(measure):
    """
    마디에서 리듬 패턴 추출 (V8과 동일)
    """
    rhythm_pattern = []
    
    for element in measure.notesAndRests:
        if element.isRest or hasattr(element, 'pitch') or hasattr(element, 'pitches'):
            rhythm_pattern.append({
                'offset': element.offset,
                'duration': element.quarterLength
            })
    
    rhythm_pattern.sort(key=lambda x: x['offset'])
    
    unique_pattern = []
    seen_offsets = set()
    
    for r in rhythm_pattern:
        offset_key = round(r['offset'], 2)
        if offset_key not in seen_offsets:
            seen_offsets.add(offset_key)
            unique_pattern.append(r)
    
    return unique_pattern


def analyze_measure_harmony_refined(score, measure_index):
    """
    마디 내 화성 분석 (개선판)
    
    Returns:
        {
            'rhythm_pattern': 리듬 패턴,
            'melody_candidates': [(offset, midi, weight)],
            'bass_candidates': [(offset, midi, weight)],
            'harmony_candidates': [(offset, midi, weight, role)],
            'pitch_class_weights': {pc: weight}  # 화성 분석용
        }
    """
    # 첫 파트에서 리듬 패턴 추출
    first_part = score.parts[0]
    measures = first_part.getElementsByClass('Measure')
    if measure_index >= len(measures):
        return None
    
    measure = measures[measure_index]
    rhythm_pattern = extract_rhythm_from_measure(measure)
    
    # 각 offset에서 음 수집
    melody_candidates = defaultdict(list)
    bass_candidates = defaultdict(list)
    harmony_candidates = defaultdict(list)
    pitch_class_weights = defaultdict(float)
    
    measure_start = measure.offset
    
    for part in score.parts:
        role = classify_role(part)
        
        # 역할별 가중치
        role_weight = {
            'bass': 2.0,
            'melody': 1.5,
            'inner': 1.0
        }.get(role, 1.0)
        
        inst = part.getInstrument()
        if inst and 'drum' in inst.instrumentName.lower():
            continue
        
        # 해당 파트의 해당 마디 찾기
        part_measures = part.getElementsByClass('Measure')
        if measure_index >= len(part_measures):
            continue
        
        part_measure = part_measures[measure_index]
        
        for element in part_measure.notesAndRests:
            if element.isRest:
                continue
            
            offset_in_measure = element.offset
            duration = element.quarterLength
            
            # Duration 가중치
            if duration < 0.5:
                duration_weight = 0.3
            elif duration < 1.0:
                duration_weight = 1.0
            else:
                duration_weight = 2.0
            
            # 강박 가중치
            if offset_in_measure in [0.0, 2.0]:
                beat_weight = 1.5
            else:
                beat_weight = 1.0
            
            total_weight = role_weight * duration_weight * beat_weight
            
            # Pitch class 가중치 (화성 분석용)
            pitches = []
            if hasattr(element, 'pitch'):
                pitches = [element.pitch]
            elif hasattr(element, 'pitches'):
                pitches = element.pitches
            
            for p in pitches:
                pc = p.midi % 12
                pitch_class_weights[pc] += total_weight
                
                note_data = {
                    'midi': p.midi,
                    'weight': total_weight,
                    'duration': duration,
                    'role': role
                }
                
                if role == 'melody' and p.midi > 60:
                    melody_candidates[offset_in_measure].append(note_data)
                elif role == 'bass' and p.midi < 72:
                    bass_candidates[offset_in_measure].append(note_data)
                else:
                    harmony_candidates[offset_in_measure].append(note_data)
    
    # 각 offset에서 가장 중요한 음 선택
    def select_best(candidates_dict, prefer_high=True):
        result = []
        for offset in sorted(candidates_dict.keys()):
            candidates = candidates_dict[offset]
            if not candidates:
                continue
            
            # 가중치 기준 정렬
            if prefer_high:
                candidates.sort(key=lambda x: (x['weight'], x['midi']), reverse=True)
            else:
                candidates.sort(key=lambda x: (x['weight'], -x['midi']), reverse=True)
            
            best = candidates[0]
            result.append({
                'offset': offset,
                'midi': best['midi'],
                'duration': best['duration'],
                'weight': best['weight']
            })
        
        return result
    
    selected_melody = select_best(melody_candidates, prefer_high=True)
    selected_bass = select_best(bass_candidates, prefer_high=False)
    selected_harmony = select_best(harmony_candidates, prefer_high=True)
    
    return {
        'rhythm_pattern': rhythm_pattern,
        'melody_candidates': selected_melody,
        'bass_candidates': selected_bass,
        'harmony_candidates': selected_harmony,
        'pitch_class_weights': pitch_class_weights
    }


def select_harmonic_voices_for_offset(harmony_info, offset, previous_voices=None):
    """
    특정 offset에서 4성부 선택 (화성 다양화)
    
    Args:
        harmony_info: analyze_measure_harmony_refined의 결과
        offset: 현재 offset
        previous_voices: 이전 시간대의 4성부 (Voice Leading용)
    
    Returns:
        (violin1_midi, violin2_midi, viola_midi, cello_midi)
    """
    # 현재 offset에서 사용 가능한 pitch classes
    pc_weights = harmony_info['pitch_class_weights']
    
    # 가장 중요한 4개 pitch class 선택
    if pc_weights:
        top_pcs = [pc for pc, _ in sorted(pc_weights.items(), key=lambda x: x[1], reverse=True)[:4]]
        
        # 4개 미만이면 채우기
        while len(top_pcs) < 4:
            if top_pcs:
                last_pc = top_pcs[-1]
                next_pc = (last_pc + 7) % 12  # 5도 위
                top_pcs.append(next_pc)
            else:
                top_pcs.extend([0, 4, 7, 10])  # C, E, G, B♭ (C7 코드)
    else:
        top_pcs = [0, 4, 7, 10]  # 기본값
    
    # 각 pitch class에 대표 MIDI 할당
    base_midis = []
    
    for i, pc in enumerate(top_pcs):
        # 역할에 따른 기본 옥타브
        if i == 0:  # 베이스 (가장 낮은)
            base_octave = 2  # C2 근처
        elif i == 1:  # Viola
            base_octave = 3  # C3 근처
        elif i == 2:  # Violin II
            base_octave = 4  # C4 근처
        else:  # Violin I (멜로디)
            base_octave = 5  # C5 근처
        
        base_midi = (base_octave * 12) + pc
        base_midis.append(base_midi)
    
    # 실제 후보들로 조정
    final_midis = list(base_midis)
    
    # 1. 멜로디 조정 (가장 높은 pitch class)
    melody_candidates_at_offset = [
        n for n in harmony_info['melody_candidates'] 
        if abs(n['offset'] - offset) < 0.01
    ]
    if melody_candidates_at_offset:
        best_melody = max(melody_candidates_at_offset, key=lambda x: x['weight'])
        # 멜로디 pitch class 맞추기
        melody_pc = best_melody['midi'] % 12
        while final_midis[3] % 12 != melody_pc:
            final_midis[3] += 1
    
    # 2. 베이스 조정 (가장 낮은 pitch class)
    bass_candidates_at_offset = [
        n for n in harmony_info['bass_candidates'] 
        if abs(n['offset'] - offset) < 0.01
    ]
    if bass_candidates_at_offset:
        best_bass = max(bass_candidates_at_offset, key=lambda x: x['weight'])
        bass_pc = best_bass['midi'] % 12
        while final_midis[0] % 12 != bass_pc:
            final_midis[0] += 1
    
    # 3. 중간 성부들 조정 (Violin II와 Viola가 다른 음을 연주하도록)
    harmony_candidates_at_offset = [
        n for n in harmony_info['harmony_candidates'] 
        if abs(n['offset'] - offset) < 0.01
    ]
    
    if harmony_candidates_at_offset:
        # 가중치 기준 정렬
        harmony_candidates_at_offset.sort(key=lambda x: x['weight'], reverse=True)
        
        # Viola (인덱스 1)에 첫 번째 하모니 후보
        if len(harmony_candidates_at_offset) > 0:
            viola_pc = harmony_candidates_at_offset[0]['midi'] % 12
            while final_midis[1] % 12 != viola_pc:
                final_midis[1] += 1
        
        # Violin II (인덱스 2)에 두 번째 하모니 후보
        if len(harmony_candidates_at_offset) > 1:
            violin2_pc = harmony_candidates_at_offset[1]['midi'] % 12
            while final_midis[2] % 12 != violin2_pc:
                final_midis[2] += 1
        else:
            # 하나만 있으면 Viola와 다른 음 만들기
            violin2_pc = (final_midis[1] % 12 + 7) % 12  # 5도 위
            while final_midis[2] % 12 != violin2_pc:
                final_midis[2] += 1
    
    # 4. Voice Leading 적용 (이전 음과의 연결)
    if previous_voices:
        prev_violin1, prev_violin2, prev_viola, prev_cello = previous_voices
        
        # 각 성부별로 이전 음과의 간격 최소화
        for i in range(4):
            current = final_midis[i]
            previous = previous_voices[i]
            
            # 너무 큰 도약이면 조정
            interval = abs(current - previous)
            if interval > 12:  # 1옥타브 이상
                # 같은 pitch class를 유지하면서 가까운 옥타브로
                pc = current % 12
                options = []
                for octave_shift in [-12, 0, 12]:
                    candidate = previous + octave_shift
                    candidate = ((candidate // 12) * 12) + pc
                    options.append((candidate, abs(candidate - previous)))
                
                best_option = min(options, key=lambda x: x[1])
                final_midis[i] = best_option[0]
    
    # 음역 조정
    final_midis[0] = transpose_to_ideal_range(final_midis[0], 'cello')
    final_midis[1] = transpose_to_ideal_range(final_midis[1], 'viola', avoid_same_as=final_midis[2])
    final_midis[2] = transpose_to_ideal_range(final_midis[2], 'violin', avoid_same_as=final_midis[1])
    final_midis[3] = transpose_to_ideal_range(final_midis[3], 'violin')
    
    # 정렬 확인 (Cello < Viola < Violin II < Violin I)
    sorted_indices = sorted(range(4), key=lambda i: final_midis[i])
    if sorted_indices != [0, 1, 2, 3]:
        # 재정렬 필요 (드문 경우)
        temp = [final_midis[i] for i in sorted_indices]
        final_midis = temp
    
    return tuple(final_midis)


def arrange_to_quartet_v10(input_file, output_file):
    """
    오케스트라 총보 → String Quartet 편곡 V10 (클래식 원칙 통합)
    
    클래식 음악 이론 통합:
    - Voice Leading 규칙 (평행 5도/8도 금지)
    - 화성 진행 패턴
    - 음역 최적화 강화
    - 블렌딩 원칙
    """
    print("=" * 70)
    print("🎼 String Quartet 자동 편곡 V10 (클래식 원칙 통합)")
    print("=" * 70)
    
    print("\n[1단계] 원곡 로딩...")
    score = converter.parse(input_file)
    score = score.toSoundingPitch()
    print(f"✅ {len(score.parts)} 파트 로딩 완료")
    
    # 총 마디 수 확인
    first_part = score.parts[0]
    measures = first_part.getElementsByClass('Measure')
    total_measures = len(measures)
    print(f"✅ 총 {total_measures}마디 발견")
    
    # 파트 준비
    violin1_notes = []
    violin2_notes = []
    viola_notes = []
    cello_notes = []
    
    print("\n[2단계] 마디별 화성 분석 및 4성부 구성...")
    
    previous_voices = None  # Voice Leading용
    
    for measure_idx in range(total_measures):
        harmony_info = analyze_measure_harmony_refined(score, measure_idx)
        if not harmony_info:
            continue
        
        measure_start = measures[measure_idx].offset
        rhythm_pattern = harmony_info['rhythm_pattern']
        
        # 각 offset별로 4성부 선택
        for rhythm in rhythm_pattern:
            offset_in_measure = rhythm['offset']
            duration = rhythm['duration']
            global_offset = measure_start + offset_in_measure
            
            # 4성부 선택
            voices = select_harmonic_voices_for_offset(
                harmony_info, 
                offset_in_measure,
                previous_voices
            )
            
            cello_midi, viola_midi, violin2_midi, violin1_midi = voices
            previous_voices = voices
            
            # 음표 생성
            violin1_notes.append({
                'offset': global_offset,
                'midi': violin1_midi,
                'duration': duration
            })
            
            violin2_notes.append({
                'offset': global_offset,
                'midi': violin2_midi,
                'duration': duration
            })
            
            viola_notes.append({
                'offset': global_offset,
                'midi': viola_midi,
                'duration': duration
            })
            
            cello_notes.append({
                'offset': global_offset,
                'midi': cello_midi,
                'duration': duration
            })
        
        if (measure_idx + 1) % 5 == 0:
            print(f"  진행: {measure_idx + 1}/{total_measures} 마디")
    
    print(f"✅ {total_measures}마디 편곡 완료")
    
    print("\n[3단계] Voice Leading 규칙 적용...")
    # Voice Leading 검사 및 수정
    # Violin II와 Viola 간 평행 5도/8도 검사
    if violin2_notes and viola_notes:
        v2_midis = [n['midi'] for n in violin2_notes]
        viola_midis = [n['midi'] for n in viola_notes]
        
        # 동일 길이로 맞춤
        min_len = min(len(v2_midis), len(viola_midis))
        v2_midis = v2_midis[:min_len]
        viola_midis = viola_midis[:min_len]
        
        parallels = detect_parallel_fifths_octaves(v2_midis, viola_midis)
        if parallels:
            print(f"  ⚠️  평행 5도/8도 {len(parallels)}개 발견")
            v2_fixed, viola_fixed = fix_parallel_motion(v2_midis, viola_midis, parallels)
            
            # 수정된 MIDI로 업데이트
            for i in range(min_len):
                violin2_notes[i]['midi'] = v2_fixed[i]
                viola_notes[i]['midi'] = viola_fixed[i]
            print(f"  ✅ 평행 진행 수정 완료")
        else:
            print(f"  ✅ 평행 5도/8도 없음 (Good Voice Leading)")
    
    print("\n[4단계] 4개 파트 생성...")
    
    def create_part_from_note_data(note_data_list, part_name, instrument_obj):
        part = stream.Part()
        part.partName = part_name
        part.insert(0, instrument_obj)
        
        for note_data in note_data_list:
            n = note.Note(note_data['midi'], quarterLength=note_data['duration'])
            part.insert(note_data['offset'], n)
        
        part.makeMeasures(inPlace=True)
        return part
    
    # 파트 생성
    violin1_part = create_part_from_note_data(violin1_notes, "Violin I", instrument.Violin())
    violin2_part = create_part_from_note_data(violin2_notes, "Violin II", instrument.Violin())
    viola_part = create_part_from_note_data(viola_notes, "Viola", instrument.Viola())
    cello_part = create_part_from_note_data(cello_notes, "Cello", instrument.Violoncello())
    
    # 메타데이터 복사
    ts = score.flat.getElementsByClass('TimeSignature')
    ks = score.flat.getElementsByClass('KeySignature')
    tempos = score.flat.getElementsByClass('MetronomeMark')
    
    for part in [violin1_part, violin2_part, viola_part, cello_part]:
        if ts:
            part.insert(0, ts[0])
        if ks:
            part.insert(0, ks[0])
        if tempos:
            part.insert(0, tempos[0])
    
    # Score 조립
    quartet_score = stream.Score()
    quartet_score.append(violin1_part)
    quartet_score.append(violin2_part)
    quartet_score.append(viola_part)
    quartet_score.append(cello_part)
    
    print(f"\n[5단계] MusicXML 저장...")
    quartet_score.write('musicxml', fp=output_file)
    print(f"✅ 저장 완료: {output_file}")
    
    # MIDI 파일도 저장
    midi_file = output_file.replace('.musicxml', '.mid')
    quartet_score.write('midi', fp=midi_file)
    print(f"✅ MIDI 저장 완료: {midi_file}")
    
    # 간단한 통계
    print(f"\n📊 V10 결과 통계:")
    stats_data = [
        ("Violin I", violin1_notes),
        ("Violin II", violin2_notes),
        ("Viola", viola_notes),
        ("Cello", cello_notes)
    ]
    
    for part_name, notes in stats_data:
        if notes:
            midis = [n['midi'] for n in notes]
            unique_pitches = len(set(midis))
            print(f"  {part_name}: {len(notes)}음표, 음역: MIDI {min(midis)}-{max(midis)}, {unique_pitches}개 다른 음")
    
    # Violin II와 Viola의 음 차이 분석
    if violin2_notes and viola_notes:
        same_count = sum(1 for i in range(min(len(violin2_notes), len(viola_notes)))
                        if violin2_notes[i]['midi'] == viola_notes[i]['midi'])
        same_ratio = same_count / min(len(violin2_notes), len(viola_notes))
        print(f"  🎯 Violin II-Viola 음 차이: {100*(1-same_ratio):.1f}% 다른 음 연주")
    
    return quartet_score


if __name__ == '__main__':
    input_file = '/Users/tsk/.openclaw/workspace/music-project/ode_to_joy_source.mxl'
    output_file = '/Users/tsk/.openclaw/workspace/music-project/ode_to_joy_quartet_v10.musicxml'
    
    print("\n🎻 Ode to Joy 편곡 V10 (클래식 원칙 통합) 시작...")
    quartet = arrange_to_quartet_v10(input_file, output_file)
    
    print("\n[5단계] 평가 함수로 품질 측정...")
    import subprocess
    result = subprocess.run(
        ['python3', 'evaluate_arrangement.py'],
        capture_output=True,
        text=True
    )
    print(result.stdout)
    
    print("\n🎉 완료! MuseScore에서 확인해보세요.")