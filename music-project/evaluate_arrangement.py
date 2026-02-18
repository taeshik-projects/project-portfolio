#!/usr/bin/env python3
"""
String Quartet 편곡 평가 함수

평가 항목:
1. 멜로디 명확성 (Melody Clarity)
2. 베이스 라인 강도 (Bass Line Strength)
3. 화성 풍부도 (Harmonic Richness)
4. 음역 적절성 (Range Appropriateness)
5. 리듬 정확성 (Rhythm Accuracy)
6. Voice Leading 자연스러움
"""

from music21 import converter, instrument, note
from collections import defaultdict, Counter
import math

# 현악기 음역 (MIDI 번호) - 이상적인 범위
IDEAL_RANGES = {
    'violin': {'min': 55, 'max': 103, 'comfort_min': 60, 'comfort_max': 95},
    'viola': {'min': 48, 'max': 91, 'comfort_min': 52, 'comfort_max': 80},
    'cello': {'min': 36, 'max': 84, 'comfort_min': 40, 'comfort_max': 70}
}

def evaluate_melody_clarity(score):
    """
    멜로디 명확성 평가 (0-100)
    - Violin I이 멜로디 역할을 하는가?
    - 멜로디 라인이 연속적인가?
    - 원곡의 주요 멜로디 음들을 포함하는가?
    """
    violin1_part = None
    for part in score.parts:
        if part.partName == "Violin I":
            violin1_part = part
            break
    
    if not violin1_part:
        return 0
    
    # Violin I의 음표 수집
    violin1_notes = [n for n in violin1_part.flatten().notesAndRests if hasattr(n, 'pitch')]
    
    if not violin1_notes:
        return 0
    
    # 1. 높은 음 비율 (멜로디는 일반적으로 높은 음)
    high_notes = sum(1 for n in violin1_notes if n.pitch.midi > 72)  # C5 이상
    pitch_score = (high_notes / len(violin1_notes)) * 50
    
    # 2. 연속성 평가 (같은 음이 길게 이어지는지)
    continuity_score = 0
    if len(violin1_notes) > 1:
        same_pitch_count = 0
        for i in range(1, len(violin1_notes)):
            if violin1_notes[i].pitch.midi == violin1_notes[i-1].pitch.midi:
                same_pitch_count += 1
        
        # 적절한 연속성 (너무 많이 같지도, 너무 다르지도 않음)
        continuity_ratio = same_pitch_count / (len(violin1_notes) - 1)
        if 0.1 < continuity_ratio < 0.3:
            continuity_score = 30
        elif continuity_ratio <= 0.1:
            continuity_score = 20
        elif continuity_ratio <= 0.5:
            continuity_score = 10
    
    # 3. 음역 다양성 (너무 좁지 않아야)
    midis = [n.pitch.midi for n in violin1_notes]
    range_width = max(midis) - min(midis)
    if range_width > 12:  # 1옥타브 이상
        range_score = 20
    elif range_width > 6:
        range_score = 15
    else:
        range_score = 5
    
    total_score = min(100, pitch_score + continuity_score + range_score)
    return total_score


def evaluate_bass_line_strength(score):
    """
    베이스 라인 강도 평가 (0-100)
    - Cello가 낮은 음을 연주하는가?
    - 베이스 라인이 연속적인가?
    - 화성의 기초를 제공하는가?
    """
    cello_part = None
    for part in score.parts:
        if part.partName == "Cello":
            cello_part = part
            break
    
    if not cello_part:
        return 0
    
    cello_notes = [n for n in cello_part.flatten().notesAndRests if hasattr(n, 'pitch')]
    
    if not cello_notes:
        return 0
    
    # 1. 낮은 음 비율
    low_notes = sum(1 for n in cello_notes if n.pitch.midi < 60)  # C4 이하
    pitch_score = (low_notes / len(cello_notes)) * 50
    
    # 2. 긴 duration 비율 (베이스는 일반적으로 긴 음)
    long_notes = sum(1 for n in cello_notes if n.quarterLength >= 1.0)
    duration_score = (long_notes / len(cello_notes)) * 30
    
    # 3. 음역 안정성 (너무 높지 않아야)
    midis = [n.pitch.midi for n in cello_notes]
    avg_pitch = sum(midis) / len(midis)
    if avg_pitch < 50:  # D3 이하 평균
        range_score = 20
    elif avg_pitch < 60:  # C4 이하
        range_score = 15
    else:
        range_score = 5
    
    total_score = min(100, pitch_score + duration_score + range_score)
    return total_score


