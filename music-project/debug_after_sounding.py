#!/usr/bin/env python3
"""
toSoundingPitch() 후 마디 1 확인
"""

from music21 import converter
from collections import Counter

filepath = '/Users/tsk/.openclaw/workspace/music-project/ode_to_joy_source.mxl'

print("=" * 70)
print("🔍 toSoundingPitch() 후 마디 1, 박자 2 확인")
print("=" * 70)

score = converter.parse(filepath)

# Concert pitch 변환
print("\n[변환 전] Written pitch (악보상 음)")
score = score.toSoundingPitch()
print("[변환 후] Concert pitch (실제 울리는 음)")

# 마디 1, 박자 2 (오프셋 1.0 ~ 2.0)
print("\n마디 1, 두 번째 박자:")
print("-" * 70)

concert_pitches = []

for part in score.parts:
    instrument = part.getInstrument()
    if not instrument or 'drum' in instrument.instrumentName.lower():
        continue
    
    part_name = part.partName if part.partName else "Unknown"
    
    measures = part.getElementsByClass('Measure')
    if len(measures) == 0:
        continue
    
    measure1 = measures[0]
    
    for element in measure1.flatten().notesAndRests:
        note_start = element.offset
        note_end = note_start + element.quarterLength
        
        if note_start < 2.0 and note_end > 1.0:
            if hasattr(element, 'pitch'):  # Note
                concert_pitches.append(element.pitch.name)
            elif hasattr(element, 'pitches'):  # Chord
                for p in element.pitches:
                    concert_pitches.append(p.name)

# 집계
pitch_counter = Counter(concert_pitches)

print("\n실제 울리는 음 빈도:")
for p, count in sorted(pitch_counter.items()):
    print(f"  {p}: {count}회")

if 'E' in pitch_counter:
    print("\n❌ E 음이 있습니다!")
    print("   어떤 파트에서 E가 나오는지 확인:")
    
    for part in score.parts:
        instrument = part.getInstrument()
        if not instrument or 'drum' in instrument.instrumentName.lower():
            continue
        
        part_name = part.partName
        measures = part.getElementsByClass('Measure')
        if len(measures) == 0:
            continue
        
        measure1 = measures[0]
        
        for element in measure1.flatten().notesAndRests:
            note_start = element.offset
            note_end = note_start + element.quarterLength
            
            if note_start < 2.0 and note_end > 1.0:
                if hasattr(element, 'pitch') and element.pitch.name == 'E':
                    print(f"      {part_name}: E{element.pitch.octave} (오프셋 {note_start})")
                elif hasattr(element, 'pitches'):
                    for p in element.pitches:
                        if p.name == 'E':
                            print(f"      {part_name}: E{p.octave} (오프셋 {note_start}, 코드)")
else:
    print("\n✅ E 음이 없습니다.")

print("\n결론:")
print(f"  피치 클래스: {sorted(set([{'C':0,'D':2,'E':4,'F':5,'G':7,'A':9,'B':11,'C#':1,'D#':3,'F#':6,'G#':8,'A#':10}[p] for p in pitch_counter.keys()]))}")
