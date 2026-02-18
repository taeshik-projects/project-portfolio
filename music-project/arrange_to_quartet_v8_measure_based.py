#!/usr/bin/env python3
"""
오케스트라 총보 → String Quartet 자동 편곡 V8

마디 단위 접근:
- 원곡의 각 마디(measure)를 분석
- 마디 내 리듬 패턴 그대로 복사
- 4성부에 맞게 음높이만 역할 기반으로 선택
- 마디 경계 정확히 지키기
"""

from music21 import converter, stream, note, instrument, meter
from collections import defaultdict, Counter

# 현악기 음역 (MIDI 번호)
INSTRUMENT_RANGES = {
    'violin': (55, 103),    # G3 ~ G7
    'viola': (48, 91),      # C3 ~ G6
    'cello': (36, 84)       # C2 ~ C6
}

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


def transpose_to_range(midi, min_midi, max_midi):
    """음을 악기 음역에 맞게 조정"""
    while midi < min_midi:
        midi += 12
    while midi > max_midi:
        midi -= 12
    return midi


def extract_rhythm_from_measure(measure):
    """
    마디에서 리듬 패턴 추출
    
    Returns:
        [(offset_in_measure, duration), ...]
    """
    rhythm_pattern = []
    
    for element in measure.notesAndRests:
        if element.isRest or hasattr(element, 'pitch') or hasattr(element, 'pitches'):
            rhythm_pattern.append({
                'offset': element.offset,
                'duration': element.quarterLength
            })
    
    # offset 기준 정렬
    rhythm_pattern.sort(key=lambda x: x['offset'])
    
    # 중복 offset 제거 (같은 시간에 시작하는 음표들 중 하나만)
    unique_pattern = []
    seen_offsets = set()
    
    for r in rhythm_pattern:
        offset_key = round(r['offset'], 2)  # 소수점 2자리까지 비교
        if offset_key not in seen_offsets:
            seen_offsets.add(offset_key)
            unique_pattern.append(r)
    
    return unique_pattern


def analyze_measure_harmony(score, measure_index):
    """
    특정 마디의 화성 분석
    
    Returns:
        {
            'rhythm_pattern': [(offset, duration), ...],
            'melody_notes': [(offset, midi, weight), ...],
            'bass_notes': [(offset, midi, weight), ...],
            'harmony_notes': [(offset, midi, weight), ...]
        }
    """
    # 리듬 패턴 추출 (첫 번째 파트에서)
    first_part = score.parts[0]
    measures = first_part.getElementsByClass('Measure')
    if measure_index >= len(measures):
        return None
    
    measure = measures[measure_index]
    rhythm_pattern = extract_rhythm_from_measure(measure)
    
    # 각 offset에서의 음들 수집
    melody_notes = defaultdict(list)
    bass_notes = defaultdict(list)
    harmony_notes = defaultdict(list)
    
    # 마디 시작 offset 찾기
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
        
        # 이 파트의 해당 마디 찾기
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
                duration_weight = 0.3  # passing notes
            elif duration < 1.0:
                duration_weight = 1.0
            else:
                duration_weight = 2.0
            
            # 강박 가중치 (마디 내에서)
            if offset_in_measure in [0.0, 2.0]:
                beat_weight = 1.5
            else:
                beat_weight = 1.0
            
            total_weight = role_weight * duration_weight * beat_weight
            
            # 음 처리
            pitches = []
            if hasattr(element, 'pitch'):
                pitches = [element.pitch]
            elif hasattr(element, 'pitches'):
                pitches = element.pitches
            
            for p in pitches:
                note_data = {
                    'midi': p.midi,
                    'weight': total_weight,
                    'duration': duration
                }
                
                if role == 'melody' and p.midi > 60:  # C3 이상
                    melody_notes[offset_in_measure].append(note_data)
                elif role == 'bass' and p.midi < 72:  # C5 이하
                    bass_notes[offset_in_measure].append(note_data)
                else:
                    harmony_notes[offset_in_measure].append(note_data)
    
    # 각 offset에서 가장 중요한 음 선택
    def select_best_notes(notes_dict, is_melody=False, is_bass=False):
        result = []
        for offset in sorted(notes_dict.keys()):
            candidates = notes_dict[offset]
            if not candidates:
                continue
            
            # 가중치 기준 선택
            if is_bass:
                # 베이스: 낮은 음 우선 (같은 가중치면)
                candidates.sort(key=lambda x: (x['weight'], -x['midi']), reverse=True)
            elif is_melody:
                # 멜로디: 높은 음 우선 (같은 가중치면)
                candidates.sort(key=lambda x: (x['weight'], x['midi']), reverse=True)
            else:
                # 하모니: 가중치만
                candidates.sort(key=lambda x: x['weight'], reverse=True)
            
            best = candidates[0]
            result.append({
                'offset': offset,
                'midi': best['midi'],
                'duration': best['duration'],
                'weight': best['weight']
            })
        
        return result
    
    selected_melody = select_best_notes(melody_notes, is_melody=True)
    selected_bass = select_best_notes(bass_notes, is_bass=True)
    selected_harmony = select_best_notes(harmony_notes)
    
    return {
        'rhythm_pattern': rhythm_pattern,
        'melody_notes': selected_melody,
        'bass_notes': selected_bass,
        'harmony_notes': selected_harmony
    }


