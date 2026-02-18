#!/usr/bin/env python3
"""
오케스트라 총보 → String Quartet 자동 편곡 V7

역할 기반 접근:
- Violin I: 멜로디 라인 (원곡의 가장 중요한 높은 음들)
- Cello: 베이스 라인 (원곡의 가장 중요한 낮은 음들)
- Viola/Violin II: 하모니 (중음역대, 화성 채우기)
"""

from music21 import converter, stream, note, instrument, chord
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


def extract_melody_line(score):
    """
    멜로디 라인 추출 (Violin I 용)
    
    전략: 원곡의 높은 음들 중 가장 중요한 것들 선택
    - 높은 음 (C5 이상)에 가중치 부여
    - duration 길수록, 강박일수록 중요
    - passing notes도 보존하되 가중치 낮게
    """
    melody_notes = []  # (offset, midi, duration)
    
    for part in score.parts:
        role = classify_role(part)
        if role != 'melody':
            continue  # 멜로디 역할 파트만
        
        inst = part.getInstrument()
        if inst and 'drum' in inst.instrumentName.lower():
            continue
        
        for element in part.flatten().notesAndRests:
            if element.isRest:
                continue
            
            if not hasattr(element, 'pitch') and not hasattr(element, 'pitches'):
                continue
            
            offset = element.offset
            duration = element.quarterLength
            
            # Duration 가중치
            if duration < 0.5:
                duration_weight = 0.3  # passing notes
            elif duration < 1.0:
                duration_weight = 1.0
            else:
                duration_weight = 2.0
            
            # 강박 가중치
            beat_pos = offset % 4.0
            if beat_pos in [0.0, 2.0]:
                beat_weight = 1.5
            else:
                beat_weight = 1.0
            
            # 높은 음 보너스
            height_bonus = 1.0
            
            pitches = []
            if hasattr(element, 'pitch'):
                pitches = [element.pitch]
            elif hasattr(element, 'pitches'):
                pitches = element.pitches
            
            for p in pitches:
                if p.midi > 72:  # C5 이상
                    height_bonus = 1.5
                
                total_weight = duration_weight * beat_weight * height_bonus
                
                melody_notes.append({
                    'offset': offset,
                    'midi': p.midi,
                    'duration': duration,
                    'weight': total_weight
                })
    
    # 같은 offset에 여러 음이 있으면 가장 가중치 높은 것 선택
    notes_by_offset = defaultdict(list)
    for note_data in melody_notes:
        notes_by_offset[note_data['offset']].append(note_data)
    
    selected_notes = []
    for offset in sorted(notes_by_offset.keys()):
        candidates = notes_by_offset[offset]
        best = max(candidates, key=lambda x: x['weight'])
        
        # 음역 조정
        adjusted_midi = transpose_to_range(best['midi'], INSTRUMENT_RANGES['violin'][0], INSTRUMENT_RANGES['violin'][1])
        
        selected_notes.append({
            'offset': offset,
            'midi': adjusted_midi,
            'duration': best['duration']
        })
    
    # offset 순으로 정렬
    selected_notes.sort(key=lambda x: x['offset'])
    
    # 겹치는 음 병합 (같은 음이 연속이면 하나로)
    merged_notes = []
    if selected_notes:
        current = selected_notes[0].copy()
        
        for i in range(1, len(selected_notes)):
            next_note = selected_notes[i]
            current_end = current['offset'] + current['duration']
            
            if (next_note['midi'] == current['midi'] and 
                abs(next_note['offset'] - current_end) < 0.1):
                # 같은 음, 연결됨 → 병합
                current['duration'] = next_note['offset'] + next_note['duration'] - current['offset']
            else:
                merged_notes.append(current)
                current = next_note.copy()
        
        merged_notes.append(current)
    
    return merged_notes


