#!/usr/bin/env python3
"""
개선된 코드 진행 추출 V2
- 베이스라인 변화 기반 시간 분할
- 내성 중심 코드 추론
- 옥타브 정보 유지 (텐션 노트 인식)
"""

from music21 import converter, stream, note, chord, pitch
from collections import Counter, defaultdict
import json

# 악기별 음역대 분류 기준 (MIDI 번호)
BASS_RANGE = (0, 55)      # ~G3: Cello, Bass, Tuba, Bassoon
INNER_RANGE = (48, 72)    # C3~C5: Viola, Horn, Trombone
MELODY_RANGE = (60, 108)  # C4~: Violin, Flute, Soprano

# 확장된 코드 템플릿 (피치 클래스 기준)
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
    'min7b5': [0, 3, 6, 10],     # Bm7b5 (half-diminished)
    'dim7': [0, 3, 6, 9],        # Bdim7
    
    # 텐션 노트 포함 (옥타브 정보 필요)
    'maj9': [0, 4, 7, 11, 14],   # Cmaj9 (C, E, G, B, D)
    '9': [0, 4, 7, 10, 14],      # C9 (dominant 9th)
    'min9': [0, 3, 7, 10, 14],   # Cm9
    'maj11': [0, 4, 7, 11, 14, 17],  # Cmaj11
    '11': [0, 4, 7, 10, 14, 17],     # C11
    '13': [0, 4, 7, 10, 14, 21],     # C13
    
    # sus 코드
    'sus2': [0, 2, 7],
    'sus4': [0, 5, 7],
}

def classify_instrument_role(part):
    """
    악기 파트를 역할로 분류: 'bass', 'inner', 'melody'
    """
    instrument = part.getInstrument()
    if not instrument:
        return 'inner'  # 기본값
    
    name = instrument.instrumentName.lower()
    
    # 베이스 악기
    if any(keyword in name for keyword in ['bass', 'cello', 'tuba', 'bassoon', 'contrabass']):
        return 'bass'
    
    # 멜로디 악기
    elif any(keyword in name for keyword in ['violin', 'flute', 'soprano', 'oboe', 'clarinet', 'trumpet']):
        return 'melody'
    
    # 내성 악기
    else:  # Viola, Horn, Alto, Tenor, etc.
        return 'inner'


def extract_bass_line_changes(score, min_quarter_length=0.25):
    """
    베이스 라인의 변화 지점 추출
    
    Returns:
        List of (offset, bass_pitch) tuples
    """
    print("\n[베이스라인 분석]")
    
    # 베이스 파트들 찾기
    bass_parts = [p for p in score.parts if classify_instrument_role(p) == 'bass']
    
    print(f"  베이스 파트 {len(bass_parts)}개 발견:")
    for bp in bass_parts:
        print(f"    - {bp.partName}")
    
    # 모든 베이스 음들을 시간축으로 정렬
    bass_timeline = []
    
    for part in bass_parts:
        for element in part.flatten().notesAndRests:
            if isinstance(element, note.Note):
                bass_timeline.append((element.offset, element.pitch))
            elif isinstance(element, chord.Chord):
                # 코드의 가장 낮은 음
                lowest = min(element.pitches, key=lambda p: p.midi)
                bass_timeline.append((element.offset, lowest))
    
    # 시간 순 정렬
    bass_timeline.sort(key=lambda x: x[0])
    
    # 베이스 음 변화 지점 찾기
    bass_changes = []
    prev_pitch_class = None
    
    for offset, p in bass_timeline:
        pc = p.pitchClass
        
        # 피치 클래스가 바뀌면 변화 지점
        if prev_pitch_class is None or pc != prev_pitch_class:
            bass_changes.append((offset, p))
            prev_pitch_class = pc
    
    print(f"  베이스 변화 {len(bass_changes)}회 감지")
    
    return bass_changes


