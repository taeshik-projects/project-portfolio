#!/usr/bin/env python3
"""
오케스트라 총보에서 코드 진행 추출
모든 파트의 음들을 분석하여 각 마디/박자의 코드를 자동 추론
"""

from music21 import converter, chord, pitch, stream, note
from collections import Counter
import json

def extract_chord_progression(filepath, output_json=None):
    """
    MusicXML 파일에서 코드 진행 추출
    
    전략:
    1. 각 마디를 작은 시간 단위로 나눔 (예: 반박자 또는 1박자)
    2. 각 시간 단위에 울리는 모든 음 수집
    3. 그 음들로부터 가장 적합한 코드 추론
    """
    
    print("=" * 70)
    print(f"🎼 코드 진행 추출: {filepath}")
    print("=" * 70)
    
    # 1. 파일 로드
    print("\n[1단계] 파일 로딩 중...")
    score = converter.parse(filepath)
    print(f"✅ 로드 완료: {len(score.parts)} 파트")
    
    # 2. 타악기 파트 제외 (Unpitched 때문에 chordify 에러)
    print("\n[2단계] 타악기 제외하고 파트 필터링 중...")
    
    # 타악기 제외할 악기 목록
    exclude_instruments = ['Acoustic Bass Drum', 'Crash Cymbal', 'Timpani', 'drum', 'cymbal', 'percussion']
    
    filtered_score = stream.Score()
    for part in score.parts:
        instrument_name = part.getInstrument().instrumentName if part.getInstrument() else ""
        
        # 타악기가 아닌 경우만 추가
        if not any(excl.lower() in instrument_name.lower() for excl in exclude_instruments):
            filtered_score.append(part)
    
    print(f"✅ 필터링 완료: {len(filtered_score.parts)} 파트 (타악기 제외)")
    
    # 3. 모든 파트를 하나의 타임라인으로 합치기
    print("\n[3단계] 모든 파트 합치는 중...")
    # 중요: chordify()는 모든 파트를 수직적으로 분석해서 코드로 만들어줌
    chordified = filtered_score.chordify()
    print(f"✅ Chordify 완료")
    
    # 4. 마디별 코드 분석
    print("\n[4단계] 마디별 코드 추출 중...")
    measures = chordified.getElementsByClass('Measure')
    
    chord_progression = []
    
    for i, measure in enumerate(measures):
        measure_num = i + 1
        print(f"\n   === 마디 {measure_num} ===")
        
        # 마디 내의 모든 chord/note 추출
        elements = measure.flatten().notesAndRests
        
        measure_chords = []
        
        for element in elements:
            if isinstance(element, chord.Chord):
                # 코드 분석
                offset = element.offset
                pitches = [p.nameWithOctave for p in element.pitches]
                
                # music21의 코드 인식 시도
                chord_name = None
                try:
                    # 코드 분석
                    root = element.root()
                    chord_type = element.commonName
                    
                    # 단순화: 메이저/마이너/sus 등
                    if 'minor' in chord_type.lower():
                        chord_name = f"{root.name}m"
                    elif 'major' in chord_type.lower() or chord_type == '':
                        chord_name = f"{root.name}"
                    else:
                        chord_name = f"{root.name}{chord_type}"
                    
                except:
                    # 코드 인식 실패 시 음들만 표시
                    pitch_classes = sorted(set([p.name for p in element.pitches]))
                    chord_name = f"[{','.join(pitch_classes)}]"
                
                measure_chords.append({
                    'offset': float(offset),
                    'chord': chord_name,
                    'pitches': pitches,
                    'duration': float(element.quarterLength)
                })
                
                print(f"      박자 {offset}: {chord_name} ({len(pitches)} 음)")
            
            elif isinstance(element, note.Note):
                # 단일 음표 (드물지만 있을 수 있음)
                offset = element.offset
                measure_chords.append({
                    'offset': float(offset),
                    'chord': element.pitch.nameWithOctave,
                    'pitches': [element.pitch.nameWithOctave],
                    'duration': float(element.quarterLength)
                })
        
        # 마디의 주요 코드 결정 (가장 긴 duration)
        if measure_chords:
            # duration으로 정렬하여 가장 긴 코드 찾기
            main_chord = max(measure_chords, key=lambda x: x['duration'])
            
            chord_progression.append({
                'measure': measure_num,
                'main_chord': main_chord['chord'],
                'all_chords': measure_chords
            })
    
    # 5. 결과 출력
    print("\n" + "=" * 70)
    print("📊 코드 진행 요약:")
    print("=" * 70)
    for item in chord_progression:
        measure_num = item['measure']
        main_chord = item['main_chord']
        print(f"마디 {measure_num:2d}: {main_chord}")
    
    # 6. JSON 저장
    if output_json:
        with open(output_json, 'w', encoding='utf-8') as f:
            json.dump(chord_progression, f, indent=2, ensure_ascii=False)
        print(f"\n✅ JSON 저장 완료: {output_json}")
    
    return chord_progression


def analyze_chord_progression_simple(filepath):
    """
    간단한 방법: music21의 자동 화성 분석 사용
    """
    print("=" * 70)
    print("🎹 간단한 코드 분석 (Alternative Method)")
    print("=" * 70)
    
    score = converter.parse(filepath)
    chordified = score.chordify()
    
    print("\n마디별 코드 (간소화):")
    
    measures = chordified.getElementsByClass('Measure')
    for i, measure in enumerate(measures):
        measure_num = i + 1
        
        # 마디 내 모든 코드/음표
        all_chords = []
        for element in measure.flatten().notesAndRests:
            if isinstance(element, chord.Chord):
                try:
                    # 코드 심볼로 변환
                    cs = element.closedPosition()
                    root = cs.root()
                    quality = cs.quality
                    
                    if quality == 'major':
                        chord_symbol = root.name
                    elif quality == 'minor':
                        chord_symbol = f"{root.name}m"
                    else:
                        chord_symbol = f"{root.name}({quality})"
                    
                    all_chords.append({
                        'symbol': chord_symbol,
                        'duration': element.quarterLength
                    })
                except:
                    pass
        
        # 가장 긴 코드 선택
        if all_chords:
            main = max(all_chords, key=lambda x: x['duration'])
            print(f"   마디 {measure_num:2d}: {main['symbol']}")
        else:
            print(f"   마디 {measure_num:2d}: (휴식 또는 분석 실패)")


if __name__ == '__main__':
    filepath = '/Users/tsk/.openclaw/workspace/music-project/ode_to_joy_source.mxl'
    output_json = '/Users/tsk/.openclaw/workspace/music-project/ode_to_joy_chords.json'
    
    # 방법 1: 상세 분석
    print("\n")
    progression = extract_chord_progression(filepath, output_json)
    
    print("\n\n")
    
    # 방법 2: 간단한 분석
    analyze_chord_progression_simple(filepath)
