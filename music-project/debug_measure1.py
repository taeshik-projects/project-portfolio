#!/usr/bin/env python3
"""
마디 1의 실제 음들 디버깅
"""

from music21 import converter, note, chord

filepath = '/Users/tsk/.openclaw/workspace/music-project/ode_to_joy_source.mxl'

print("=" * 70)
print("🔍 마디 1 음표 디버깅")
print("=" * 70)

score = converter.parse(filepath)

# 마디 1 (오프셋 0.0 ~ 4.0)
print("\n[마디 1] 오프셋 0.0 ~ 4.0")
print("-" * 70)

all_notes_measure1 = []

for part in score.parts:
    instrument = part.getInstrument()
    if not instrument:
        continue
    
    part_name = part.partName if part.partName else "Unknown"
    instrument_name = instrument.instrumentName
    
    # 마디 1 찾기
    measures = part.getElementsByClass('Measure')
    if len(measures) == 0:
        continue
    
    measure1 = measures[0]
    
    notes_in_measure = []
    
    for element in measure1.flatten().notesAndRests:
        if isinstance(element, note.Note):
            notes_in_measure.append({
                'offset': element.offset,
                'pitch': element.pitch.nameWithOctave,
                'duration': element.quarterLength
            })
            all_notes_measure1.append({
                'part': part_name,
                'instrument': instrument_name,
                'offset': element.offset,
                'pitch': element.pitch.nameWithOctave,
                'pitch_class': element.pitch.pitchClass,
                'midi': element.pitch.midi,
                'duration': element.quarterLength
            })
        elif isinstance(element, chord.Chord):
            for p in element.pitches:
                notes_in_measure.append({
                    'offset': element.offset,
                    'pitch': p.nameWithOctave,
                    'duration': element.quarterLength
                })
                all_notes_measure1.append({
                    'part': part_name,
                    'instrument': instrument_name,
                    'offset': element.offset,
                    'pitch': p.nameWithOctave,
                    'pitch_class': p.pitchClass,
                    'midi': p.midi,
                    'duration': element.quarterLength
                })
    
    if notes_in_measure:
        print(f"\n{part_name} ({instrument_name}):")
        for n in notes_in_measure:
            print(f"  오프셋 {n['offset']:.2f}: {n['pitch']:6s} (길이: {n['duration']:.2f})")

# 오프셋 순으로 정렬
all_notes_measure1.sort(key=lambda x: x['offset'])

print("\n" + "=" * 70)
print("📊 시간축 순서대로 모든 음:")
print("=" * 70)

for n in all_notes_measure1:
    print(f"오프셋 {n['offset']:.2f}: {n['pitch']:6s} (PC:{n['pitch_class']:2d}, MIDI:{n['midi']:3d}) - {n['part'][:20]:20s}")

# 피치 클래스 분석
print("\n" + "=" * 70)
print("📊 시간 구간별 피치 클래스:")
print("=" * 70)

for start in [0.0, 1.0, 2.0, 3.0]:
    end = start + 1.0
    print(f"\n박자 {start+1:.0f} (오프셋 {start:.1f} ~ {end:.1f}):")
    
    pitches_in_range = []
    for n in all_notes_measure1:
        note_start = n['offset']
        note_end = note_start + n['duration']
        
        # 겹치는지 확인
        if note_start < end and note_end > start:
            pitches_in_range.append(n)
    
    # 피치 클래스 추출
    pitch_classes = set()
    for n in pitches_in_range:
        pitch_classes.add(n['pitch_class'])
    
    print(f"  피치 클래스: {sorted(pitch_classes)}")
    
    # 실제 음 이름
    pitch_names = set()
    for n in pitches_in_range:
        pitch_names.add(n['pitch'][:-1])  # 옥타브 제거
    
    print(f"  음 이름: {sorted(pitch_names)}")
    
    # 주요 악기만
    print(f"  주요 음들:")
    for n in pitches_in_range[:10]:  # 처음 10개만
        print(f"    {n['pitch']:6s} - {n['part'][:15]:15s}")