def get_active_pitches_at_offset(score, start_offset, end_offset, role_weights=None):
    """
    특정 시간 구간에서 울리는 모든 음들 수집 (악기 역할별 가중치 적용)
    
    Args:
        role_weights: {'bass': 1.5, 'inner': 2.0, 'melody': 0.5}
    
    Returns:
        {pitch_class: weight, ...}
    """
    if role_weights is None:
        role_weights = {'bass': 1.5, 'inner': 2.0, 'melody': 0.5}
    
    pitch_class_weights = defaultdict(float)
    all_pitches = []  # 옥타브 정보 포함
    
    for part in score.parts:
        role = classify_instrument_role(part)
        weight = role_weights.get(role, 1.0)
        
        # 타악기 제외
        instrument = part.getInstrument()
        if instrument and 'drum' in instrument.instrumentName.lower():
            continue
        
        for element in part.flatten().notesAndRests:
            if isinstance(element, note.Note):
                # 시간 구간 체크
                note_start = element.offset
                note_end = note_start + element.quarterLength
                
                # 겹치는 구간이 있으면 포함
                if note_start < end_offset and note_end > start_offset:
                    pc = element.pitch.pitchClass
                    pitch_class_weights[pc] += weight
                    all_pitches.append(element.pitch)
            
            elif isinstance(element, chord.Chord):
                note_start = element.offset
                note_end = note_start + element.quarterLength
                
                if note_start < end_offset and note_end > start_offset:
                    for p in element.pitches:
                        pc = p.pitchClass
                        pitch_class_weights[pc] += weight
                        all_pitches.append(p)
    
    return dict(pitch_class_weights), all_pitches


def match_chord_template(pitch_classes, bass_pitch, all_pitches):
    """
    피치 클래스 + 베이스 음 + 옥타브 정보로 코드 매칭
    
    Returns:
        (chord_symbol, confidence)
    """
    if not pitch_classes:
        return None, 0.0
    
    # 베이스 음 근음 가정
    root_pc = bass_pitch.pitchClass
    root_name = bass_pitch.name
    
    # 근음 기준으로 상대 간격 계산
    intervals = set()
    for pc in pitch_classes:
        interval = (pc - root_pc) % 12
        intervals.add(interval)
    
    # 옥타브 정보로 텐션 판단 (9th = 14, 11th = 17, 13th = 21)
    extended_intervals = set()
    for p in all_pitches:
        # 근음 대비 반음 간격 (옥타브 포함)
        semitones = p.midi - bass_pitch.midi
        if semitones >= 0:
            extended_intervals.add(semitones)
    
    # 템플릿 매칭
    best_match = None
    best_score = 0.0
    
    for chord_type, template in CHORD_TEMPLATES.items():
        # 기본 매칭 (피치 클래스만)
        basic_template = set([t % 12 for t in template])
        matches = len(intervals & basic_template)
        
        # 확장 템플릿 매칭 (텐션 포함)
        if any(t >= 12 for t in template):  # 텐션 포함 코드
            extended_matches = len(extended_intervals & set(template))
            score = (matches + extended_matches) / len(template)
        else:
            score = matches / len(template)
        
        # 추가 음이 있어도 허용 (비화성음 또는 생략)
        if len(intervals) > len(basic_template):
            penalty = 0.1 * (len(intervals) - len(basic_template))
            score -= penalty
        
        if score > best_score:
            best_score = score
            best_match = chord_type
    
    # 코드명 생성
    if best_match:
        if best_match == 'major':
            chord_symbol = root_name
        elif best_match == 'minor':
            chord_symbol = f"{root_name}m"
        elif best_match == 'diminished':
            chord_symbol = f"{root_name}dim"
        elif best_match == 'augmented':
            chord_symbol = f"{root_name}aug"
        elif best_match == 'dom7':
            chord_symbol = f"{root_name}7"
        elif best_match == 'maj7':
            chord_symbol = f"{root_name}maj7"
        elif best_match == 'min7':
            chord_symbol = f"{root_name}m7"
        elif best_match == 'min7b5':
            chord_symbol = f"{root_name}m7b5"
        elif best_match == 'dim7':
            chord_symbol = f"{root_name}dim7"
        elif best_match == 'maj9':
            chord_symbol = f"{root_name}maj9"
        elif best_match == '9':
            chord_symbol = f"{root_name}9"
        elif best_match == 'min9':
            chord_symbol = f"{root_name}m9"
        elif best_match == 'maj11':
            chord_symbol = f"{root_name}maj11"
        elif best_match == '11':
            chord_symbol = f"{root_name}11"
        elif best_match == '13':
            chord_symbol = f"{root_name}13"
        elif best_match == 'sus2':
            chord_symbol = f"{root_name}sus2"
        elif best_match == 'sus4':
            chord_symbol = f"{root_name}sus4"
        else:
            chord_symbol = f"{root_name}{best_match}"
        
        return chord_symbol, best_score
    
    return None, 0.0


