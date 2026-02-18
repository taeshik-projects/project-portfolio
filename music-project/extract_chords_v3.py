#!/usr/bin/env python3
"""
개선된 코드 진행 추출 V3
- 이동조 악기를 실제 울리는 음(concert pitch)으로 변환
- 베이스라인 최소 duration 필터링
"""

from music21 import converter, stream, note, chord, pitch, interval
from collections import Counter, defaultdict
import json

# 악기별 음역대 분류 기준 (MIDI 번호)
BASS_RANGE = (0, 55)      # ~G3: Cello, Bass, Tuba, Bassoon
INNER_RANGE = (48, 72)    # C3~C5: Viola, Horn, Trombone
MELODY_RANGE = (60, 108)  # C4~: Violin, Flute, Soprano

# 기본 코드 템플릿만 사용 (클래식 스타일)
CHORD_TEMPLATES = {
    # 기본 3화음
    'major': [0, 4, 7],
    'minor': [0, 3, 7],
    'diminished': [0, 3, 6],
    'augmented': [0, 4, 8],
    
    # 7화음
    'dom7': [0, 4, 7, 10],       # G7
    'maj7': [0, 4, 7, 11],       # Cmaj7
    'min7': [0, 3, 7, 10],       # Dm7
    'min7b5': [0, 3, 6, 10],     # Bm7b5
    
    # sus 코드
    'sus2': [0, 2, 7],
    'sus4': [0, 5, 7],
}

def classify_instrument_role(part):
    """악기 파트를 역할로 분류"""
    instrument = part.getInstrument()
    if not instrument:
        return 'inner'
    
    name = instrument.instrumentName.lower()
    
    if any(keyword in name for keyword in ['bass', 'cello', 'tuba', 'bassoon', 'contrabass']):
        return 'bass'
    elif any(keyword in name for keyword in ['violin', 'flute', 'soprano', 'oboe']):
        return 'melody'
    else:
        return 'inner'


def get_concert_pitch(element, part):
    """
    이동조 악기를 실제 울리는 음(concert pitch)으로 변환
    
    music21의 toSoundingPitch() 사용
    """
    instrument = part.getInstrument()
    if not instrument:
        return element
    
    # 이동조 악기인지 확인
    transposition = instrument.transposition
    
    if transposition is None or transposition.semitones == 0:
        # 이동조 아님
        return element
    
    # Concert pitch로 변환
    try:
        if isinstance(element, note.Note):
            return element.transpose(transposition)
        elif isinstance(element, chord.Chord):
            return element.transpose(transposition)
    except:
        pass
    
    return element


def extract_bass_line_changes_filtered(score, min_duration=0.5):
    """
    베이스 라인의 변화 지점 추출 (최소 duration 필터링)
    
    Args:
        min_duration: 최소 음표 길이 (quarterLength 단위)
    """
    print("\n[베이스라인 분석]")
    
    bass_parts = [p for p in score.parts if classify_instrument_role(p) == 'bass']
    
    print(f"  베이스 파트 {len(bass_parts)}개:")
    for bp in bass_parts:
        print(f"    - {bp.partName}")
    
    # 베이스 라인 추출 (concert pitch로 변환)
    bass_timeline = []
    
    for part in bass_parts:
        for element in part.flatten().notesAndRests:
            # 최소 duration 필터링
            if element.quarterLength < min_duration:
                continue
            
            if isinstance(element, note.Note):
                # Concert pitch로 변환
                sounding = get_concert_pitch(element, part)
                if isinstance(sounding, note.Note):
                    bass_timeline.append((element.offset, sounding.pitch, element.quarterLength))
                    
            elif isinstance(element, chord.Chord):
                sounding = get_concert_pitch(element, part)
                if isinstance(sounding, chord.Chord):
                    lowest = min(sounding.pitches, key=lambda p: p.midi)
                    bass_timeline.append((element.offset, lowest, element.quarterLength))
    
    bass_timeline.sort(key=lambda x: x[0])
    
    # 베이스 음 변화 지점 찾기
    bass_changes = []
    prev_pitch_class = None
    
    for offset, p, duration in bass_timeline:
        pc = p.pitchClass
        
        if prev_pitch_class is None or pc != prev_pitch_class:
            bass_changes.append((offset, p))
            prev_pitch_class = pc
    
    print(f"  베이스 변화 {len(bass_changes)}회 감지 (최소 길이 {min_duration}박자)")
    
    return bass_changes