def evaluate_harmonic_richness(score):
    """
    화성 풍부도 평가 (0-100)
    - 4성부가 서로 다른 음을 연주하는가?
    - 풍부한 화음(3음, 5음, 7음 등)을 형성하는가?
    - 음의 다양성이 있는가?
    """
    # 각 파트의 음표 수집
    parts_data = {}
    for part in score.parts:
        notes = [n for n in part.flatten().notesAndRests if hasattr(n, 'pitch')]
        if notes:
            parts_data[part.partName] = notes
    
    if len(parts_data) < 4:
        return 0
    
    # 1. 파트 간 음 높이 다양성
    pitch_diversity_score = 0
    all_midis = []
    for part_name, notes in parts_data.items():
        if notes:
            part_midis = [n.pitch.midi for n in notes]
            all_midis.extend(part_midis)
    
    unique_pitches = len(set([m % 12 for m in all_midis]))  # pitch class 다양성
    pitch_diversity_score = min(40, unique_pitches * 6)  # 최대 40점
    
    # 2. 동시음(화음) 분석
    chord_quality_score = 0
    # 간단히: Violin II와 Viola가 같은 음을 많이 연주하지 않는지
    violin2_notes = parts_data.get('Violin II', [])
    viola_notes = parts_data.get('Viola', [])
    
    if violin2_notes and viola_notes:
        violin2_midis = [n.pitch.midi for n in violin2_notes[:50]]  # 처음 50개
        viola_midis = [n.pitch.midi for n in viola_notes[:50]]
        
        same_count = sum(1 for i in range(min(len(violin2_midis), len(viola_midis)))
                        if violin2_midis[i] == viola_midis[i])
        same_ratio = same_count / min(len(violin2_midis), len(viola_midis))
        
        if same_ratio < 0.2:
            chord_quality_score = 30
        elif same_ratio < 0.4:
            chord_quality_score = 20
        elif same_ratio < 0.6:
            chord_quality_score = 10
    
    # 3. 음역 분포 적절성
    range_distribution_score = 0
    part_ranges = {}
    for part_name, notes in parts_data.items():
        if notes:
            midis = [n.pitch.midi for n in notes]
            part_ranges[part_name] = (min(midis), max(midis))
    
    # 각 파트가 적절한 음역에 있는지
    if len(part_ranges) >= 4:
        range_order = []
        for part_name in ['Cello', 'Viola', 'Violin II', 'Violin I']:
            if part_name in part_ranges:
                range_order.append(part_ranges[part_name][0])  # 최저음
        
        # 낮은 순서대로 정렬되어야: Cello < Viola < Violin II < Violin I
        if (range_order[0] < range_order[1] < range_order[2] < range_order[3]):
            range_distribution_score = 30
        elif (range_order[0] < range_order[1] and range_order[2] < range_order[3]):
            range_distribution_score = 20
        else:
            range_distribution_score = 10
    
    total_score = min(100, pitch_diversity_score + chord_quality_score + range_distribution_score)
    return total_score


def evaluate_range_appropriateness(score):
    """
    음역 적절성 평가 (0-100)
    - 각 악기가 연주 가능한 음역 내에서 연주하는가?
    - 편안한 음역(comfort range)에서 연주하는가?
    """
    total_score = 0
    part_count = 0
    
    for part in score.parts:
        part_name = part.partName
        notes = [n for n in part.flatten().notesAndRests if hasattr(n, 'pitch')]
        
        if not notes:
            continue
        
        part_count += 1
        
        # 악기 타입 결정
        if 'Violin' in part_name:
            inst_type = 'violin'
        elif 'Viola' in part_name:
            inst_type = 'viola'
        elif 'Cello' in part_name:
            inst_type = 'cello'
        else:
            continue
        
        ideal = IDEAL_RANGES[inst_type]
        midis = [n.pitch.midi for n in notes]
        min_midi = min(midis)
        max_midi = max(midis)
        
        # 1. 절대 음역 내에 있는지
        if min_midi >= ideal['min'] and max_midi <= ideal['max']:
            range_score = 40
        elif min_midi >= ideal['min'] - 5 and max_midi <= ideal['max'] + 5:
            range_score = 30
        else:
            range_score = 10
        
        # 2. 편안한 음역 비율
        comfort_notes = sum(1 for m in midis if ideal['comfort_min'] <= m <= ideal['comfort_max'])
        comfort_ratio = comfort_notes / len(midis)
        
        if comfort_ratio >= 0.8:
            comfort_score = 60
        elif comfort_ratio >= 0.6:
            comfort_score = 40
        elif comfort_ratio >= 0.4:
            comfort_score = 20
        else:
            comfort_score = 5
        
        part_score = (range_score + comfort_score) / 2
        total_score += part_score
    
    if part_count == 0:
        return 0
    
    return total_score / part_count