def create_voice_from_selected_notes(selected_notes, rhythm_pattern, voice_role, measure_start):
    """
    선택된 음들과 리듬 패턴을 바탕으로 한 성부 생성
    
    Args:
        selected_notes: [{'offset':, 'midi':, 'duration':, 'weight':}, ...]
        rhythm_pattern: 마디의 리듬 패턴
        voice_role: 'melody', 'bass', 'harmony1', 'harmony2'
        measure_start: 마디 시작 offset
    
    Returns:
        stream.Part
    """
    # offset별 선택된 음 매핑
    notes_by_offset = {note['offset']: note for note in selected_notes}
    
    # 음 생성
    voice_notes = []
    
    for rhythm in rhythm_pattern:
        offset = rhythm['offset']
        duration = rhythm['duration']
        
        if offset in notes_by_offset:
            # 선택된 음이 있으면 사용
            selected = notes_by_offset[offset]
            midi = selected['midi']
        else:
            # 선택된 음이 없으면 가장 가까운 음 찾기
            closest_note = None
            min_diff = float('inf')
            
            for note in selected_notes:
                note_start = note['offset']
                note_end = note_start + note['duration']
                
                # 이 음이 이 offset을 포함하는지
                if note_start <= offset < note_end:
                    diff = 0
                    closest_note = note
                    break
                
                # 아니면 가장 가까운 음
                diff = abs(note_start - offset)
                if diff < min_diff:
                    min_diff = diff
                    closest_note = note
            
            if closest_note and min_diff < 1.0:  # 1박자 이내면
                midi = closest_note['midi']
            else:
                # 없으면 기본값 (쉼표)
                voice_notes.append({
                    'offset': measure_start + offset,
                    'is_rest': True,
                    'duration': duration
                })
                continue
        
        # 음역 조정
        if voice_role == 'melody' or voice_role == 'harmony1':
            min_midi, max_midi = INSTRUMENT_RANGES['violin']
        elif voice_role == 'harmony2':
            min_midi, max_midi = INSTRUMENT_RANGES['viola']
        elif voice_role == 'bass':
            min_midi, max_midi = INSTRUMENT_RANGES['cello']
        else:
            min_midi, max_midi = 0, 127
        
        adjusted_midi = transpose_to_range(midi, min_midi, max_midi)
        
        voice_notes.append({
            'offset': measure_start + offset,
            'midi': adjusted_midi,
            'duration': duration,
            'is_rest': False
        })
    
    # 겹치는 음 병합
    merged_notes = []
    if voice_notes:
        voice_notes.sort(key=lambda x: x['offset'])
        current = voice_notes[0].copy()
        
        for i in range(1, len(voice_notes)):
            next_note = voice_notes[i]
            
            # 둘 다 쉼표면 병합
            if current.get('is_rest', False) and next_note.get('is_rest', False):
                current_end = current['offset'] + current['duration']
                if abs(next_note['offset'] - current_end) < 0.01:
                    current['duration'] = next_note['offset'] + next_note['duration'] - current['offset']
                else:
                    merged_notes.append(current)
                    current = next_note.copy()
            # 둘 다 음표이고 같은 음이면 병합
            elif (not current.get('is_rest', False) and not next_note.get('is_rest', False) and
                  current.get('midi') == next_note.get('midi')):
                current_end = current['offset'] + current['duration']
                if abs(next_note['offset'] - current_end) < 0.01:
                    current['duration'] = next_note['offset'] + next_note['duration'] - current['offset']
                else:
                    merged_notes.append(current)
                    current = next_note.copy()
            else:
                merged_notes.append(current)
                current = next_note.copy()
        
        merged_notes.append(current)
    
    return merged_notes