def get_active_pitches_concert(score, start_offset, end_offset, role_weights=None):
    """
    특정 시간 구간에서 울리는 모든 음들 수집 (concert pitch)
    """
    if role_weights is None:
        role_weights = {'bass': 1.5, 'inner': 2.0, 'melody': 0.5}
    
    pitch_class_weights = defaultdict(float)
    all_pitches = []
    
    for part in score.parts:
        role = classify_instrument_role(part)
        weight = role_weights.get(role, 1.0)
        
        instrument = part.getInstrument()
        if instrument and 'drum' in instrument.instrumentName.lower():
            continue
        
        for element in part.flatten().notesAndRests:
            note_start = element.offset
            note_end = note_start + element.quarterLength
            
            # 시간 구간 겹침 체크
            if note_start >= end_offset or note_end <= start_offset:
                continue
            
            if isinstance(element, note.Note):
                # Concert pitch로 변환
                sounding = get_concert_pitch(element, part)
                if isinstance(sounding, note.Note):
                    pc = sounding.pitch.pitchClass
                    pitch_class_weights[pc] += weight
                    all_pitches.append(sounding.pitch)
            
            elif isinstance(element, chord.Chord):
                sounding = get_concert_pitch(element, part)
                if isinstance(sounding, chord.Chord):
                    for p in sounding.pitches:
                        pc = p.pitchClass
                        pitch_class_weights[pc] += weight
                        all_pitches.append(p)
    
    return dict(pitch_class_weights), all_pitches


def match_chord_simple(pitch_classes, bass_pitch):
    """
    간단한 코드 매칭 (3화음, 7화음만)
    """
    if not pitch_classes:
        return None, 0.0
    
    root_pc = bass_pitch.pitchClass
    root_name = bass_pitch.name
    
    intervals = set()
    for pc in pitch_classes:
        interval = (pc - root_pc) % 12
        intervals.add(interval)
    
    # 템플릿 매칭
    best_match = None
    best_score = 0.0
    
    for chord_type, template in CHORD_TEMPLATES.items():
        matches = len(intervals & set(template))
        score = matches / len(template)
        
        # 너무 많은 추가 음이 있으면 페널티
        extra = len(intervals - set(template))
        if extra > 2:
            score -= 0.2 * extra
        
        if score > best_score and score >= 0.6:  # 최소 60% 일치
            best_score = score
            best_match = chord_type
    
    # 코드명 생성
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


def extract_chord_progression_v3(filepath):
    """
    개선된 코드 진행 추출 V3
    """
    print("=" * 70)
    print("🎼 코드 진행 추출 V3 (Concert Pitch + 필터링)")
    print("=" * 70)
    
    print("\n[1단계] 파일 로딩...")
    score = converter.parse(filepath)
    print(f"✅ {len(score.parts)} 파트 로드")
    
    print("\n[2단계] 악기 역할 분류...")
    role_count = {'bass': 0, 'inner': 0, 'melody': 0}
    for part in score.parts:
        role = classify_instrument_role(part)
        role_count[role] += 1
    print(f"  베이스: {role_count['bass']}, 내성: {role_count['inner']}, 멜로디: {role_count['melody']}")
    
    # 베이스라인 변화 (최소 0.5박자)
    bass_changes = extract_bass_line_changes_filtered(score, min_duration=0.5)
    
    print("\n[3단계] 코드 추론...")
    chord_progression = []
    
    for i, (offset, bass_pitch) in enumerate(bass_changes):
        if i < len(bass_changes) - 1:
            next_offset = bass_changes[i + 1][0]
        else:
            next_offset = offset + 4.0
        
        # Concert pitch로 음들 수집
        pitch_class_weights, all_pitches = get_active_pitches_concert(
            score, offset, next_offset,
            role_weights={'bass': 2.0, 'inner': 2.0, 'melody': 0.3}  # 멜로디 가중치 낮춤
        )
        
        chord_symbol, confidence = match_chord_simple(
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
        
        print(f"  마디 {measure_num:2d}, 박자 {beat:.1f}: {chord_symbol:8s} (베이스: {bass_pitch.nameWithOctave})")
    
    # 결과 요약
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
    output_json = filepath.replace('.mxl', '_chords_v3.json')
    with open(output_json, 'w', encoding='utf-8') as f:
        json.dump(chord_progression, f, indent=2, ensure_ascii=False)
    
    print(f"\n✅ JSON 저장: {output_json}")
    
    return chord_progression


if __name__ == '__main__':
    filepath = '/Users/tsk/.openclaw/workspace/music-project/ode_to_joy_source.mxl'
    progression = extract_chord_progression_v3(filepath)
