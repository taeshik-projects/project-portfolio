#!/usr/bin/env python3
"""
오케스트라 총보 → String Quartet 자동 편곡 V3

V1으로 복귀 + 개선:
- 시간 단위별로 4개 음 선택 (화성 보존)
- 리듬 보존 (원곡의 주요 duration 사용)
- 악기 음역 고려
"""

from music21 import converter, stream, note, instrument, meter, key, tempo
from collections import defaultdict

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
    if any(kw in name for kw in ['bass', 'cello', 'tuba', 'contrabass']):
        return 'bass'
    elif any(kw in name for kw in ['violin', 'flute', 'soprano', 'oboe', 'clarinet']):
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


def get_weighted_notes_in_segment(score, start_offset, end_offset):
    """
    시간 구간 내 모든 음을 가중치와 함께 수집
    """
    notes_data = []
    
    for part in score.parts:
        role = classify_role(part)
        
        # 역할별 가중치
        role_weight = {
            'bass': 2.0,
            'melody': 1.5,
            'inner': 1.0
        }.get(role, 1.0)
        
        instrument = part.getInstrument()
        if instrument and 'drum' in instrument.instrumentName.lower():
            continue
        
        for element in part.flatten().notesAndRests:
            if not hasattr(element, 'pitch') and not hasattr(element, 'pitches'):
                continue
            
            note_start = element.offset
            note_end = note_start + element.quarterLength
            
            if note_start >= end_offset or note_end <= start_offset:
                continue
            
            overlap = min(note_end, end_offset) - max(note_start, start_offset)
            if overlap <= 0:
                continue
            
            # Duration 가중치
            if element.quarterLength < 0.5:
                duration_weight = 0.3
            elif element.quarterLength < 1.0:
                duration_weight = 1.0
            else:
                duration_weight = 2.0
            
            # 강박 가중치
            beat_pos = note_start % 4.0
            if beat_pos in [0.0, 2.0]:
                beat_weight = 1.5
            else:
                beat_weight = 1.0
            
            total_weight = role_weight * duration_weight * beat_weight * overlap
            
            # 음 정보 수집
            pitches_to_add = []
            if hasattr(element, 'pitch'):
                pitches_to_add = [element.pitch]
            elif hasattr(element, 'pitches'):
                pitches_to_add = element.pitches
            
            for p in pitches_to_add:
                notes_data.append({
                    'midi': p.midi,
                    'pitch': p,
                    'weight': total_weight,
                    'duration': element.quarterLength,
                    'role': role
                })
    
    return notes_data


def get_dominant_duration(notes_data):
    """구간 내 가장 많이 나타나는 duration 찾기"""
    if not notes_data:
        return 1.0
    
    duration_counts = defaultdict(float)
    for note_data in notes_data:
        duration_counts[note_data['duration']] += note_data['weight']
    
    return max(duration_counts.items(), key=lambda x: x[1])[0]


def select_four_voices(notes_data, segment_length):
    """
    4성부 선택
    
    Returns:
        (cello_midi, viola_midi, violin2_midi, violin1_midi, duration)
    """
    if not notes_data:
        return None
    
    # MIDI별 가중치 합산
    midi_weights = defaultdict(float)
    
    for note_data in notes_data:
        midi = note_data['midi']
        midi_weights[midi] += note_data['weight']
    
    # 가장 낮은 음에 보너스 (베이스)
    if midi_weights:
        lowest_midi = min(midi_weights.keys())
        midi_weights[lowest_midi] *= 3.0
    
    # 상위 4개 선택
    top_4 = sorted(midi_weights.items(), key=lambda x: x[1], reverse=True)[:4]
    
    if len(top_4) < 4:
        return None
    
    # MIDI 순으로 정렬 (낮은 음부터)
    selected_midis = sorted([midi for midi, _ in top_4])
    
    # 음역 조정
    cello_midi = transpose_to_range(selected_midis[0], INSTRUMENT_RANGES['cello'][0], INSTRUMENT_RANGES['cello'][1])
    viola_midi = transpose_to_range(selected_midis[1], INSTRUMENT_RANGES['viola'][0], INSTRUMENT_RANGES['viola'][1])
    violin2_midi = transpose_to_range(selected_midis[2], INSTRUMENT_RANGES['violin'][0], INSTRUMENT_RANGES['violin'][1])
    violin1_midi = transpose_to_range(selected_midis[3], INSTRUMENT_RANGES['violin'][0], INSTRUMENT_RANGES['violin'][1])
    
    # Duration: 구간에서 가장 지배적인 것 사용
    duration = get_dominant_duration(notes_data)
    
    # 하지만 segment_length를 초과하지 않도록
    duration = min(duration, segment_length)
    
    return (cello_midi, viola_midi, violin2_midi, violin1_midi, duration)


