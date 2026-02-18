#!/usr/bin/env python3
"""
실용적인 코드 진행 추출
베이스 라인 + 전체 음들 분석으로 간단한 코드 (D, Em, A 등) 추론
"""

from music21 import converter, stream, note, chord, pitch
from collections import Counter
import json

# 메이저/마이너 코드 패턴
CHORD_PATTERNS = {
    # Major chords (근음, 장3도, 완전5도)
    'major': [0, 4, 7],
    # Minor chords (근음, 단3도, 완전5도)
    'minor': [0, 3, 7],
    # Suspended 2
    'sus2': [0, 2, 7],
    # Suspended 4
    'sus4': [0, 5, 7],
    # Dominant 7th
    'dom7': [0, 4, 7, 10],
    # Major 7th
    'maj7': [0, 4, 7, 11],
    # Minor 7th
    'min7': [0, 3, 7, 10],
}

def get_pitch_class_set(pitches):
    """음높이 리스트 → pitch class set (0-11)"""
    return set([p.pitchClass for p in pitches])

def identify_chord_from_pitch_classes(pitch_classes, bass_note=None):
    """
    Pitch class set에서 가장 적합한 코드 추론
    
    Args:
        pitch_classes: set of integers (0-11)
        bass_note: pitch.Pitch 객체 (베이스 음)
    
    Returns:
        코드 심볼 (예: "D", "Em", "A")
    """
    
    if not pitch_classes:
        return None
    
    # Pitch class를 note name으로 변환
    pitch_names = {pc: pitch.Pitch(pc).name for pc in pitch_classes}
    
    # 베이스 음이 있으면 그걸 근음으로 시작
    if bass_note:
        root_pc = bass_note.pitchClass
        root_name = bass_note.name
    else:
        # 가장 낮은 pitch class를 근음으로 가정
        root_pc = min(pitch_classes)
        root_name = pitch.Pitch(root_pc).name
    
    # 근음 기준으로 상대 간격 계산
    intervals = sorted([(pc - root_pc) % 12 for pc in pitch_classes])
    
    # 패턴 매칭
    best_match = None
    best_score = 0
    
    for chord_type, pattern in CHORD_PATTERNS.items():
        # 패턴과 매칭되는 음 개수
        matches = sum([1 for interval in pattern if interval in intervals])
        score = matches / len(pattern)
        
        if score > best_score:
            best_score = score
            best_match = chord_type
    
    # 코드 심볼 생성
    if best_match == 'major':
        return root_name
    elif best_match == 'minor':
        return f"{root_name}m"
    elif best_match == 'sus2':
        return f"{root_name}sus2"
    elif best_match == 'sus4':
        return f"{root_name}sus4"
    elif best_match == 'dom7':
        return f"{root_name}7"
    elif best_match == 'maj7':
        return f"{root_name}maj7"
    elif best_match == 'min7':
        return f"{root_name}m7"
    else:
        # 매칭 실패 시 pitch names만 표시
        return f"[{','.join(sorted(pitch_names.values()))}]"


def extract_bass_line(score):
    """베이스 라인 파트 추출 (Cello, Contrabass, Tuba 등)"""
    bass_parts = []
    
    for part in score.parts:
        instrument = part.getInstrument()
        if instrument:
            name = instrument.instrumentName.lower()
            if any(keyword in name for keyword in ['cello', 'bass', 'tuba', 'contrabass']):
                bass_parts.append(part)
    
    return bass_parts


def analyze_measure_simple(score, measure_num):
    """
    특정 마디의 코드 간단히 분석
    
    전략:
    1. 베이스 라인 (Cello/Contrabass)에서 근음 찾기
    2. 모든 파트에서 울리는 음들 수집
    3. 가장 많이 나타나는 pitch class로 코드 추론
    """
    
    # 베이스 파트 찾기
    bass_parts = extract_bass_line(score)
    
    # 모든 파트의 해당 마디 가져오기
    all_pitches = []
    bass_pitches = []
    
    for part in score.parts:
        measures = part.getElementsByClass('Measure')
        if measure_num <= len(measures):
            measure = measures[measure_num - 1]
            
            # 마디 내 모든 음표 수집
            for element in measure.flatten().notesAndRests:
                if isinstance(element, note.Note):
                    all_pitches.append(element.pitch)
                    
                    # 베이스 파트인지 확인
                    if part in bass_parts:
                        bass_pitches.append(element.pitch)
                        
                elif isinstance(element, chord.Chord):
                    all_pitches.extend(element.pitches)
                    
                    if part in bass_parts:
                        # 코드의 가장 낮은 음을 베이스로
                        bass_pitches.append(min(element.pitches, key=lambda p: p.midi))
    
    # Pitch class 추출
    pitch_classes = get_pitch_class_set(all_pitches)
    
    # 베이스 음 (가장 많이 나타나는 베이스 음)
    bass_note = None
    if bass_pitches:
        # 가장 흔한 베이스 음
        bass_counter = Counter([p.nameWithOctave for p in bass_pitches])
        most_common_bass_name = bass_counter.most_common(1)[0][0]
        bass_note = pitch.Pitch(most_common_bass_name)
    
    # 코드 추론
    chord_symbol = identify_chord_from_pitch_classes(pitch_classes, bass_note)
    
    return {
        'measure': measure_num,
        'chord': chord_symbol,
        'bass_note': bass_note.nameWithOctave if bass_note else None,
        'pitch_classes': sorted(pitch_classes),
        'all_pitches_count': len(all_pitches)
    }


def extract_all_chords(filepath):
    """전체 악보의 모든 마디 코드 추출"""
    
    print("=" * 70)
    print(f"🎼 실용적 코드 진행 추출")
    print("=" * 70)
    
    # 1. 파일 로드
    print("\n[1단계] 파일 로딩...")
    score = converter.parse(filepath)
    print(f"✅ {len(score.parts)} 파트 로드 완료")
    
    # 2. 베이스 파트 확인
    print("\n[2단계] 베이스 라인 파트 확인...")
    bass_parts = extract_bass_line(score)
    for bp in bass_parts:
        print(f"   - {bp.partName}: {bp.getInstrument().instrumentName}")
    
    # 3. 마디 수 확인
    first_part = score.parts[0]
    measures = first_part.getElementsByClass('Measure')
    total_measures = len(measures)
    print(f"\n[3단계] 총 {total_measures} 마디 분석 시작...")
    
    # 4. 각 마디 분석
    chord_progression = []
    
    for i in range(1, total_measures + 1):
        result = analyze_measure_simple(score, i)
        chord_progression.append(result)
        
        print(f"   마디 {i:2d}: {result['chord']:15s} (베이스: {result['bass_note']})")
    
    # 5. 결과 요약
    print("\n" + "=" * 70)
    print("📊 코드 진행 요약:")
    print("=" * 70)
    
    for item in chord_progression:
        print(f"마디 {item['measure']:2d}: {item['chord']}")
    
    # 6. JSON 저장
    output_json = filepath.replace('.mxl', '_chords_practical.json')
    with open(output_json, 'w', encoding='utf-8') as f:
        json.dump(chord_progression, f, indent=2, ensure_ascii=False)
    
    print(f"\n✅ JSON 저장 완료: {output_json}")
    
    return chord_progression


if __name__ == '__main__':
    filepath = '/Users/tsk/.openclaw/workspace/music-project/ode_to_joy_source.mxl'
    progression = extract_all_chords(filepath)
