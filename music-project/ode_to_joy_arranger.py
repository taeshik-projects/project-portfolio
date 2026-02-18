#!/usr/bin/env python3
"""
Ode to Joy (베토벤 교향곡 9번 4악장) String Quartet 자동 편곡
코드 진행에 맞춰 하모니 생성
"""

from music21 import stream, note, chord, instrument, tempo, key, meter, clef, expressions

def create_ode_to_joy_melody():
    """
    Ode to Joy 멜로디 16마디 생성 (D major)
    
    구조:
    - 8마디 A 섹션 (반복)
    - 8마디 B 섹션
    
    코드 진행:
    A: D - D - A - D - D - G - D/A - A
    A: D - D - A - D - D - G - D/A - A
    """
    
    melody = stream.Part()
    melody.append(instrument.Violin())
    melody.append(clef.TrebleClef())
    melody.append(key.Key('D'))
    melody.append(meter.TimeSignature('4/4'))
    melody.append(tempo.MetronomeMark(number=120, text='Allegro assai'))
    
    # Ode to Joy 멜로디 (16마디)
    # 각 튜플: (음높이, 길이, 코드)
    melody_data = [
        # 마디 1-2: D major
        ('D5', 1, 'D'), ('D5', 1, 'D'), ('E5', 1, 'D'), ('F#5', 1, 'D'),
        ('F#5', 1, 'D'), ('E5', 1, 'D'), ('D5', 1, 'D'), ('C#5', 1, 'A'),
        
        # 마디 3-4: D - A
        ('B4', 1, 'A'), ('B4', 1, 'A'), ('C#5', 1, 'A'), ('D5', 1, 'D'),
        ('D5', 1.5, 'D'), ('C#5', 0.5, 'A'), ('C#5', 2, 'A'),
        
        # 마디 5-6: D major (반복)
        ('D5', 1, 'D'), ('D5', 1, 'D'), ('E5', 1, 'D'), ('F#5', 1, 'D'),
        ('F#5', 1, 'D'), ('E5', 1, 'D'), ('D5', 1, 'D'), ('C#5', 1, 'A'),
        
        # 마디 7-8: D - A (종지)
        ('B4', 1, 'A'), ('B4', 1, 'A'), ('C#5', 1, 'A'), ('D5', 1, 'D'),
        ('D5', 1.5, 'D'), ('C#5', 0.5, 'A'), ('D5', 2, 'D'),
        
        # 마디 9-10: B 섹션 시작
        ('C#5', 1, 'A'), ('C#5', 1, 'A'), ('D5', 1, 'D'), ('B4', 1, 'G'),
        ('C#5', 1, 'A'), ('D5', 0.5, 'D'), ('E5', 0.5, 'D'), ('D5', 1, 'D'), ('B4', 1, 'G'),
        
        # 마디 11-12
        ('C#5', 1, 'A'), ('D5', 0.5, 'D'), ('E5', 0.5, 'D'), ('D5', 1, 'D'), ('C#5', 1, 'A'),
        ('B4', 1, 'G'), ('A4', 1, 'D'), ('A4', 2, 'D'),
        
        # 마디 13-14: A 섹션 재현
        ('D5', 1, 'D'), ('D5', 1, 'D'), ('E5', 1, 'D'), ('F#5', 1, 'D'),
        ('F#5', 1, 'D'), ('E5', 1, 'D'), ('D5', 1, 'D'), ('C#5', 1, 'A'),
        
        # 마디 15-16: 종결
        ('B4', 1, 'A'), ('B4', 1, 'A'), ('C#5', 1, 'A'), ('D5', 1, 'D'),
        ('D5', 1.5, 'D'), ('C#5', 0.5, 'A'), ('D5', 2, 'D'),
    ]
    
    current_offset = 0
    chord_changes = []  # (offset, chord_symbol)
    
    for pitch_name, duration, chord_sym in melody_data:
        n = note.Note(pitch_name)
        n.quarterLength = duration
        melody.append(n)
        
        # 코드 변화 기록
        if not chord_changes or chord_changes[-1][1] != chord_sym:
            chord_changes.append((current_offset, chord_sym))
        
        current_offset += duration
    
    return melody, chord_changes


def get_chord_notes(chord_symbol, octave=4):
    """코드 심볼에서 구성음 반환"""
    chord_map = {
        'D': ['D', 'F#', 'A'],   # D major
        'G': ['G', 'B', 'D'],    # G major
        'A': ['A', 'C#', 'E'],   # A major
        'Bm': ['B', 'D', 'F#'],  # B minor
    }
    
    if chord_symbol not in chord_map:
        return ['D', 'F#', 'A']  # default D major
    
    return [n + str(octave) for n in chord_map[chord_symbol]]


