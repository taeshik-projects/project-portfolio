#!/usr/bin/env python3
"""
오케스트라 총보 → String Quartet 자동 편곡 V4

원곡의 리듬/articulation 완전 보존:
- 각 note onset(시작 시간)마다 4개 음 선택
- 원곡의 duration을 그대로 사용
- 음역만 조정
"""

from music21 import converter, stream, note, instrument
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


def collect_all_onsets_and_notes(score):
    """
    모든 note onset과 해당 시점의 음들 수집
    
    Returns:
        {offset: [note_data, ...]}
    """
    notes_by_onset = defaultdict(list)
    
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
            
            if not hasattr(element, 'pitch') and not hasattr(element, 'pitches'):
                continue
            
            offset = element.offset
            duration = element.quarterLength
            
            # Duration 가중치
            if duration < 0.5:
                duration_weight = 0.5
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
            
            total_weight = role_weight * duration_weight * beat_weight
            
            # 음 추가
            pitches_to_add = []
            if hasattr(element, 'pitch'):
                pitches_to_add = [element.pitch]
            elif hasattr(element, 'pitches'):
                pitches_to_add = element.pitches
            
            for p in pitches_to_add:
                notes_by_onset[offset].append({
                    'midi': p.midi,
                    'weight': total_weight,
                    'duration': duration,
                    'role': role
                })
    
    return notes_by_onset


def select_four_voices_at_onset(notes_at_onset):
    """
    특정 onset에서 4성부 선택
    
    Returns:
        (cello_midi, viola_midi, violin2_midi, violin1_midi, duration)
    """
    if not notes_at_onset:
        return None
    
    # MIDI별 가중치 합산
    midi_weights = defaultdict(float)
    midi_durations = {}
    
    for note_data in notes_at_onset:
        midi = note_data['midi']
        midi_weights[midi] += note_data['weight']
        
        # 가장 긴 duration 기록
        if midi not in midi_durations or note_data['duration'] > midi_durations[midi]:
            midi_durations[midi] = note_data['duration']
    
    # 가장 낮은 음에 보너스 (베이스)
    if midi_weights:
        lowest_midi = min(midi_weights.keys())
        midi_weights[lowest_midi] *= 3.0
    
    # 상위 4개 선택
    top_4 = sorted(midi_weights.items(), key=lambda x: x[1], reverse=True)[:4]
    
    if len(top_4) < 4:
        # 4개 미만이면 같은 음 중복 사용
        while len(top_4) < 4:
            top_4.append(top_4[-1])
    
    # MIDI 순으로 정렬 (낮은 음부터)
    selected = sorted(top_4, key=lambda x: x[0])
    
    # 음역 조정
    cello_midi = transpose_to_range(selected[0][0], INSTRUMENT_RANGES['cello'][0], INSTRUMENT_RANGES['cello'][1])
    viola_midi = transpose_to_range(selected[1][0], INSTRUMENT_RANGES['viola'][0], INSTRUMENT_RANGES['viola'][1])
    violin2_midi = transpose_to_range(selected[2][0], INSTRUMENT_RANGES['violin'][0], INSTRUMENT_RANGES['violin'][1])
    violin1_midi = transpose_to_range(selected[3][0], INSTRUMENT_RANGES['violin'][0], INSTRUMENT_RANGES['violin'][1])
    
    # Duration: 선택된 음들 중 가장 긴 것 사용
    max_duration = max([midi_durations.get(midi, 1.0) for midi, _ in selected])
    
    return (cello_midi, viola_midi, violin2_midi, violin1_midi, max_duration)


def arrange_to_quartet_v4(input_file, output_file):
    """
    오케스트라 총보 → String Quartet 편곡 V4
    
    원곡 리듬 완전 보존
    """
    print("=" * 70)
    print("🎼 String Quartet 자동 편곡 V4")
    print("=" * 70)
    
    print("\n[1단계] 원곡 로딩...")
    score = converter.parse(input_file)
    score = score.toSoundingPitch()
    print(f"✅ {len(score.parts)} 파트 로딩 완료")
    
    print("\n[2단계] 모든 note onset 수집...")
    notes_by_onset = collect_all_onsets_and_notes(score)
    sorted_onsets = sorted(notes_by_onset.keys())
    print(f"✅ {len(sorted_onsets)}개 onset 발견")
    
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
    
    print("\n[3단계] 각 onset마다 4성부 배치...")
    
    for i, onset in enumerate(sorted_onsets):
        notes_at_onset = notes_by_onset[onset]
        
        # 4성부 선택
        result = select_four_voices_at_onset(notes_at_onset)
        
        if result:
            cello_midi, viola_midi, violin2_midi, violin1_midi, duration = result
            
            # 각 파트에 노트 추가 (원곡 duration 그대로)
            violin1_part.append(note.Note(violin1_midi, quarterLength=duration))
            violin2_part.append(note.Note(violin2_midi, quarterLength=duration))
            viola_part.append(note.Note(viola_midi, quarterLength=duration))
            cello_part.append(note.Note(cello_midi, quarterLength=duration))
        
        if (i + 1) % 50 == 0:
            print(f"  진행: {i + 1}/{len(sorted_onsets)} ({100 * (i + 1) / len(sorted_onsets):.1f}%)")
    
    print(f"✅ {len(sorted_onsets)}개 onset 편곡 완료")
    
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
    output_file = '/Users/tsk/.openclaw/workspace/music-project/ode_to_joy_quartet_v4.musicxml'
    
    print("\n🎻 Ode to Joy 편곡 V4 시작...")
    quartet = arrange_to_quartet_v4(input_file, output_file)
    print("\n🎉 완료! MuseScore에서 확인해보세요.")
