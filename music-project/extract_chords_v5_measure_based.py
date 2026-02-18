#!/usr/bin/env python3
"""
코드 진행 추출 V5 - 마디 기반
- 마디 단위로 분석
- 강박(첫 박자)의 베이스 음을 근음으로
- Passing notes 무시
"""

from music21 import converter
from collections import Counter, defaultdict
import json

CHORD_TEMPLATES = {
    'major': [0, 4, 7],
    'minor': [0, 3, 7],
    'dom7': [0, 4, 7, 10],
    'min7': [0, 3, 7, 10],
    'diminished': [0, 3, 6],
    'sus4': [0, 5, 7],
}

def classify_role(part):
    """악기 역할 분류"""
    instrument = part.getInstrument()
    if not instrument:
        return 'inner'
    name = instrument.instrumentName.lower()
    if any(kw in name for kw in ['bass', 'cello', 'tuba', 'bassoon', 'contrabass']):
        return 'bass'
    elif any(kw in name for kw in ['violin', 'flute', 'soprano', 'oboe', 'clarinet']):
        return 'melody'
    else:
        return 'inner'


def get_downbeat_bass(measure, bass_parts):
    """
    마디의 첫 박자(downbeat) 베이스 음 추출
    여러 베이스 파트가 있으면 가장 흔한 음
    """
    downbeat_basses = []
    
    for part in bass_parts:
        part_name = part.partName
        
        # 해당 마디 찾기
        measures = part.getElementsByClass('Measure')
        if len(measures) <= measure:
            continue
        
        m = measures[measure]
        
        # 첫 음(또는 코드)
        for element in m.flatten().notesAndRests:
            if element.offset == 0.0:  # 강박
                if hasattr(element, 'pitch'):
                    downbeat_basses.append(element.pitch)
                elif hasattr(element, 'pitches') and len(element.pitches) > 0:
                    lowest = min(element.pitches, key=lambda p: p.midi)
                    downbeat_basses.append(lowest)
                break  # 첫 음만
    
    if not downbeat_basses:
        return None
    
    # 가장 흔한 pitch class
    pc_counter = Counter([p.pitchClass for p in downbeat_basses])
    most_common_pc = pc_counter.most_common(1)[0][0]
    
    # 해당 PC의 첫 번째 pitch 반환
    for p in downbeat_basses:
        if p.pitchClass == most_common_pc:
            return p
    
    return downbeat_basses[0]


def get_measure_pitches(measure_num, score, role_weights):
    """
    마디 전체의 모든 음 수집 (역할별 가중치)
    """
    pitch_class_weights = defaultdict(float)
    
    for part in score.parts:
        role = classify_role(part)
        weight = role_weights.get(role, 1.0)
        
        instrument = part.getInstrument()
        if instrument and 'drum' in instrument.instrumentName.lower():
            continue
        
        measures = part.getElementsByClass('Measure')
        if len(measures) <= measure_num:
            continue
        
        m = measures[measure_num]
        
        for element in m.flatten().notesAndRests:
            if hasattr(element, 'pitch'):
                pc = element.pitch.pitchClass
                pitch_class_weights[pc] += weight * element.quarterLength
            elif hasattr(element, 'pitches'):
                for p in element.pitches:
                    pc = p.pitchClass
                    pitch_class_weights[pc] += weight * element.quarterLength
    
    return dict(pitch_class_weights)


def match_chord(pitch_classes, bass_pitch):
    """코드 매칭"""
    if not pitch_classes:
        return None, 0.0
    
    root_pc = bass_pitch.pitchClass
    root_name = bass_pitch.name
    
    intervals = set()
    for pc in pitch_classes:
        interval = (pc - root_pc) % 12
        intervals.add(interval)
    
    best_match = None
    best_score = 0.0
    
    for chord_type, template in CHORD_TEMPLATES.items():
        matches = len(intervals & set(template))
        score = matches / len(template)
        
        if score > best_score and score >= 0.6:
            best_score = score
            best_match = chord_type
    
    if best_match:
        if best_match == 'major':
            return root_name, best_score
        elif best_match == 'minor':
            return f"{root_name}m", best_score
        elif best_match == 'dom7':
            return f"{root_name}7", best_score
        elif best_match == 'min7':
            return f"{root_name}m7", best_score
        elif best_match == 'diminished':
            return f"{root_name}dim", best_score
        elif best_match == 'sus4':
            return f"{root_name}sus4", best_score
        else:
            return f"{root_name}{best_match}", best_score
    
    return None, 0.0


def extract_chord_progression_v5(filepath):
    """
    마디 기반 코드 추출
    """
    print("=" * 70)
    print("🎼 코드 진행 추출 V5 (마디 기반, 강박 베이스)")
    print("=" * 70)
    
    print("\n[1단계] 파일 로딩 및 Concert Pitch 변환...")
    score = converter.parse(filepath)
    score = score.toSoundingPitch()
    print(f"✅ {len(score.parts)} 파트")
    
    # 베이스 파트 찾기
    bass_parts = [p for p in score.parts if classify_role(p) == 'bass']
    print(f"\n[2단계] 베이스 파트 {len(bass_parts)}개 발견")
    
    # 마디 수
    first_part = score.parts[0]
    measures = first_part.getElementsByClass('Measure')
    num_measures = len(measures)
    print(f"\n[3단계] 총 {num_measures}마디 분석...")
    
    chord_progression = []
    
    for measure_num in range(num_measures):
        # 강박의 베이스 음
        bass_pitch = get_downbeat_bass(measure_num, bass_parts)
        
        if bass_pitch is None:
            continue
        
        # 마디 전체의 음들 (멜로디 가중치 낮춤)
        pitch_class_weights = get_measure_pitches(
            measure_num, score,
            role_weights={'bass': 2.0, 'inner': 2.0, 'melody': 0.2}
        )
        
        # 코드 매칭
        chord_symbol, confidence = match_chord(
            pitch_class_weights.keys(),
            bass_pitch
        )
        
        if chord_symbol is None:
            continue
        
        chord_progression.append({
            'measure': measure_num + 1,
            'chord': chord_symbol,
            'bass': bass_pitch.nameWithOctave,
            'confidence': float(confidence),
            'pitch_classes': sorted(pitch_class_weights.keys())
        })
        
        print(f"  마디 {measure_num + 1:2d}: {chord_symbol:8s} (베이스: {bass_pitch.nameWithOctave})")
    
    # 결과
    print("\n" + "=" * 70)
    print("📊 코드 진행 요약:")
    print("=" * 70)
    
    for item in chord_progression:
        print(f"마디 {item['measure']:2d}: {item['chord']}")
    
    # JSON 저장
    output_json = filepath.replace('.mxl', '_chords_v5.json')
    with open(output_json, 'w', encoding='utf-8') as f:
        json.dump(chord_progression, f, indent=2, ensure_ascii=False)
    
    print(f"\n✅ JSON 저장: {output_json}")
    
    return chord_progression


if __name__ == '__main__':
    filepath = '/Users/tsk/.openclaw/workspace/music-project/ode_to_joy_source.mxl'
    progression = extract_chord_progression_v5(filepath)
