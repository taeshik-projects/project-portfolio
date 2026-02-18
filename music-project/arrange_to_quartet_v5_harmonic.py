#!/usr/bin/env python3
"""
오케스트라 총보 → String Quartet 자동 편곡 V5

화성 기반 접근:
- 시간 segment 단위 (0.5박자)
- 각 segment의 화성 감 파악 (pitch class 가중치)
- 화성에 맞는 4성부 구성
- 원곡 duration 보존
"""

from music21 import converter, stream, note, instrument, chord as music21_chord
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


def analyze_harmony_in_segment(score, start_offset, end_offset):
    """
    segment 내 화성 분석
    
    Returns:
        {
            'pitch_class_weights': {pc: weight},
            'bass_candidates': [(midi, weight)],
            'melody_candidates': [(midi, weight)],
            'duration_weights': {duration: weight}
        }
    """
    pitch_class_weights = defaultdict(float)
    bass_candidates = []
    melody_candidates = []
    duration_weights = defaultdict(float)
    
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
        
        for element in part.flatten().notesAndRests:
            if element.isRest:
                continue
            
            note_start = element.offset
            note_end = note_start + element.quarterLength
            
            if note_start >= end_offset or note_end <= start_offset:
                continue
            
            overlap = min(note_end, end_offset) - max(note_start, start_offset)
            if overlap <= 0:
                continue
            
            # Duration 가중치 (더 긴 음이 더 중요)
            duration_weight = element.quarterLength ** 0.7  # 제곱근으로 완화
            
            # 강박 가중치
            beat_pos = note_start % 4.0
            if beat_pos in [0.0, 2.0]:
                beat_weight = 1.5
            else:
                beat_weight = 1.0
            
            total_weight = role_weight * duration_weight * beat_weight * overlap
            
            # Duration 기록
            duration_weights[element.quarterLength] += total_weight
            
            # 음 처리
            pitches = []
            if hasattr(element, 'pitch'):
                pitches = [element.pitch]
            elif hasattr(element, 'pitches'):
                pitches = element.pitches
            
            for p in pitches:
                midi = p.midi
                pc = midi % 12  # pitch class
                
                # Pitch class 가중치
                pitch_class_weights[pc] += total_weight
                
                # 베이스 후보 (낮은 음)
                if midi < 60:  # C3 아래
                    bass_candidates.append((midi, total_weight * 2.0))  # 베이스 보너스
                
                # 멜로디 후보 (높은 음)
                if midi > 72:  # C5 위
                    melody_candidates.append((midi, total_weight * 1.5))  # 멜로디 보너스
    
    return {
        'pitch_class_weights': pitch_class_weights,
        'bass_candidates': bass_candidates,
        'melody_candidates': melody_candidates,
        'duration_weights': duration_weights
    }


