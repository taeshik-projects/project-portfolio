#!/usr/bin/env python3
"""
오케스트라 총보 → String Quartet 자동 편곡 V2

개선사항:
- 원곡의 리듬 보존
- 각 악기의 음역(range) 고려
- Passing notes 보존 (멜로디에 필수적)
"""

from music21 import converter, stream, note, instrument, chord
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


def extract_voice_line(score, role_filter, target_range):
    """
    특정 역할의 파트들에서 주요 선율 추출
    
    Args:
        role_filter: 'bass', 'melody', 'inner'
        target_range: (min_midi, max_midi)
    
    Returns:
        List of (offset, duration, midi)
    """
    notes_by_time = defaultdict(list)
    
    # 해당 역할의 모든 음 수집
    for part in score.parts:
        role = classify_role(part)
        if role != role_filter:
            continue
        
        inst = part.getInstrument()
        if inst and 'drum' in inst.instrumentName.lower():
            continue
        
        for element in part.flatten().notesAndRests:
            if element.isRest:
                continue
            
            offset = element.offset
            duration = element.quarterLength
            
            # Duration 가중치
            if duration < 0.5:
                weight = 0.3  # Passing notes도 보존하되 가중치는 낮게
            elif duration < 1.0:
                weight = 1.0
            else:
                weight = 2.0
            
            # 강박 가중치
            beat_pos = offset % 4.0
            if beat_pos in [0.0, 2.0]:
                beat_weight = 1.5
            else:
                beat_weight = 1.0
            
            total_weight = weight * beat_weight
            
            if hasattr(element, 'pitch'):
                notes_by_time[offset].append({
                    'midi': element.pitch.midi,
                    'duration': duration,
                    'weight': total_weight
                })
            elif hasattr(element, 'pitches'):
                # 코드인 경우 가장 높은 음 (멜로디) 또는 가장 낮은 음 (베이스)
                if role_filter == 'bass':
                    p = min(element.pitches, key=lambda x: x.midi)
                else:
                    p = max(element.pitches, key=lambda x: x.midi)
                
                notes_by_time[offset].append({
                    'midi': p.midi,
                    'duration': duration,
                    'weight': total_weight
                })
    
    # 각 시간마다 가장 중요한 음 선택
    result = []
    for offset in sorted(notes_by_time.keys()):
        candidates = notes_by_time[offset]
        if not candidates:
            continue
        
        # 가중치 최고인 음 선택
        best = max(candidates, key=lambda x: x['weight'])
        
        # 음역 조정
        adjusted_midi = transpose_to_range(best['midi'], target_range[0], target_range[1])
        
        result.append({
            'offset': offset,
            'duration': best['duration'],
            'midi': adjusted_midi
        })
    
    return result


def merge_overlapping_notes(notes):
    """
    겹치는 음들을 병합
    
    같은 음이 연속으로 나오면 하나로 합침
    """
    if not notes:
        return []
    
    merged = []
    current = notes[0].copy()
    
    for i in range(1, len(notes)):
        next_note = notes[i]
        current_end = current['offset'] + current['duration']
        
        # 다음 음이 현재 음과 같고, 타이밍이 연결되면 병합
        if (next_note['midi'] == current['midi'] and 
            abs(next_note['offset'] - current_end) < 0.1):
            current['duration'] = next_note['offset'] + next_note['duration'] - current['offset']
        else:
            merged.append(current)
            current = next_note.copy()
    
    merged.append(current)
    return merged


def fill_harmony(score, bass_notes, melody_notes, target_range):
    """
    베이스와 멜로디 사이를 채우는 하모니 파트 생성
    """
    notes_by_time = defaultdict(list)
    
    # Inner voices에서 음 수집
    for part in score.parts:
        role = classify_role(part)
        if role not in ['inner', 'melody']:
            continue
        
        inst = part.getInstrument()
        if inst and 'drum' in inst.instrumentName.lower():
            continue
        
        for element in part.flatten().notesAndRests:
            if element.isRest:
                continue
            
            offset = element.offset
            duration = element.quarterLength
            
            weight = duration * (1.5 if offset % 4.0 in [0.0, 2.0] else 1.0)
            
            if hasattr(element, 'pitch'):
                notes_by_time[offset].append({
                    'midi': element.pitch.midi,
                    'duration': duration,
                    'weight': weight
                })
            elif hasattr(element, 'pitches'):
                for p in element.pitches:
                    notes_by_time[offset].append({
                        'midi': p.midi,
                        'duration': duration,
                        'weight': weight
                    })
    
    # 각 시간마다 중간 음역의 음 선택
    result = []
    for offset in sorted(notes_by_time.keys()):
        candidates = notes_by_time[offset]
        if not candidates:
            continue
        
        # 음역에 맞는 후보만
        valid = [c for c in candidates 
                 if target_range[0] <= transpose_to_range(c['midi'], target_range[0], target_range[1]) <= target_range[1]]
        
        if not valid:
            continue
        
        # 가중치 최고
        best = max(valid, key=lambda x: x['weight'])
        adjusted_midi = transpose_to_range(best['midi'], target_range[0], target_range[1])
        
        result.append({
            'offset': offset,
            'duration': best['duration'],
            'midi': adjusted_midi
        })
    
    return merge_overlapping_notes(result)


