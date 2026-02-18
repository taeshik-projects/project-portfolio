#!/usr/bin/env python3
"""
Concert pitch 변환 디버깅
"""

from music21 import converter, note, chord

filepath = '/Users/tsk/.openclaw/workspace/music-project/ode_to_joy_source.mxl'

print("=" * 70)
print("🔍 Concert Pitch 변환 디버깅")
print("=" * 70)

score = converter.parse(filepath)

# 마디 1, 오프셋 1.0 ~ 2.0 (두 번째 박자)
print("\n[마디 1, 두 번째 박자] 오프셋 1.0 ~ 2.0")
print("-" * 70)

for part in score.parts:
    instrument = part.getInstrument()
    if not instrument:
        continue
    
    part_name = part.partName if part.partName else "Unknown"
    instrument_name = instrument.instrumentName
    
    # 이동조 악기 정보
    transposition = instrument.transposition
    trans_info = ""
    if transposition:
        trans_info = f" (이동: {transposition.directedName}, {transposition.semitones} 반음)"
    
    # 마디 1
    measures = part.getElementsByClass('Measure')
    if len(measures) == 0:
        continue
    
    measure1 = measures[0]
    
    notes_at_beat2 = []
    
    for element in measure1.flatten().notesAndRests:
        note_start = element.offset
        note_end = note_start + element.quarterLength
        
        # 오프셋 1.0 ~ 2.0 구간과 겹치는지
        if note_start < 2.0 and note_end > 1.0:
            
            if isinstance(element, note.Note):
                written_pitch = element.pitch.nameWithOctave
                
                # Concert pitch로 변환 시도
                try:
                    if transposition:
                        concert_note = element.transpose(transposition)
                        concert_pitch = concert_note.pitch.nameWithOctave
                    else:
                        concert_pitch = written_pitch
                except:
                    concert_pitch = f"{written_pitch} (변환실패)"
                
                notes_at_beat2.append({
                    'written': written_pitch,
                    'concert': concert_pitch
                })
            
            elif isinstance(element, chord.Chord):
                for p in element.pitches:
                    written_pitch = p.nameWithOctave
                    
                    try:
                        if transposition:
                            concert_p = p.transpose(transposition)
                            concert_pitch = concert_p.nameWithOctave
                        else:
                            concert_pitch = written_pitch
                    except:
                        concert_pitch = f"{written_pitch} (변환실패)"
                    
                    notes_at_beat2.append({
                        'written': written_pitch,
                        'concert': concert_pitch
                    })
    
    if notes_at_beat2:
        print(f"\n{part_name} ({instrument_name}){trans_info}:")
        for n in notes_at_beat2:
            print(f"  악보: {n['written']:6s} → 실제 음: {n['concert']}")

# 피치 클래스 집계
print("\n" + "=" * 70)
print("📊 두 번째 박자의 실제 음 (Concert Pitch) 집계:")
print("=" * 70)

from collections import Counter

concert_pitches = []
concert_pitch_classes = []

for part in score.parts:
    instrument = part.getInstrument()
    if not instrument:
        continue
    
    if 'drum' in instrument.instrumentName.lower():
        continue
    
    transposition = instrument.transposition
    
    measures = part.getElementsByClass('Measure')
    if len(measures) == 0:
        continue
    
    measure1 = measures[0]
    
    for element in measure1.flatten().notesAndRests:
        note_start = element.offset
        note_end = note_start + element.quarterLength
        
        if note_start < 2.0 and note_end > 1.0:
            if isinstance(element, note.Note):
                if transposition:
                    try:
                        concert_note = element.transpose(transposition)
                        concert_pitches.append(concert_note.pitch.name)
                        concert_pitch_classes.append(concert_note.pitch.pitchClass)
                    except:
                        pass
                else:
                    concert_pitches.append(element.pitch.name)
                    concert_pitch_classes.append(element.pitch.pitchClass)
            
            elif isinstance(element, chord.Chord):
                for p in element.pitches:
                    if transposition:
                        try:
                            concert_p = p.transpose(transposition)
                            concert_pitches.append(concert_p.name)
                            concert_pitch_classes.append(concert_p.pitchClass)
                        except:
                            pass
                    else:
                        concert_pitches.append(p.name)
                        concert_pitch_classes.append(p.pitchClass)

pitch_counter = Counter(concert_pitches)
pc_counter = Counter(concert_pitch_classes)

print("\n음 이름 빈도:")
for pitch, count in pitch_counter.most_common():
    print(f"  {pitch}: {count}회")

print("\n피치 클래스 (0-11):")
pc_names = {0: 'C', 1: 'C#', 2: 'D', 3: 'Eb', 4: 'E', 5: 'F', 6: 'F#', 7: 'G', 8: 'G#', 9: 'A', 10: 'Bb', 11: 'B'}
for pc in sorted(pc_counter.keys()):
    print(f"  {pc:2d} ({pc_names[pc]:3s}): {pc_counter[pc]}회")

print("\n결론:")
if 4 in pc_counter or 'E' in pitch_counter:
    print("  ❌ E 음이 있습니다! 이동조 변환이 제대로 안 됐어요.")
else:
    print("  ✅ E 음이 없습니다. 변환 성공!")