def extract_bass_line(score):
    """
    베이스 라인 추출 (Cello 용)
    
    전략: 원곡의 낮은 음들 중 가장 중요한 것들 선택
    - 낮은 음 (C3 이하)에 가중치 부여
    - 베이스 역할 파트 우선
    - 긴 duration 중요
    """
    bass_notes = []  # (offset, midi, duration)
    
    for part in score.parts:
        role = classify_role(part)
        
        # 베이스 역할이면 높은 가중치
        role_weight = 2.0 if role == 'bass' else 1.0
        
        inst = part.getInstrument()
        if inst and 'drum' in inst.instrumentName.lower():
            continue
        
        for element in part.flatten().notesAndRests:
            if element.isRest:
                continue
            
            if not hasattr(element, 'pitch') and not hasattr(element, 'pitches'):
                continue
            
            offset = element.offset
            duration = element.quarterLength
            
            # Duration 가중치 (베이스는 긴 음 중요)
            duration_weight = duration ** 0.7  # 제곱근으로 완화
            
            # 강박 가중치
            beat_pos = offset % 4.0
            if beat_pos in [0.0, 2.0]:
                beat_weight = 1.5
            else:
                beat_weight = 1.0
            
            # 낮은 음 보너스
            pitches = []
            if hasattr(element, 'pitch'):
                pitches = [element.pitch]
            elif hasattr(element, 'pitches'):
                pitches = element.pitches
            
            for p in pitches:
                height_bonus = 1.0
                if p.midi < 60:  # C3 이하
                    height_bonus = 1.5
                
                total_weight = role_weight * duration_weight * beat_weight * height_bonus
                
                bass_notes.append({
                    'offset': offset,
                    'midi': p.midi,
                    'duration': duration,
                    'weight': total_weight
                })
    
    # 같은 offset에 여러 음이 있으면 가장 가중치 높은 것 선택
    notes_by_offset = defaultdict(list)
    for note_data in bass_notes:
        notes_by_offset[note_data['offset']].append(note_data)
    
    selected_notes = []
    for offset in sorted(notes_by_offset.keys()):
        candidates = notes_by_offset[offset]
        best = max(candidates, key=lambda x: x['weight'])
        
        # 음역 조정 (낮은 옥타브)
        adjusted_midi = transpose_to_range(best['midi'], INSTRUMENT_RANGES['cello'][0], INSTRUMENT_RANGES['cello'][1])
        
        selected_notes.append({
            'offset': offset,
            'midi': adjusted_midi,
            'duration': best['duration']
        })
    
    # offset 순으로 정렬
    selected_notes.sort(key=lambda x: x['offset'])
    
    # 겹치는 음 병합
    merged_notes = []
    if selected_notes:
        current = selected_notes[0].copy()
        
        for i in range(1, len(selected_notes)):
            next_note = selected_notes[i]
            current_end = current['offset'] + current['duration']
            
            if (next_note['midi'] == current['midi'] and 
                abs(next_note['offset'] - current_end) < 0.1):
                current['duration'] = next_note['offset'] + next_note['duration'] - current['offset']
            else:
                merged_notes.append(current)
                current = next_note.copy()
        
        merged_notes.append(current)
    
    return merged_notes


def analyze_harmony_at_offsets(score, offsets_with_melody_bass):
    """
    각 offset에서 화성 분석 (중음역대 채우기 용)
    
    Returns:
        {offset: {'pitch_classes': [pc1, pc2, ...], 'available_midis': [midi1, ...]}}
    """
    harmony_data = {}
    
    # 모든 offset의 모든 음 수집
    for offset, _, _ in offsets_with_melody_bass:
        notes_at_offset = []
        
        for part in score.parts:
            inst = part.getInstrument()
            if inst and 'drum' in inst.instrumentName.lower():
                continue
            
            for element in part.flatten().notesAndRests:
                if element.isRest:
                    continue
                
                if abs(element.offset - offset) > 0.01:  # 정확히 같은 offset만
                    continue
                
                if hasattr(element, 'pitch'):
                    notes_at_offset.append({
                        'midi': element.pitch.midi,
                        'duration': element.quarterLength
                    })
                elif hasattr(element, 'pitches'):
                    for p in element.pitches:
                        notes_at_offset.append({
                            'midi': p.midi,
                            'duration': element.quarterLength
                        })
        
        # Pitch classes 수집
        pitch_classes = Counter()
        midis = []
        
        for note_data in notes_at_offset:
            pc = note_data['midi'] % 12
            pitch_classes[pc] += 1
            midis.append(note_data['midi'])
        
        harmony_data[offset] = {
            'pitch_classes': [pc for pc, _ in pitch_classes.most_common(4)],
            'available_midis': list(set(midis))  # 중복 제거
        }
    
    return harmony_data


