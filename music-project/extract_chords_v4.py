#!/usr/bin/env python3
"""
개선된 코드 진행 추출 V4
- score.toSoundingPitch()로 전체 악보를 concert pitch로 한 번에 변환
- 베이스라인 최소 duration 필터링
- 간단한 코드만 인식
"""

from music21 import converter, stream, note, chord, pitch
from collections import Counter, defaultdict
import json

# 기본 코드 템플릿만
CHORD_TEMPLATES = {
    'major': [0, 4, 7],
    'minor': [0, 3, 7],
    'diminished': [0, 3, 6],
    'augmented': [0, 4, 8],
    'dom7': [0, 4, 7, 10],
    'maj7': [0, 4, 7, 11],
    'min7': [0, 3, 7, 10],
    'sus2': [0, 2, 7],
    'sus4': [0, 5, 7],
}

def classify_instrument_role(part):
    """악기 파트 역할 분류"""
    instrument = part.getInstrument()
    if not instrument:
        return 'inner'
    
    name = instrument.instrumentName.lower()
    
    if any(kw in name for kw in ['bass', 'cello', 'tuba', 'bassoon', 'contrabass']):
        return 'bass'
    elif any(kw in name for kw in ['violin', 'flute', 'soprano', 'oboe']):
        return 'melody'
    else:
        return 'inner'


def extract_bass_changes(score, min_duration=1.0):
    """
    베이스 라인 변화 지점 추출 (최소 길이 필터)
    """
    print(f"\n[베이스라인 분석] (최소 길이: {min_duration}박자)")
    
    bass_parts = [p for p in score.parts if classify_instrument_role(p) == 'bass']
    print(f"  베이스 파트 {len(bass_parts)}개")
    
    bass_timeline = []
    
    for part in bass_parts:
        for element in part.flatten().notesAndRests:
            if element.quarterLength < min_duration:
                continue
            
            if isinstance(element, note.Note):
                bass_timeline.append((element.offset, element.pitch))
            elif isinstance(element, chord.Chord):
                lowest = min(element.pitches, key=lambda p: p.midi)
                bass_timeline.append((element.offset, lowest))
    
    bass_timeline.sort(key=lambda x: x[0])
    
    # 변화 지점
    bass_changes = []
    prev_pc = None
    
    for offset, p in bass_timeline:
        pc = p.pitchClass
        if prev_pc is None or pc != prev_pc:
            bass_changes.append((offset, p))
            prev_pc = pc
    
    print(f"  베이스 변화 {len(bass_changes)}회")
    return bass_changes


def get_active_pitches(score, start, end, role_weights):
    """
    시간 구간의 활성 음들 수집
    """
    pitch_class_weights = defaultdict(float)
    
    for part in score.parts:
        role = classify_instrument_role(part)
        weight = role_weights.get(role, 1.0)
        
        instrument = part.getInstrument()
        if instrument and 'drum' in instrument.instrumentName.lower():
            continue
        
        for element in part.flatten().notesAndRests:
            note_start = element.offset
            note_end = note_start + element.quarterLength
            
            if note_start >= end or note_end <= start:
                continue
            
            if isinstance(element, note.Note):
                pc = element.pitch.pitchClass
                pitch_class_weights[pc] += weight
            elif isinstance(element, chord.Chord):
                for p in element.pitches:
                    pc = p.pitchClass
                    pitch_class_weights[pc] += weight
    
    return dict(pitch_class_weights)


