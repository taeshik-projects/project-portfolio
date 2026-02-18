#!/usr/bin/env python3
"""
오케스트라 총보 → String Quartet 자동 편곡

알고리즘:
1. 시간 단위별로 모든 음 수집 (가중치 포함)
2. 4성부 역할 분배:
   - Cello: 베이스 (가장 낮은 음)
   - Violin I: 멜로디 (가장 높은 음역 + 중요도)
   - Violin II, Viola: 하모니 (나머지 주요 음 2개)
3. MusicXML 출력
"""

from music21 import converter, stream, note, chord, tempo, key, meter
from collections import defaultdict
import json

def classify_role(part):
    """악기 역할 분류"""
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


def get_weighted_notes(score, start_offset, end_offset):
    """
    시간 구간 내 모든 음을 가중치와 함께 수집
    
    가중치 = duration × 강박 × 역할
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
                duration_weight = 0.2  # Passing notes
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
                    'offset': note_start,
                    'role': role
                })
    
    return notes_data


def select_voices(notes_data):
    """
    4성부 배치 결정
    
    Returns:
        {
            'cello': Pitch,
            'viola': Pitch,
            'violin2': Pitch,
            'violin1': Pitch
        }
    """
    if not notes_data:
        return None
    
    # MIDI별 가중치 합산
    midi_weights = defaultdict(float)
    midi_pitches = {}
    
    for note_data in notes_data:
        midi = note_data['midi']
        midi_weights[midi] += note_data['weight']
        if midi not in midi_pitches:
            midi_pitches[midi] = note_data['pitch']
    
    # 1. Cello (베이스): 가장 낮은 음 (단, 가중치 보너스)
    lowest_midi = min(midi_weights.keys())
    midi_weights[lowest_midi] *= 3.0  # 베이스 보너스
    
    # 상위 4개 음 선택
    top_4 = sorted(midi_weights.items(), key=lambda x: x[1], reverse=True)[:4]
    
    if len(top_4) < 4:
        # 4개 미만이면 나머지는 None
        selected_midis = [midi for midi, _ in top_4]
        while len(selected_midis) < 4:
            selected_midis.append(None)
    else:
        selected_midis = [midi for midi, _ in top_4]
    
    # MIDI 번호 순으로 정렬 (낮은 음부터)
    selected_midis_sorted = sorted([m for m in selected_midis if m is not None])
    
    # 4성부 배치 (낮은 것부터)
    voices = {}
    voice_names = ['cello', 'viola', 'violin2', 'violin1']
    
    for i, voice_name in enumerate(voice_names):
        if i < len(selected_midis_sorted):
            voices[voice_name] = midi_pitches[selected_midis_sorted[i]]
        else:
            voices[voice_name] = None
    
    return voices


def arrange_to_quartet(input_file, output_file, segment_length=0.5):
    """
    오케스트라 총보 → String Quartet 편곡
    
    Args:
        input_file: 입력 MusicXML 파일
        output_file: 출력 MusicXML 파일
        segment_length: 시간 단위 (quarter notes)
    """
    print("=" * 70)
    print("🎼 String Quartet 자동 편곡")
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
    
    # 4개 파트 생성 (악기 설정 포함)
    from music21 import instrument
    
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
    for part in [violin1_part, violin2_part, viola_part, cello_part]:
        # Time signature
        ts = score.flat.getElementsByClass('TimeSignature')
        if ts:
            part.append(ts[0])
        
        # Key signature
        ks = score.flat.getElementsByClass('KeySignature')
        if ks:
            part.append(ks[0])
        
        # Tempo
        tempos = score.flat.getElementsByClass('MetronomeMark')
        if tempos:
            part.append(tempos[0])
    
    print("\n[3단계] 4성부 배치 및 편곡...")
    
    for i in range(num_segments):
        segment_start = i * segment_length
        segment_end = segment_start + segment_length
        
        # 음 수집
        notes_data = get_weighted_notes(score, segment_start, segment_end)
        
        # 4성부 선택
        voices = select_voices(notes_data)
        
        if voices:
            # 각 파트에 노트 추가
            for voice_name, pitch in voices.items():
                if pitch is None:
                    n = note.Rest(quarterLength=segment_length)
                else:
                    n = note.Note(pitch.midi, quarterLength=segment_length)
                
                if voice_name == 'violin1':
                    violin1_part.append(n)
                elif voice_name == 'violin2':
                    violin2_part.append(n)
                elif voice_name == 'viola':
                    viola_part.append(n)
                elif voice_name == 'cello':
                    cello_part.append(n)
        
        if (i + 1) % 100 == 0:
            print(f"  진행: {i + 1}/{num_segments} ({100 * (i + 1) / num_segments:.1f}%)")
    
    print(f"✅ {num_segments}개 구간 편곡 완료")
    
    # Score 조립
    quartet_score = stream.Score()
    quartet_score.append(violin1_part)
    quartet_score.append(violin2_part)
    quartet_score.append(viola_part)
    quartet_score.append(cello_part)
    
    print(f"\n[4단계] MusicXML 저장...")
    quartet_score.write('musicxml', fp=output_file)
    print(f"✅ 저장 완료: {output_file}")
    
    return quartet_score


if __name__ == '__main__':
    input_file = '/Users/tsk/.openclaw/workspace/music-project/ode_to_joy_source.mxl'
    output_file = '/Users/tsk/.openclaw/workspace/music-project/ode_to_joy_quartet_v1.musicxml'
    
    print("\n🎻 Ode to Joy 편곡 시작...")
    quartet = arrange_to_quartet(input_file, output_file, segment_length=1.0)
    print("\n🎉 완료! MuseScore에서 확인해보세요.")