def evaluate_rhythm_accuracy(score):
    """
    리듬 정확성 평가 (0-100)
    - 각 마디가 정확히 4박자인가?
    - 리듬 패턴이 자연스러운가?
    """
    # 첫 번째 파트로 마디 분석
    first_part = score.parts[0]
    measures = first_part.getElementsByClass('Measure')
    
    if not measures:
        return 0
    
    correct_measures = 0
    total_measures = min(len(measures), 10)  # 처음 10개 마디만
    
    for i in range(total_measures):
        measure = measures[i]
        total_duration = 0
        
        for element in measure.notesAndRests:
            total_duration += element.quarterLength
        
        # 4/4 마디이므로 정확히 4.0이어야
        if abs(total_duration - 4.0) < 0.01:
            correct_measures += 1
    
    rhythm_score = (correct_measures / total_measures) * 100
    
    return rhythm_score


def evaluate_voice_leading(score):
    """
    Voice Leading 자연스러움 평가 (0-100)
    - 음과 음 사이의 이동이 자연스러운가?
    - 큰 도약(leap)이 적은가?
    - 각 성부가 독립적으로 움직이는가?
    """
    voice_leading_score = 0
    
    # 각 파트의 음표 시퀀스 분석
    for part in score.parts:
        notes = [n for n in part.flatten().notesAndRests if hasattr(n, 'pitch')]
        
        if len(notes) < 2:
            continue
        
        # 도약(leap) 분석
        leaps = []
        for i in range(1, min(len(notes), 20)):  # 처음 20개 음표
            interval = abs(notes[i].pitch.midi - notes[i-1].pitch.midi)
            leaps.append(interval)
        
        if leaps:
            avg_leap = sum(leaps) / len(leaps)
            # 평균 도약이 작을수록 좋음 (stepwise motion)
            if avg_leap <= 3:  # 3반음 이하 평균
                part_score = 25
            elif avg_leap <= 6:  # 6반음 이하
                part_score = 15
            elif avg_leap <= 9:  # 9반음 이하
                part_score = 10
            else:
                part_score = 5
            
            voice_leading_score += part_score
    
    # 파트 간 독립성 (간단히 Violin II와 Viola 비교)
    violin2_part = None
    viola_part = None
    
    for part in score.parts:
        if part.partName == "Violin II":
            violin2_part = part
        elif part.partName == "Viola":
            viola_part = part
    
    if violin2_part and viola_part:
        violin2_notes = [n for n in violin2_part.flatten().notesAndRests if hasattr(n, 'pitch')]
        viola_notes = [n for n in viola_part.flatten().notesAndRests if hasattr(n, 'pitch')]
        
        if violin2_notes and viola_notes:
            same_count = 0
            min_len = min(len(violin2_notes), len(viola_notes), 20)
            
            for i in range(min_len):
                if (violin2_notes[i].pitch.midi == viola_notes[i].pitch.midi):
                    same_count += 1
            
            independence_ratio = 1.0 - (same_count / min_len)
            independence_score = independence_ratio * 25  # 최대 25점
            voice_leading_score += independence_score
    
    return min(100, voice_leading_score)