def extract_chord_progression_v2(filepath):
    """
    개선된 코드 진행 추출 메인 함수
    """
    print("=" * 70)
    print("🎼 코드 진행 추출 V2 (베이스라인 기반)")
    print("=" * 70)
    
    # 1. 파일 로드
    print("\n[1단계] 파일 로딩...")
    score = converter.parse(filepath)
    print(f"✅ {len(score.parts)} 파트 로드 완료")
    
    # 2. 악기 역할 분류
    print("\n[2단계] 악기 역할 분류...")
    role_count = {'bass': 0, 'inner': 0, 'melody': 0}
    for part in score.parts:
        role = classify_instrument_role(part)
        role_count[role] += 1
    
    print(f"  베이스: {role_count['bass']}개")
    print(f"  내성: {role_count['inner']}개")
    print(f"  멜로디: {role_count['melody']}개")
    
    # 3. 베이스라인 변화 감지
    bass_changes = extract_bass_line_changes(score)
    
    # 4. 각 구간별 코드 추론
    print("\n[3단계] 코드 추론 시작...")
    chord_progression = []
    
    for i, (offset, bass_pitch) in enumerate(bass_changes):
        # 다음 변화 지점까지의 구간
        if i < len(bass_changes) - 1:
            next_offset = bass_changes[i + 1][0]
        else:
            # 마지막 구간: 악보 끝까지
            next_offset = offset + 8.0  # 임시로 2마디 가정
        
        # 해당 구간의 음들 수집 (내성 가중치 높게)
        pitch_class_weights, all_pitches = get_active_pitches_at_offset(
            score, offset, next_offset,
            role_weights={'bass': 1.5, 'inner': 2.0, 'melody': 0.5}
        )
        
        # 코드 매칭
        chord_symbol, confidence = match_chord_template(
            pitch_class_weights.keys(),
            bass_pitch,
            all_pitches
        )
        
        # 마디 번호 계산 (4/4박자 가정)
        measure_num = int(offset / 4.0) + 1
        beat = (offset % 4.0) + 1
        
        # 코드를 찾지 못한 경우 스킵
        if chord_symbol is None:
            continue
        
        chord_progression.append({
            'offset': float(offset),
            'measure': measure_num,
            'beat': float(beat),
            'chord': chord_symbol,
            'bass': bass_pitch.nameWithOctave,
            'confidence': float(confidence),
            'pitch_classes': sorted(pitch_class_weights.keys())
        })
        
        print(f"  오프셋 {offset:6.2f} (마디 {measure_num}, 박자 {beat:.1f}): {chord_symbol:10s} (신뢰도: {confidence:.2f})")
    
    # 5. 결과 요약
    print("\n" + "=" * 70)
    print("📊 코드 진행 요약 (마디별):")
    print("=" * 70)
    
    # 마디별로 그룹화
    by_measure = defaultdict(list)
    for item in chord_progression:
        by_measure[item['measure']].append(item)
    
    for measure_num in sorted(by_measure.keys()):
        chords = by_measure[measure_num]
        chord_str = ' - '.join([c['chord'] for c in chords])
        print(f"마디 {measure_num:2d}: {chord_str}")
    
    # 6. JSON 저장
    output_json = filepath.replace('.mxl', '_chords_v2.json')
    with open(output_json, 'w', encoding='utf-8') as f:
        json.dump(chord_progression, f, indent=2, ensure_ascii=False)
    
    print(f"\n✅ JSON 저장 완료: {output_json}")
    
    return chord_progression


if __name__ == '__main__':
    filepath = '/Users/tsk/.openclaw/workspace/music-project/ode_to_joy_source.mxl'
    progression = extract_chord_progression_v2(filepath)