def fill_harmony_voices(melody_notes, bass_notes, harmony_data):
    """
    중음역대 (Viola, Violin II) 채우기
    
    전략:
    - 각 offset에서 멜로디와 베이스 사이의 음 선택
    - 가능한 실제 원곡의 음 사용
    - 없으면 화성에 맞는 음 생성
    """
    # 모든 offset 수집 (멜로디와 베이스 합침)
    all_offsets = set()
    for note in melody_notes:
        all_offsets.add(note['offset'])
    for note in bass_notes:
        all_offsets.add(note['offset'])
    
    offsets_sorted = sorted(all_offsets)
    
    # 각 offset에서 멜로디와 베이스 찾기
    offset_to_melody = {note['offset']: note for note in melody_notes}
    offset_to_bass = {note['offset']: note for note in bass_notes}
    
    viola_notes = []
    violin2_notes = []
    
    for offset in offsets_sorted:
        melody_note = offset_to_melody.get(offset)
        bass_note = offset_to_bass.get(offset)
        harmony_info = harmony_data.get(offset, {'pitch_classes': [], 'available_midis': []})
        
        if not melody_note and not bass_note:
            # 둘 다 없으면 쉼표
            viola_notes.append({'offset': offset, 'midi': None, 'duration': 0.5})
            violin2_notes.append({'offset': offset, 'midi': None, 'duration': 0.5})
            continue
        
        # Duration 결정 (멜로디 또는 베이스의 duration 사용)
        duration = 0.5
        if melody_note:
            duration = melody_note['duration']
        elif bass_note:
            duration = bass_note['duration']
        
        # 중간 음역대 선택
        target_midis = []
        
        if harmony_info['available_midis']:
            # 원곡의 실제 음 사용
            available = sorted(harmony_info['available_midis'])
            
            # 멜로디와 베이스 제외
            if melody_note:
                available = [m for m in available if abs(m - melody_note['midi']) > 3]
            if bass_note:
                available = [m for m in available if abs(m - bass_note['midi']) > 3]
            
            if len(available) >= 2:
                # Viola: 낮은 쪽, Violin II: 높은 쪽
                viola_midi = available[0] if len(available) > 0 else 60
                violin2_midi = available[1] if len(available) > 1 else 67
            elif len(available) == 1:
                viola_midi = available[0]
                violin2_midi = available[0] + 7  # 5도 위
            else:
                # 없으면 멜로디와 베이스 사이의 적절한 음 생성
                if melody_note and bass_note:
                    middle = (melody_note['midi'] + bass_note['midi']) // 2
                    viola_midi = middle - 3
                    violin2_midi = middle + 3
                elif melody_note:
                    viola_midi = melody_note['midi'] - 7  # 5도 아래
                    violin2_midi = melody_note['midi'] - 4  # 3도 아래
                else:
                    viola_midi = bass_note['midi'] + 4  # 3도 위
                    violin2_midi = bass_note['midi'] + 7  # 5도 위
        else:
            # 화성 정보 없으면 기본값
            viola_midi = 60  # C4
            violin2_midi = 67  # G4
        
        # 음역 조정
        viola_midi = transpose_to_range(viola_midi, INSTRUMENT_RANGES['viola'][0], INSTRUMENT_RANGES['viola'][1])
        violin2_midi = transpose_to_range(violin2_midi, INSTRUMENT_RANGES['violin'][0], INSTRUMENT_RANGES['violin'][1])
        
        viola_notes.append({
            'offset': offset,
            'midi': viola_midi,
            'duration': duration
        })
        
        violin2_notes.append({
            'offset': offset,
            'midi': violin2_midi,
            'duration': duration
        })
    
    return viola_notes, violin2_notes


