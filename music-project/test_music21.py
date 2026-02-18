#!/usr/bin/env python3
"""
music21 설치 테스트 및 간단한 String Quartet 자동 편곡 데모
"""

from music21 import stream, note, chord, instrument, tempo, key, meter, clef

def create_simple_melody():
    """간단한 테스트 멜로디 생성 (C major, 8마디)"""
    melody = stream.Part()
    melody.append(instrument.Violin())
    melody.append(clef.TrebleClef())
    melody.append(key.Key('C'))
    melody.append(meter.TimeSignature('4/4'))
    melody.append(tempo.MetronomeMark(number=80))
    
    # "Can't Help Falling in Love" 스타일의 간단한 멜로디
    notes_data = [
        ('C5', 1.0), ('D5', 1.0), ('E5', 1.0), ('G5', 1.0),
        ('A5', 2.0), ('G5', 2.0),
        ('E5', 1.0), ('D5', 1.0), ('C5', 2.0),
        ('D5', 1.0), ('E5', 1.0), ('D5', 2.0)
    ]
    
    for pitch, duration in notes_data:
        n = note.Note(pitch)
        n.quarterLength = duration
        melody.append(n)
    
    return melody


def arrange_to_string_quartet(melody_part):
    """
    멜로디를 String Quartet으로 자동 편곡
    
    전략:
    - Violin I: 원본 멜로디
    - Violin II: 3도 또는 6도 하모니
    - Viola: 옥타브 아래 하모니
    - Cello: 베이스 라인 (근음 중심)
    """
    
    # Score 생성
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
    
    # Violin II - 3도 아래 하모니
    violin2 = stream.Part()
    violin2.append(instrument.Violin())
    violin2.append(clef.TrebleClef())
    violin2.id = 'Violin II'
    for element in melody_part:
        if isinstance(element, note.Note):
            # 3도 아래로 transpose
            harmony_note = element.transpose(-4)  # 장3도
            violin2.append(harmony_note)
        elif isinstance(element, note.Rest):
            violin2.append(element)
        elif isinstance(element, (key.Key, meter.TimeSignature, tempo.MetronomeMark)):
            violin2.append(element)
    
    # Viola - 옥타브 아래 하모니
    viola = stream.Part()
    viola.append(instrument.Viola())
    viola.append(clef.AltoClef())
    viola.id = 'Viola'
    for element in melody_part:
        if isinstance(element, note.Note):
            # 옥타브 아래, 약간의 리듬 변화
            lower_note = element.transpose(-12)
            # 음역대 체크 (Viola: C3-E6)
            if lower_note.pitch.midi < 48:  # C3
                lower_note = lower_note.transpose(12)
            viola.append(lower_note)
        elif isinstance(element, note.Rest):
            viola.append(element)
        elif isinstance(element, (key.Key, meter.TimeSignature, tempo.MetronomeMark)):
            viola.append(element)
    
    # Cello - 베이스 라인 (근음 중심)
    cello = stream.Part()
    cello.append(instrument.Violoncello())
    cello.append(clef.BassClef())
    cello.id = 'Cello'
    
    current_key = key.Key('C')
    for element in melody_part:
        if isinstance(element, key.Key):
            current_key = element
            cello.append(element)
        elif isinstance(element, (meter.TimeSignature, tempo.MetronomeMark)):
            cello.append(element)
        elif isinstance(element, note.Note):
            # 현재 조의 으뜸음 (tonic) 사용
            tonic = current_key.tonic
            bass_note = note.Note(tonic.name + '3')  # C3 등
            bass_note.quarterLength = element.quarterLength
            
            # 음역대 체크 (Cello: C2-C5)
            if bass_note.pitch.midi < 36:  # C2
                bass_note = bass_note.transpose(12)
            if bass_note.pitch.midi > 72:  # C5
                bass_note = bass_note.transpose(-12)
            
            cello.append(bass_note)
        elif isinstance(element, note.Rest):
            cello.append(element)
    
    # Score에 파트 추가
    quartet_score.append(violin1)
    quartet_score.append(violin2)
    quartet_score.append(viola)
    quartet_score.append(cello)
    
    return quartet_score


def main():
    print("=" * 60)
    print("music21 자동 편곡 테스트")
    print("=" * 60)
    
    # 1. 간단한 멜로디 생성
    print("\n[1단계] 테스트 멜로디 생성 중...")
    melody = create_simple_melody()
    print(f"✅ 멜로디 생성 완료: {len(melody.notes)} 음표")
    
    # 2. String Quartet으로 편곡
    print("\n[2단계] String Quartet 자동 편곡 중...")
    quartet = arrange_to_string_quartet(melody)
    print(f"✅ 편곡 완료: {len(quartet.parts)} 파트")
    for part in quartet.parts:
        print(f"   - {part.id}: {len(part.notes)} 음표")
    
    # 3. MusicXML 출력 (MuseScore에서 열 수 있음)
    output_file = '/Users/tsk/.openclaw/workspace/music-project/test_quartet.musicxml'
    print(f"\n[3단계] MusicXML 파일 저장 중: {output_file}")
    quartet.write('musicxml', output_file)
    print("✅ 저장 완료!")
    
    # 4. 기본 분석
    print("\n[4단계] 악보 분석:")
    print(f"   - 조성: {quartet.analyze('key')}")
    print(f"   - 박자: {quartet.parts[0].getElementsByClass(meter.TimeSignature)[0]}")
    print(f"   - 템포: {quartet.parts[0].getElementsByClass(tempo.MetronomeMark)[0]}")
    
    print("\n" + "=" * 60)
    print("완료! MuseScore에서 열어보세요:")
    print(f"  open -a 'MuseScore 4' {output_file}")
    print("=" * 60)


if __name__ == '__main__':
    main()
