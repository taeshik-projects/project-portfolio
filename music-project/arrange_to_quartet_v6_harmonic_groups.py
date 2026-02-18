#!/usr/bin/env python3
"""
오케스트라 총보 → String Quartet 자동 편곡 V6

화성 구간 기반 접근:
- 원곡의 모든 onset 수집 (V4의 장점 보존)
- 인접 onset들을 화성 구간으로 그룹화 (1-2박자)
- 각 구간의 지배적인 화성 결정
- 그 화성을 바탕으로 각 onset마다 4성부 선택
- 원곡 duration 완전 보존
"""

from music21 import converter, stream, note, instrument
from collections import defaultdict, Counter
import statistics

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
    모든 note onset과 해당 시점의 음들 수집 (V4와 유사)
    
    Returns:
        [(offset, [note_data, ...]), ...]  # 정렬된 리스트
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
                    'role': role,
                    'pitch': p
                })
    
    # 정렬된 리스트로 변환
    sorted_onsets = sorted(notes_by_onset.items())
    return sorted_onsets


def group_onsets_into_harmonic_segments(sorted_onsets, max_gap=1.0):
    """
    인접한 onset들을 화성 구간으로 그룹화
    
    Args:
        sorted_onsets: [(offset, notes), ...]
        max_gap: 최대 허용 간격 (박자)
    
    Returns:
        [{'start': offset, 'end': offset, 'onsets': [(offset, notes), ...]}, ...]
    """
    if not sorted_onsets:
        return []
    
    segments = []
    current_segment = {
        'start': sorted_onsets[0][0],
        'end': sorted_onsets[0][0],
        'onsets': []
    }
    
    for offset, notes in sorted_onsets:
        if offset - current_segment['end'] > max_gap:
            # 새로운 구간 시작
            segments.append(current_segment)
            current_segment = {
                'start': offset,
                'end': offset,
                'onsets': []
            }
        
        current_segment['onsets'].append((offset, notes))
        current_segment['end'] = max(current_segment['end'], offset)
    
    if current_segment['onsets']:
        segments.append(current_segment)
    
    return segments


def analyze_harmony_in_segment(segment_onsets):
    """
    화성 구간의 지배적인 화성 분석
    
    Returns:
        {
            'primary_pcs': [pc1, pc2, pc3, pc4],  # 가장 중요한 pitch classes
            'bass_midi': 가장 중요한 베이스 MIDI,
            'melody_midi': 가장 중요한 멜로디 MIDI
        }
    """
    pc_weights = defaultdict(float)
    bass_weights = defaultdict(float)
    melody_weights = defaultdict(float)
    
    for offset, notes in segment_onsets:
        for note_data in notes:
            midi = note_data['midi']
            weight = note_data['weight']
            
            # Pitch class
            pc = midi % 12
            pc_weights[pc] += weight
            
            # 베이스 (낮은 음)
            if midi < 60:  # C3 아래
                bass_weights[midi] += weight * 2.0
            
            # 멜로디 (높은 음)
            if midi > 72:  # C5 위
                melody_weights[midi] += weight * 1.5
    
    # 가장 중요한 4개 pitch class
    top_pcs = [pc for pc, _ in sorted(pc_weights.items(), key=lambda x: x[1], reverse=True)[:4]]
    
    # 4개 미만이면 채우기
    while len(top_pcs) < 4:
        if top_pcs:
            last_pc = top_pcs[-1]
            next_pc = (last_pc + 7) % 12  # 5도 위
            top_pcs.append(next_pc)
        else:
            top_pcs.append(0)  # C
    
    # 베이스와 멜로디
    bass_midi = min(bass_weights.keys(), key=lambda x: x) if bass_weights else 48  # C3
    melody_midi = max(melody_weights.keys(), key=lambda x: x) if melody_weights else 72  # C5
    
    return {
        'primary_pcs': top_pcs,
        'bass_midi': bass_midi,
        'melody_midi': melody_midi
    }