def create_part_from_note_sequence(note_sequence, part_name, instrument_obj):
    """음 시퀀스를 Part로 변환"""
    part = stream.Part()
    part.partName = part_name
    part.insert(0, instrument_obj)
    
    for note_data in note_sequence:
        if note_data['midi'] is None:
            n = note.Rest(quarterLength=note_data['duration'])
        else:
            n = note.Note(note_data['midi'], quarterLength=note_data['duration'])
        part.insert(note_data['offset'], n)
    
    # 마디 구조 생성
    part.makeMeasures(inPlace=True)
    
    return part


def arrange_to_quartet_v7(input_file, output_file):
    """
    오케스트라 총보 → String Quartet 편곡 V7
    
    역할 기반 접근
    """
    print("=" * 70)
    print("🎼 String Quartet 자동 편곡 V7 (역할 기반)")
    print("=" * 70)
    
    print("\n[1단계] 원곡 로딩...")
    score = converter.parse(input_file)
    score = score.toSoundingPitch()
    print(f"✅ {len(score.parts)} 파트 로딩 완료")
    
    print("\n[2단계] 멜로디 라인 추출 (Violin I)...")
    melody_notes = extract_melody_line(score)
    print(f"✅ {len(melody_notes)}개 멜로디 음표 추출")
    
    print("\n[3단계] 베이스 라인 추출 (Cello)...")
    bass_notes = extract_bass_line(score)
    print(f"✅ {len(bass_notes)}개 베이스 음표 추출")
    
    print("\n[4단계] 화성 분석 (중음역대 채우기)...")
    # 멜로디와 베이스의 offset들
    offsets_with_notes = []
    for note_data in melody_notes:
        offsets_with_notes.append((note_data['offset'], 'melody', note_data['midi']))
    for note_data in bass_notes:
        offsets_with_notes.append((note_data['offset'], 'bass', note_data['midi']))
    
    harmony_data = analyze_harmony_at_offsets(score, offsets_with_notes)
    
    print("\n[5단계] 중음역대 채우기 (Viola, Violin II)...")
    viola_notes, violin2_notes = fill_harmony_voices(melody_notes, bass_notes, harmony_data)
    print(f"✅ Viola: {len(viola_notes)}개, Violin II: {len(violin2_notes)}개")
    
    # 메타데이터 추출
    ts = score.flat.getElementsByClass('TimeSignature')
    ks = score.flat.getElementsByClass('KeySignature')
    tempos = score.flat.getElementsByClass('MetronomeMark')
    
    print("\n[6단계] 4개 파트 생성...")
    
    # Violin I (멜로디)
    violin1_part = create_part_from_note_sequence(melody_notes, "Violin I", instrument.Violin())
    
    # Violin II (하모니)
    violin2_part = create_part_from_note_sequence(violin2_notes, "Violin II", instrument.Violin())
    
    # Viola (하모니)
    viola_part = create_part_from_note_sequence(viola_notes, "Viola", instrument.Viola())
    
    # Cello (베이스)
    cello_part = create_part_from_note_sequence(bass_notes, "Cello", instrument.Violoncello())
    
    # 메타데이터 추가
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
    
    print(f"\n[7단계] MusicXML 저장...")
    quartet_score.write('musicxml', fp=output_file)
    print(f"✅ 저장 완료: {output_file}")
    
    return quartet_score


if __name__ == '__main__':
    input_file = '/Users/tsk/.openclaw/workspace/music-project/ode_to_joy_source.mxl'
    output_file = '/Users/tsk/.openclaw/workspace/music-project/ode_to_joy_quartet_v7.musicxml'
    
    print("\n🎻 Ode to Joy 편곡 V7 시작...")
    quartet = arrange_to_quartet_v7(input_file, output_file)
    print("\n🎉 완료! MuseScore에서 확인해보세요.")