def arrange_to_quartet_v3(input_file, output_file, segment_length=0.5):
    """
    오케스트라 총보 → String Quartet 편곡 V3
    
    V1 기반 + 리듬 보존 + 음역 고려
    """
    print("=" * 70)
    print("🎼 String Quartet 자동 편곡 V3")
    print("=" * 70)
    
    print("\n[1단계] 원곡 로딩...")
    score = converter.parse(input_file)
    score = score.toSoundingPitch()
    print(f"✅ {len(score.parts)} 파트 로딩 완료")
    
    # 메타데이터 추출
    first_part = score.parts[0]
    measures = first_part.getElementsByClass('Measure')
    total_length = measures[-1].offset + measures[-1].quarterLength if measures else 0
    
    print(f"\n[2단계] 시간 단위별 분석 (단위: {segment_length}박자)...")
    num_segments = int(total_length / segment_length)
    print(f"✅ 총 {num_segments}개 구간")
    
    # 4개 파트 생성
    violin1_part = stream.Part()
    violin1_part.partName = "Violin I"
    violin1_part.insert(0, instrument.Violin())
    
    violin2_part = stream.Part()
    violin2_part.partName = "Violin II"
    violin2_part.insert(0, instrument.Violin())
    
    viola_part = stream.Part()
    viola_part.partName = "Viola"
    viola_part.insert(0, instrument.Viola())
    
    cello_part = stream.Part()
    cello_part.partName = "Cello"
    cello_part.insert(0, instrument.Violoncello())
    
    # 메타데이터 복사
    ts = score.flat.getElementsByClass('TimeSignature')
    ks = score.flat.getElementsByClass('KeySignature')
    tempos = score.flat.getElementsByClass('MetronomeMark')
    
    for part in [violin1_part, violin2_part, viola_part, cello_part]:
        if ts:
            part.append(ts[0])
        if ks:
            part.append(ks[0])
        if tempos:
            part.append(tempos[0])
    
    print("\n[3단계] 4성부 배치 및 편곡...")
    
    current_offset = 0.0
    
    for i in range(num_segments):
        segment_start = i * segment_length
        segment_end = segment_start + segment_length
        
        # 음 수집
        notes_data = get_weighted_notes_in_segment(score, segment_start, segment_end)
        
        # 4성부 선택
        result = select_four_voices(notes_data, segment_length)
        
        if result:
            cello_midi, viola_midi, violin2_midi, violin1_midi, duration = result
            
            # 각 파트에 노트 추가
            violin1_part.append(note.Note(violin1_midi, quarterLength=duration))
            violin2_part.append(note.Note(violin2_midi, quarterLength=duration))
            viola_part.append(note.Note(viola_midi, quarterLength=duration))
            cello_part.append(note.Note(cello_midi, quarterLength=duration))
            
            current_offset += duration
        else:
            # 4개 못 찾으면 쉼표
            for part in [violin1_part, violin2_part, viola_part, cello_part]:
                part.append(note.Rest(quarterLength=segment_length))
            current_offset += segment_length
        
        if (i + 1) % 100 == 0:
            print(f"  진행: {i + 1}/{num_segments} ({100 * (i + 1) / num_segments:.1f}%)")
    
    print(f"✅ {num_segments}개 구간 편곡 완료")
    
    # 마디 구조 생성
    print("\n[4단계] 마디 구조 생성...")
    for part in [violin1_part, violin2_part, viola_part, cello_part]:
        part.makeMeasures(inPlace=True)
    
    # Score 조립
    quartet_score = stream.Score()
    quartet_score.append(violin1_part)
    quartet_score.append(violin2_part)
    quartet_score.append(viola_part)
    quartet_score.append(cello_part)
    
    print(f"\n[5단계] MusicXML 저장...")
    quartet_score.write('musicxml', fp=output_file)
    print(f"✅ 저장 완료: {output_file}")
    
    return quartet_score


if __name__ == '__main__':
    input_file = '/Users/tsk/.openclaw/workspace/music-project/ode_to_joy_source.mxl'
    output_file = '/Users/tsk/.openclaw/workspace/music-project/ode_to_joy_quartet_v3.musicxml'
    
    print("\n🎻 Ode to Joy 편곡 V3 시작...")
    quartet = arrange_to_quartet_v3(input_file, output_file, segment_length=0.5)
    print("\n🎉 완료! MuseScore에서 확인해보세요.")
