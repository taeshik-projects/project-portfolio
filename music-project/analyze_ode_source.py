#!/usr/bin/env python3
"""
MuseScore.com에서 받은 Ode to Joy MusicXML 파일 분석
"""

from music21 import converter, stream, note, chord

def analyze_musicxml(filepath):
    print("=" * 70)
    print(f"🎵 MusicXML 파일 분석: {filepath}")
    print("=" * 70)
    
    # 1. 파일 로드
    print("\n[1단계] 파일 로딩 중...")
    try:
        score = converter.parse(filepath)
        print("✅ 파일 로드 성공!")
    except Exception as e:
        print(f"❌ 오류: {e}")
        return
    
    # 2. 기본 정보
    print("\n[2단계] 기본 정보:")
    print(f"   - 제목: {score.metadata.title if score.metadata and score.metadata.title else 'N/A'}")
    print(f"   - 작곡가: {score.metadata.composer if score.metadata and score.metadata.composer else 'N/A'}")
    print(f"   - 총 파트 수: {len(score.parts)}")
    
    # 3. 각 파트 분석
    print("\n[3단계] 파트 정보:")
    for i, part in enumerate(score.parts):
        part_name = part.partName if part.partName else f"Part {i+1}"
        instrument_name = part.getInstrument().instrumentName if part.getInstrument() else "Unknown"
        
        # 마디 수 계산
        measures = part.getElementsByClass('Measure')
        measure_count = len(measures)
        
        # 음표 수 계산
        notes_count = len(part.flatten().notes)
        
        print(f"\n   파트 {i+1}: {part_name}")
        print(f"      - 악기: {instrument_name}")
        print(f"      - 마디 수: {measure_count}")
        print(f"      - 음표 수: {notes_count}")
        
        # 조성/박자 정보
        key_sig = part.flatten().getElementsByClass('KeySignature')
        if key_sig:
            print(f"      - 조성: {key_sig[0]}")
        
        time_sig = part.flatten().getElementsByClass('TimeSignature')
        if time_sig:
            print(f"      - 박자: {time_sig[0]}")
    
    # 4. 첫 번째 파트의 처음 16마디 멜로디 추출
    if len(score.parts) > 0:
        print("\n[4단계] 첫 번째 파트의 처음 16마디 멜로디:")
        first_part = score.parts[0]
        measures = first_part.getElementsByClass('Measure')
        
        print("\n   마디별 음표:")
        for i, measure in enumerate(measures[:16]):  # 처음 16마디만
            notes_in_measure = []
            for element in measure.flatten().notesAndRests:
                if isinstance(element, note.Note):
                    notes_in_measure.append(f"{element.pitch.nameWithOctave}")
                elif isinstance(element, chord.Chord):
                    chord_notes = [p.nameWithOctave for p in element.pitches]
                    notes_in_measure.append(f"[{','.join(chord_notes)}]")
                elif isinstance(element, note.Rest):
                    notes_in_measure.append("Rest")
            
            print(f"   마디 {i+1}: {' '.join(notes_in_measure)}")
    
    # 5. MusicXML 구조 요약
    print("\n[5단계] 구조 분석:")
    print(f"   - Score type: {type(score).__name__}")
    print(f"   - Flattened notes: {len(score.flatten().notes)}")
    
    # 6. 저장 (확인용)
    print("\n[6단계] 정보 저장:")
    output_file = filepath.replace('.mxl', '_info.txt')
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(f"Title: {score.metadata.title if score.metadata else 'N/A'}\n")
        f.write(f"Parts: {len(score.parts)}\n")
        for i, part in enumerate(score.parts):
            f.write(f"\nPart {i+1}: {part.partName if part.partName else 'Unnamed'}\n")
            measures = part.getElementsByClass('Measure')
            f.write(f"  Measures: {len(measures)}\n")
            f.write(f"  Notes: {len(part.flatten().notes)}\n")
    
    print(f"✅ 정보 저장 완료: {output_file}")
    
    print("\n" + "=" * 70)
    print("분석 완료!")
    print("=" * 70)
    
    return score


if __name__ == '__main__':
    filepath = '/Users/tsk/.openclaw/workspace/music-project/ode_to_joy_source.mxl'
    analyze_musicxml(filepath)