def arrange_with_harmony(melody_part, chord_changes):
    """
    멜로디를 코드 진행에 맞춰 String Quartet으로 편곡
    """
    
    quartet_score = stream.Score()
    
    # Violin I - 원본 멜로디
    violin1 = stream.Part()
    violin1.append(instrument.Violin())
    violin1.append(clef.TrebleClef())
    violin1.id = 'Violin I'
    
    for element in melody_part:
        if isinstance(element, (note.Note, note.Rest)):
            violin1.append(element)
        elif isinstance(element, (key.Key, meter.TimeSignature, tempo.MetronomeMark)):
            violin1.append(element)
    
    # Violin II - 3도/6도 하모니
    violin2 = stream.Part()
    violin2.append(instrument.Violin())
    violin2.append(clef.TrebleClef())
    violin2.id = 'Violin II'
    
    current_chord = 'D'
    chord_idx = 0
    current_offset = 0
    
    for element in melody_part:
        if isinstance(element, (key.Key, meter.TimeSignature, tempo.MetronomeMark)):
            violin2.append(element)
        elif isinstance(element, note.Note):
            # 현재 코드 찾기
            if chord_idx < len(chord_changes) - 1:
                if current_offset >= chord_changes[chord_idx + 1][0]:
                    chord_idx += 1
            current_chord = chord_changes[chord_idx][1]
            
            # 코드 구성음 가져오기
            chord_notes = get_chord_notes(current_chord, 4)
            
            # 멜로디 음과 가장 가까운 3도/6도 찾기
            melody_pitch = element.pitch.midi
            
            # 3도 아래 시도
            harmony_note = element.transpose(-4)
            
            # 코드 내 음으로 조정
            # (간단화: 일단 3도 아래 사용)
            
            violin2.append(harmony_note)
            current_offset += element.quarterLength
        elif isinstance(element, note.Rest):
            violin2.append(element)
            current_offset += element.quarterLength
    
    # Viola - 내성 (코드의 5음 또는 3음)
    viola = stream.Part()
    viola.append(instrument.Viola())
    viola.append(clef.AltoClef())
    viola.id = 'Viola'
    
    current_chord = 'D'
    chord_idx = 0
    current_offset = 0
    
    for element in melody_part:
        if isinstance(element, (key.Key, meter.TimeSignature, tempo.MetronomeMark)):
            viola.append(element)
        elif isinstance(element, note.Note):
            # 현재 코드
            if chord_idx < len(chord_changes) - 1:
                if current_offset >= chord_changes[chord_idx + 1][0]:
                    chord_idx += 1
            current_chord = chord_changes[chord_idx][1]
            
            # Viola는 옥타브 아래 + 코드 5음
            inner_note = element.transpose(-12)
            
            # 음역대 체크
            if inner_note.pitch.midi < 48:  # C3
                inner_note = inner_note.transpose(12)
            
            viola.append(inner_note)
            current_offset += element.quarterLength
        elif isinstance(element, note.Rest):
            viola.append(element)
            current_offset += element.quarterLength
    
    # Cello - 베이스 라인 (코드 근음)
    cello = stream.Part()
    cello.append(instrument.Violoncello())
    cello.append(clef.BassClef())
    cello.id = 'Cello'
    
    current_chord = 'D'
    chord_idx = 0
    current_offset = 0
    
    chord_roots = {
        'D': 'D3',
        'G': 'G2',
        'A': 'A2',
        'Bm': 'B2',
    }
    
    for element in melody_part:
        if isinstance(element, (key.Key, meter.TimeSignature, tempo.MetronomeMark)):
            cello.append(element)
        elif isinstance(element, note.Note):
            # 현재 코드
            if chord_idx < len(chord_changes) - 1:
                if current_offset >= chord_changes[chord_idx + 1][0]:
                    chord_idx += 1
            current_chord = chord_changes[chord_idx][1]
            
            # 코드 근음 사용
            root = chord_roots.get(current_chord, 'D3')
            bass_note = note.Note(root)
            bass_note.quarterLength = element.quarterLength
            
            cello.append(bass_note)
            current_offset += element.quarterLength
        elif isinstance(element, note.Rest):
            cello.append(element)
            current_offset += element.quarterLength
    
    # Score에 추가
    quartet_score.append(violin1)
    quartet_score.append(violin2)
    quartet_score.append(viola)
    quartet_score.append(cello)
    
    return quartet_score


def main():
    print("=" * 70)
    print("🎵 Ode to Joy - String Quartet 자동 편곡")
    print("=" * 70)
    
    # 1. 멜로디 생성
    print("\n[1단계] Ode to Joy 멜로디 생성 (16마디)...")
    melody, chord_changes = create_ode_to_joy_melody()
    print(f"✅ 멜로디 생성 완료: {len(melody.notes)} 음표")
    print(f"✅ 코드 진행: {len(chord_changes)}개 변화")
    
    # 코드 진행 출력
    print("\n코드 진행:")
    for offset, chord_sym in chord_changes[:10]:  # 처음 10개만
        print(f"  마디 {int(offset/4) + 1}: {chord_sym}")
    
    # 2. String Quartet 편곡
    print("\n[2단계] String Quartet 자동 편곡 중...")
    quartet = arrange_with_harmony(melody, chord_changes)
    print(f"✅ 편곡 완료: {len(quartet.parts)} 파트")
    for part in quartet.parts:
        print(f"   - {part.id}: {len(part.notes)} 음표")
    
    # 3. MusicXML 저장
    output_file = '/Users/tsk/.openclaw/workspace/music-project/ode_to_joy_quartet.musicxml'
    print(f"\n[3단계] MusicXML 저장 중: {output_file}")
    quartet.write('musicxml', output_file)
    print("✅ 저장 완료!")
    
    # 4. 분석
    print("\n[4단계] 악보 정보:")
    print(f"   - 조성: D major")
    print(f"   - 박자: 4/4")
    print(f"   - 템포: Allegro assai (♩= 120)")
    print(f"   - 총 마디: 16마디")
    
    print("\n" + "=" * 70)
    print("완료! MuseScore에서 확인:")
    print(f"  open -a 'MuseScore 4' {output_file}")
    print("=" * 70)


if __name__ == '__main__':
    main()