def match_chord(pitch_classes, bass_pitch):
    """
    피치 클래스와 베이스 음으로 코드 추론
    """
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
        
        # 추가 음이 많으면 페널티
        extra = len(intervals - set(template))
        if extra > 1:
            score -= 0.15 * extra
        
        if score > best_score and score >= 0.65:
            best_score = score
            best_match = chord_type
    
    if best_match:
        if best_match == 'major':
            return root_name, best_score
        elif best_match == 'minor':
            return f"{root_name}m", best_score
        elif best_match == 'diminished':
            return f"{root_name}dim", best_score
        elif best_match == 'dom7':
            return f"{root_name}7", best_score
        elif best_match == 'maj7':
            return f"{root_name}maj7", best_score
        elif best_match == 'min7':
            return f"{root_name}m7", best_score
        elif best_match == 'sus2':
            return f"{root_name}sus2", best_score
        elif best_match == 'sus4':
            return f"{root_name}sus4", best_score
        else:
            return f"{root_name}{best_match}", best_score
    
    return None, 0.0


def extract_chord_progression_v4(filepath):
    """
    코드 진행 추출 V4 (toSoundingPitch 사용)
    """
    print("=" * 70)
    print("🎼 코드 진행 추출 V4 (toSoundingPitch)")
    print("=" * 70)
    
    print("\n[1단계] 파일 로딩...")
    score = converter.parse(filepath)
    print(f"✅ {len(score.parts)} 파트 로드")
    
    # ★ 핵심: Concert pitch로 한 번에 변환
    print("\n[2단계] Concert pitch로 변환 중...")
    score = score.toSoundingPitch()
    print("✅ 이동조 악기 변환 완료")
    
    print("\n[3단계] 악기 역할...")
    role_count = {'bass': 0, 'inner': 0, 'melody': 0}
    for part in score.parts:
        role = classify_instrument_role(part)
        role_count[role] += 1
    print(f"  베이스: {role_count['bass']}, 내성: {role_count['inner']}, 멜로디: {role_count['melody']}")
    
    # 베이스 변화 (1박자 이상만)
    bass_changes = extract_bass_changes(score, min_duration=1.0)
    
    print("\n[4단계] 코드 추론...")
    chord_progression = []
    
    for i, (offset, bass_pitch) in enumerate(bass_changes):
        if i < len(bass_changes) - 1:
            next_offset = bass_changes[i + 1][0]
        else:
            next_offset = offset + 4.0
        
        # 음들 수집 (멜로디 가중치 낮춤)
        pitch_class_weights = get_active_pitches(
            score, offset, next_offset,
            role_weights={'bass': 2.0, 'inner': 2.0, 'melody': 0.2}
        )
        
        chord_symbol, confidence = match_chord(
            pitch_class_weights.keys(),
            bass_pitch
        )
        
        if chord_symbol is None:
            continue
        
        measure_num = int(offset / 4.0) + 1
        beat = (offset % 4.0) + 1
        
        chord_progression.append({
            'offset': float(offset),
            'measure': measure_num,
            'beat': float(beat),
            'chord': chord_symbol,
            'bass': bass_pitch.nameWithOctave,
            'confidence': float(confidence),
            'pitch_classes': sorted(pitch_class_weights.keys())
        })
        
        print(f"  마디 {measure_num:2d}, 박 {beat:.0f}: {chord_symbol:8s} (베이스: {bass_pitch.nameWithOctave})")
    
    # 마디별 요약
    print("\n" + "=" * 70)
    print("📊 코드 진행 요약:")
    print("=" * 70)
    
    by_measure = defaultdict(list)
    for item in chord_progression:
        by_measure[item['measure']].append(item)
    
    for measure_num in sorted(by_measure.keys()):
        chords = by_measure[measure_num]
        chord_str = ' - '.join([c['chord'] for c in chords])
        print(f"마디 {measure_num:2d}: {chord_str}")
    
    # JSON 저장
    output_json = filepath.replace('.mxl', '_chords_v4.json')
    with open(output_json, 'w', encoding='utf-8') as f:
        json.dump(chord_progression, f, indent=2, ensure_ascii=False)
    
    print(f"\n✅ JSON 저장: {output_json}")
    
    return chord_progression


if __name__ == '__main__':
    filepath = '/Users/tsk/.openclaw/workspace/music-project/ode_to_joy_source.mxl'
    progression = extract_chord_progression_v4(filepath)