def select_harmonic_voices(harmony_data, segment_length):
    """
    화성 데이터를 기반으로 4성부 선택
    
    Returns:
        (cello_midi, viola_midi, violin2_midi, violin1_midi, duration)
    """
    pc_weights = harmony_data['pitch_class_weights']
    bass_candidates = harmony_data['bass_candidates']
    melody_candidates = harmony_data['melody_candidates']
    duration_weights = harmony_data['duration_weights']
    
    if not pc_weights:
        return None
    
    # 1. 가장 중요한 4개 pitch class 선택
    top_pcs = sorted(pc_weights.items(), key=lambda x: x[1], reverse=True)[:4]
    
    # 2. 각 pitch class에 대한 대표 MIDI 선택
    selected_midis = []
    
    for pc, weight in top_pcs:
        # 이 pitch class의 적절한 옥타브 찾기
        # 기본적으로 중간 음역(C4 = MIDI 60) 근처
        base_midi = 60 + pc
        
        # 베이스나 멜로디 후보가 있으면 조정
        if pc in [b[0] % 12 for b in bass_candidates]:
            # 베이스 후보 있으면 낮은 옥타브
            base_midi = 36 + pc  # C2 근처
        
        selected_midis.append(base_midi)
    
    # 3. 4개 미만이면 중복 또는 채우기
    while len(selected_midis) < 4:
        if len(selected_midis) == 0:
            selected_midis.append(48)  # C3
        else:
            selected_midis.append(selected_midis[-1] + 7)  # 5도 위
    
    # 4. 베이스와 멜로디 우선순위
    if bass_candidates:
        # 가장 가중치 높은 베이스 후보
        best_bass = max(bass_candidates, key=lambda x: x[1])[0]
        # selected_midis 중 가장 낮은 음을 베이스로 교체
        selected_midis[0] = min(selected_midis[0], best_bass)
    
    if melody_candidates:
        # 가장 가중치 높은 멜로디 후보
        best_melody = max(melody_candidates, key=lambda x: x[1])[0]
        # selected_midis 중 가장 높은 음을 멜로디로 교체
        selected_midis[-1] = max(selected_midis[-1], best_melody)
    
    # 5. MIDI 정렬 (낮은 음부터)
    selected_midis.sort()
    
    # 6. 음역 조정
    cello_midi = transpose_to_range(selected_midis[0], INSTRUMENT_RANGES['cello'][0], INSTRUMENT_RANGES['cello'][1])
    viola_midi = transpose_to_range(selected_midis[1], INSTRUMENT_RANGES['viola'][0], INSTRUMENT_RANGES['viola'][1])
    violin2_midi = transpose_to_range(selected_midis[2], INSTRUMENT_RANGES['violin'][0], INSTRUMENT_RANGES['violin'][1])
    violin1_midi = transpose_to_range(selected_midis[3], INSTRUMENT_RANGES['violin'][0], INSTRUMENT_RANGES['violin'][1])
    
    # 7. Duration: 가장 지배적인 것 선택
    if duration_weights:
        best_duration = max(duration_weights.items(), key=lambda x: x[1])[0]
        # segment_length를 초과하지 않도록
        duration = min(best_duration, segment_length)
    else:
        duration = segment_length
    
    return (cello_midi, viola_midi, violin2_midi, violin1_midi, duration)


def arrange_to_quartet_v5(input_file, output_file, segment_length=0.5):
    """
    오케스트라 총보 → String Quartet 편곡 V5
    
    화성 기반 접근
    """
    print("=" * 70)
    print("🎼 String Quartet 자동 편곡 V5 (화성 기반)")
    print("=" * 70)
    
    print("\n[1단계] 원곡 로딩...")
    score = converter.parse(input_file)
    score = score.toSoundingPitch()
    print(f"✅ {len(score.parts)} 파트 로딩 완료")
    
    # 총 길이 계산
    first_part = score.parts[0]
    measures = first_part.getElementsByClass('Measure')
    total_length = measures[-1].offset + measures[-1].quarterLength if measures else 0
    
    print(f"\n[2단계] 시간 단위별 분석 (단위: {segment_length}박자)...")
    num_segments = int(total_length / segment_length) + 1
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
    
    print("\n[3단계] 화성 분석 및 4성부 배치...")
    
    for i in range(num_segments):
        segment_start = i * segment_length
        segment_end = segment_start + segment_length
        
        # 화성 분석
        harmony_data = analyze_harmony_in_segment(score, segment_start, segment_end)
        
        # 4성부 선택
        result = select_harmonic_voices(harmony_data, segment_length)
        
        if result:
            cello_midi, viola_midi, violin2_midi, violin1_midi, duration = result
            
            # 각 파트에 노트 추가
            violin1_part.append(note.Note(violin1_midi, quarterLength=duration))
            violin2_part.append(note.Note(violin2_midi, quarterLength=duration))
            viola_part.append(note.Note(viola_midi, quarterLength=duration))
            cello_part.append(note.Note(cello_midi, quarterLength=duration))
        else:
            # 쉼표
            for part in [violin1_part, violin2_part, viola_part, cello_part]:
                part.append(note.Rest(quarterLength=segment_length))
        
        if (i + 1) % 50 == 0:
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
    output_file = '/Users/tsk/.openclaw/workspace/music-project/ode_to_joy_quartet_v5.musicxml'
    
    print("\n🎻 Ode to Joy 편곡 V5 시작...")
    quartet = arrange_to_quartet_v5(input_file, output_file, segment_length=0.5)
    print("\n🎉 완료! MuseScore에서 확인해보세요.")