def create_part_from_notes(notes_data, part_name, inst_obj):
    """음 리스트를 Part로 변환"""
    part = stream.Part()
    part.partName = part_name
    part.insert(0, inst_obj)
    
    for note_data in notes_data:
        n = note.Note(note_data['midi'])
        n.quarterLength = note_data['duration']
        part.insert(note_data['offset'], n)
    
    # ★ 중요: 마디 구조 생성
    part.makeMeasures(inPlace=True)
    
    return part


def arrange_to_quartet_v2(input_file, output_file):
    """
    오케스트라 총보 → String Quartet 편곡 V2
    
    리듬 보존 + 음역 고려
    """
    print("=" * 70)
    print("🎼 String Quartet 자동 편곡 V2")
    print("=" * 70)
    
    print("\n[1단계] 원곡 로딩...")
    score = converter.parse(input_file)
    score = score.toSoundingPitch()
    print(f"✅ {len(score.parts)} 파트 로딩 완료")
    
    print("\n[2단계] 4성부 추출 (리듬 보존)...")
    
    # Cello: 베이스 라인
    print("  🎻 Cello (Bass line) 추출 중...")
    cello_notes = extract_voice_line(score, 'bass', INSTRUMENT_RANGES['cello'])
    cello_notes = merge_overlapping_notes(cello_notes)
    print(f"     ✅ {len(cello_notes)}개 음표")
    
    # Violin I: 멜로디
    print("  🎻 Violin I (Melody) 추출 중...")
    violin1_notes = extract_voice_line(score, 'melody', INSTRUMENT_RANGES['violin'])
    violin1_notes = merge_overlapping_notes(violin1_notes)
    print(f"     ✅ {len(violin1_notes)}개 음표")
    
    # Viola & Violin II: 하모니
    print("  🎻 Viola (Harmony) 추출 중...")
    viola_notes = fill_harmony(score, cello_notes, violin1_notes, INSTRUMENT_RANGES['viola'])
    print(f"     ✅ {len(viola_notes)}개 음표")
    
    print("  🎻 Violin II (Harmony) 추출 중...")
    violin2_notes = fill_harmony(score, cello_notes, violin1_notes, 
                                  (INSTRUMENT_RANGES['viola'][0], INSTRUMENT_RANGES['violin'][1]))
    print(f"     ✅ {len(violin2_notes)}개 음표")
    
    print("\n[3단계] Score 조립...")
    
    # 메타데이터 추출
    ts = score.flat.getElementsByClass('TimeSignature')
    ks = score.flat.getElementsByClass('KeySignature')
    tempos = score.flat.getElementsByClass('MetronomeMark')
    
    # 4개 파트 생성
    violin1_part = create_part_from_notes(violin1_notes, "Violin I", instrument.Violin())
    violin2_part = create_part_from_notes(violin2_notes, "Violin II", instrument.Violin())
    viola_part = create_part_from_notes(viola_notes, "Viola", instrument.Viola())
    cello_part = create_part_from_notes(cello_notes, "Cello", instrument.Violoncello())
    
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
    
    print("\n[4단계] MusicXML 저장...")
    quartet_score.write('musicxml', fp=output_file)
    print(f"✅ 저장 완료: {output_file}")
    
    return quartet_score


if __name__ == '__main__':
    input_file = '/Users/tsk/.openclaw/workspace/music-project/ode_to_joy_source.mxl'
    output_file = '/Users/tsk/.openclaw/workspace/music-project/ode_to_joy_quartet_v2.musicxml'
    
    print("\n🎻 Ode to Joy 편곡 V2 시작...")
    quartet = arrange_to_quartet_v2(input_file, output_file)
    print("\n🎉 완료! MuseScore에서 확인해보세요.")