def select_voices_for_onset(notes_at_onset, harmony_info, onset_offset):
    """
    특정 onset에서 화성 정보를 바탕으로 4성부 선택
    
    Returns:
        (cello_midi, viola_midi, violin2_midi, violin1_midi, duration)
    """
    if not notes_at_onset:
        return None
    
    # 1. 이 onset의 duration 결정 (가장 긴 duration)
    max_duration = max(note_data['duration'] for note_data in notes_at_onset)
    
    # 2. 화성 정보에서 pitch classes 가져오기
    primary_pcs = harmony_info['primary_pcs']
    bass_midi = harmony_info['bass_midi']
    melody_midi = harmony_info['melody_midi']
    
    # 3. 각 pitch class에 적절한 MIDI 선택
    selected_midis = []
    
    # 베이스: 가장 낮은 pitch class 또는 실제 베이스 MIDI
    bass_pc = primary_pcs[0] if primary_pcs else (bass_midi % 12)
    bass_candidate = bass_midi
    # 베이스 후보 조정: pitch class 맞추기
    while bass_candidate % 12 != bass_pc:
        bass_candidate += 1
    
    selected_midis.append(bass_candidate)
    
    # 중간 음들: 나머지 pitch classes
    for i, pc in enumerate(primary_pcs[1:3] if len(primary_pcs) > 1 else [3, 7]):  # 3음, 5음 기본
        # 적절한 옥타브: 베이스보다 1-2 옥타브 위
        midi_candidate = bass_candidate + 12 * (i + 1)
        while midi_candidate % 12 != pc:
            midi_candidate += 1
        selected_midis.append(midi_candidate)
    
    # 멜로디: 가장 높은 pitch class 또는 실제 멜로디 MIDI
    melody_pc = primary_pcs[-1] if primary_pcs else (melody_midi % 12)
    melody_candidate = melody_midi
    # 멜로디 후보 조정: pitch class 맞추기
    while melody_candidate % 12 != melody_pc:
        melody_candidate += 1
    
    selected_midis.append(melody_candidate)
    
    # 4개 미만이면 채우기
    while len(selected_midis) < 4:
        selected_midis.append(selected_midis[-1] + 12)
    
    # 정렬 (낮은 음부터)
    selected_midis.sort()
    
    # 4. 음역 조정
    cello_midi = transpose_to_range(selected_midis[0], INSTRUMENT_RANGES['cello'][0], INSTRUMENT_RANGES['cello'][1])
    viola_midi = transpose_to_range(selected_midis[1], INSTRUMENT_RANGES['viola'][0], INSTRUMENT_RANGES['viola'][1])
    violin2_midi = transpose_to_range(selected_midis[2], INSTRUMENT_RANGES['violin'][0], INSTRUMENT_RANGES['violin'][1])
    violin1_midi = transpose_to_range(selected_midis[3], INSTRUMENT_RANGES['violin'][0], INSTRUMENT_RANGES['violin'][1])
    
    return (cello_midi, viola_midi, violin2_midi, violin1_midi, max_duration)


def arrange_to_quartet_v6(input_file, output_file):
    """
    오케스트라 총보 → String Quartet 편곡 V6
    
    화성 구간 기반 접근
    """
    print("=" * 70)
    print("🎼 String Quartet 자동 편곡 V6 (화성 구간 기반)")
    print("=" * 70)
    
    print("\n[1단계] 원곡 로딩...")
    score = converter.parse(input_file)
    score = score.toSoundingPitch()
    print(f"✅ {len(score.parts)} 파트 로딩 완료")
    
    print("\n[2단계] 모든 onset 수집...")
    sorted_onsets = collect_all_onsets_and_notes(score)
    print(f"✅ {len(sorted_onsets)}개 onset 발견")
    
    print("\n[3단계] 화성 구간으로 그룹화...")
    harmonic_segments = group_onsets_into_harmonic_segments(sorted_onsets, max_gap=1.0)
    print(f"✅ {len(harmonic_segments)}개 화성 구간 생성")
    
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
    
    print("\n[4단계] 각 구간별 화성 분석 및 편곡...")
    
    total_onsets = 0
    for seg_idx, segment in enumerate(harmonic_segments):
        # 구간 화성 분석
        harmony_info = analyze_harmony_in_segment(segment['onsets'])
        
        # 구간 내 각 onset 처리
        for offset, notes in segment['onsets']:
            result = select_voices_for_onset(notes, harmony_info, offset)
            
            if result:
                cello_midi, viola_midi, violin2_midi, violin1_midi, duration = result
                
                # 각 파트에 노트 추가
                violin1_part.append(note.Note(violin1_midi, quarterLength=duration))
                violin2_part.append(note.Note(violin2_midi, quarterLength=duration))
                viola_part.append(note.Note(viola_midi, quarterLength=duration))
                cello_part.append(note.Note(cello_midi, quarterLength=duration))
            
            total_onsets += 1
        
        if (seg_idx + 1) % 10 == 0:
            print(f"  진행: {seg_idx + 1}/{len(harmonic_segments)} 구간")
    
    print(f"✅ {total_onsets}개 onset 편곡 완료")
    
    # 마디 구조 생성
    print("\n[5단계] 마디 구조 생성...")
    for part in [violin1_part, violin2_part, viola_part, cello_part]:
        part.makeMeasures(inPlace=True)
    
    # Score 조립
    quartet_score = stream.Score()
    quartet_score.append(violin1_part)
    quartet_score.append(violin2_part)
    quartet_score.append(viola_part)
    quartet_score.append(cello_part)
    
    print(f"\n[6단계] MusicXML 저장...")
    quartet_score.write('musicxml', fp=output_file)
    print(f"✅ 저장 완료: {output_file}")
    
    return quartet_score


if __name__ == '__main__':
    input_file = '/Users/tsk/.openclaw/workspace/music-project/ode_to_joy_source.mxl'
    output_file = '/Users/tsk/.openclaw/workspace/music-project/ode_to_joy_quartet_v6.musicxml'
    
    print("\n🎻 Ode to Joy 편곡 V6 시작...")
    quartet = arrange_to_quartet_v6(input_file, output_file)
    print("\n🎉 완료! MuseScore에서 확인해보세요.")