def evaluate_arrangement(file_path):
    """
    전체 편곡 평가
    """
    print("=" * 70)
    print("🎼 String Quartet 편곡 평가")
    print("=" * 70)
    
    score = converter.parse(file_path)
    
    # 각 항목 평가
    melody_score = evaluate_melody_clarity(score)
    bass_score = evaluate_bass_line_strength(score)
    harmony_score = evaluate_harmonic_richness(score)
    range_score = evaluate_range_appropriateness(score)
    rhythm_score = evaluate_rhythm_accuracy(score)
    voice_score = evaluate_voice_leading(score)
    
    # 가중치 적용
    weights = {
        'melody': 0.25,      # 멜로디 중요
        'bass': 0.20,        # 베이스 중요
        'harmony': 0.20,     # 화성 중요
        'range': 0.15,       # 음역 적절성
        'rhythm': 0.10,      # 리듬 정확성
        'voice': 0.10        # Voice leading
    }
    
    weighted_total = (
        melody_score * weights['melody'] +
        bass_score * weights['bass'] +
        harmony_score * weights['harmony'] +
        range_score * weights['range'] +
        rhythm_score * weights['rhythm'] +
        voice_score * weights['voice']
    )
    
    # 결과 출력
    print(f"\n📊 평가 결과:")
    print(f"  1. 멜로디 명확성: {melody_score:.1f}/100")
    print(f"  2. 베이스 라인 강도: {bass_score:.1f}/100")
    print(f"  3. 화성 풍부도: {harmony_score:.1f}/100")
    print(f"  4. 음역 적절성: {range_score:.1f}/100")
    print(f"  5. 리듬 정확성: {rhythm_score:.1f}/100")
    print(f"  6. Voice Leading: {voice_score:.1f}/100")
    
    print(f"\n⭐️ 가중 평균: {weighted_total:.1f}/100")
    
    # 진단 및 개선 제안
    print(f"\n🔍 진단 및 개선 제안:")
    
    if melody_score < 70:
        print(f"  - ❌ 멜로디 명확성 부족: Violin I이 높은 음을 더 많이 연주해야")
    
    if bass_score < 70:
        print(f"  - ❌ 베이스 라인 약함: Cello가 더 낮은 음, 긴 duration의 음을 연주해야")
    
    if harmony_score < 70:
        print(f"  - ❌ 화성 풍부도 부족: Violin II와 Viola가 서로 다른 음을 연주해야")
    
    if range_score < 70:
        print(f"  - ❌ 음역 문제: 일부 악기가 이상적인 음역 밖에서 연주 중")
    
    if rhythm_score < 100:
        print(f"  - ⚠️ 리듬 정확성: 일부 마디가 4박자가 아님")
    
    if voice_score < 70:
        print(f"  - ❌ Voice Leading 문제: 도약이 너무 크거나 성부 독립성 부족")
    
    return {
        'melody': melody_score,
        'bass': bass_score,
        'harmony': harmony_score,
        'range': range_score,
        'rhythm': rhythm_score,
        'voice': voice_score,
        'total': weighted_total
    }


if __name__ == '__main__':
    # V8 평가
    print("\n🎻 Ode to Joy V8 편곡 평가...")
    v8_result = evaluate_arrangement('/Users/tsk/.openclaw/workspace/music-project/ode_to_joy_quartet_v8.musicxml')
    
    print(f"\n{'='*70}")
    print("📈 종합 평가 및 V9 설계 방향")
    print(f"{'='*70}")
    
    # 주요 문제점 파악
    print(f"\n🎯 주요 문제점:")
    if v8_result['harmony'] < 70:
        print(f"  1. 화성 풍부도 낮음 ({v8_result['harmony']:.1f}/100)")
        print(f"     → Violin II와 Viola가 같은 음 연주 중")
        print(f"     → 해결: 중음역대 더 다양한 화성 구성")
    
    if v8_result['voice'] < 70:
        print(f"  2. Voice Leading 문제 ({v8_result['voice']:.1f}/100)")
        print(f"     → 도약이 크거나 성부 독립성 부족")
        print(f"     → 해결: stepwise motion 강화, 성부 간 차이화")
    
    print(f"\n💡 V9 설계 전략:")
    print(f"  1. 화성 다양화 알고리즘:")
    print(f"     - 각 시간대별로 4개의 서로 다른 pitch class 선택")
    print(f"     - 3음, 5음, 7음 등 풍부한 화음 구성")
    print(f"     - Violin II와 Viola의 역할 명확히 분리")
    
    print(f"\n  2. Voice Leading 최적화:")
    print(f"     - 이전 음과의 간격 최소화 (stepwise motion)")
    print(f"     - 각 성부의 독립적인 움직임 보장")
    print(f"     - 화성 변화 시 자연스러운 연결")
    
    print(f"\n  3. 리듬 정확성 유지:")
    print(f"     - V8의 마디 단위 접근법 유지")
    print(f"     - 각 마디 정확히 4박자 보장")
    
    print(f"\n🎯 목표: 총점 {v8_result['total']:.1f} → 85.0+ 향상")