def arrange_to_quartet_v8(input_file, output_file):
    """
    오케스트라 총보 → String Quartet 편곡 V8
    
    마디 단위 접근
    """
    print("=" * 70)
    print("🎼 String Quartet 자동 편곡 V8 (마디 단위)")
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
    
    # 4개 파트 준비
    violin1_notes = []
    violin2_notes = []
    viola_notes = []
    cello_notes = []
    
    print("\n[2단계] 각 마디별 분석 및 편곡...")
    
    for measure_idx in range(total_measures):
        measure_info = analyze_measure_harmony(score, measure_idx)
        if not measure_info:
            continue
        
        # 마디 시작 offset 계산
        measure_start = measures[measure_idx].offset
        
        # 멜로디 (Violin I)
        melody_voice = create_voice_from_selected_notes(
            measure_info['melody_notes'],
            measure_info['rhythm_pattern'],
            'melody',
            measure_start
        )
        violin1_notes.extend(melody_voice)
        
        # 베이스 (Cello)
        bass_voice = create_voice_from_selected_notes(
            measure_info['bass_notes'],
            measure_info['rhythm_pattern'],
            'bass',
            measure_start
        )
        cello_notes.extend(bass_voice)
        
        # 하모니 (Violin II, Viola)
        harmony_voice1 = create_voice_from_selected_notes(
            measure_info['harmony_notes'],
            measure_info['rhythm_pattern'],
            'harmony1',  # Violin II
            measure_start
        )
        violin2_notes.extend(harmony_voice1)
        
        harmony_voice2 = create_voice_from_selected_notes(
            measure_info['harmony_notes'],
            measure_info['rhythm_pattern'],
            'harmony2',  # Viola
            measure_start
        )
        viola_notes.extend(harmony_voice2)
        
        if (measure_idx + 1) % 5 == 0:
            print(f"  진행: {measure_idx + 1}/{total_measures} 마디")
    
    print(f"✅ {total_measures}마디 편곡 완료")
    
    print("\n[3단계] 4개 파트 생성...")
    
    # 파트 생성 함수
    def create_part_from_note_data(note_data_list, part_name, instrument_obj):
        part = stream.Part()
        part.partName = part_name
        part.insert(0, instrument_obj)
        
        for note_data in note_data_list:
            if note_data.get('is_rest', False):
                n = note.Rest(quarterLength=note_data['duration'])
            else:
                n = note.Note(note_data['midi'], quarterLength=note_data['duration'])
            part.insert(note_data['offset'], n)
        
        # 마디 구조 생성
        part.makeMeasures(inPlace=True)
        return part
    
    # Violin I (멜로디)
    violin1_part = create_part_from_note_data(violin1_notes, "Violin I", instrument.Violin())
    
    # Violin II (하모니)
    violin2_part = create_part_from_note_data(violin2_notes, "Violin II", instrument.Violin())
    
    # Viola (하모니)
    viola_part = create_part_from_note_data(viola_notes, "Viola", instrument.Viola())
    
    # Cello (베이스)
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
    
    print(f"\n[4단계] MusicXML 저장...")
    quartet_score.write('musicxml', fp=output_file)
    print(f"✅ 저장 완료: {output_file}")
    
    # 결과 통계 출력
    print(f"\n📊 결과 통계:")
    for part_name, part_notes in [("Violin I", violin1_notes), ("Violin II", violin2_notes), 
                                   ("Viola", viola_notes), ("Cello", cello_notes)]:
        notes_count = sum(1 for n in part_notes if not n.get('is_rest', False))
        rests_count = sum(1 for n in part_notes if n.get('is_rest', False))
        if part_notes:
            midis = [n['midi'] for n in part_notes if not n.get('is_rest', False)]
            if midis:
                print(f"  {part_name}: {notes_count}음표, {rests_count}쉼표, 음역: MIDI {min(midis)}-{max(midis)}")
    
    return quartet_score


if __name__ == '__main__':
    input_file = '/Users/tsk/.openclaw/workspace/music-project/ode_to_joy_source.mxl'
    output_file = '/Users/tsk/.openclaw/workspace/music-project/ode_to_joy_quartet_v8.musicxml'
    
    print("\n🎻 Ode to Joy 편곡 V8 시작...")
    quartet = arrange_to_quartet_v8(input_file, output_file)
    print("\n🎉 완료! MuseScore에서 확인해보세요.")
