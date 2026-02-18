#!/usr/bin/env python3
"""
V10 편곡 평가 (클래식 원칙 통합 평가 포함)
"""

import sys
import os
from collections import defaultdict
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from evaluate_arrangement import evaluate_arrangement
from music21 import converter

def evaluate_classical_principles(score):
    """
    클래식 원칙 평가 (추가 평가 항목)
    """
    # 1. 평행 5도/8도 검출
    parallel_violations = detect_parallel_intervals(score)
    
    # 2. 화성 진행 패턴 평가
    harmonic_progression_score = evaluate_harmonic_progression(score)
    
    # 3. 음역 적절성 (클래식 기준)
    range_classical_score = evaluate_range_classical(score)
    
    # 4. 블렌딩 평가
    blending_score = evaluate_blending(score)
    
    return {
        'parallel_violations': len(parallel_violations),
        'harmonic_progression': harmonic_progression_score,
        'range_classical': range_classical_score,
        'blending': blending_score
    }

def detect_parallel_intervals(score):
    """
    평행 5도/8도 검출
    """
    violations = []
    
    # 각 성부의 음 추출
    parts = {}
    for part in score.parts:
        if 'Violin I' in part.partName:
            parts['violin1'] = [n.pitch.midi for n in part.flatten().notes if hasattr(n, 'pitch')]
        elif 'Violin II' in part.partName:
            parts['violin2'] = [n.pitch.midi for n in part.flatten().notes if hasattr(n, 'pitch')]
        elif 'Viola' in part.partName:
            parts['viola'] = [n.pitch.midi for n in part.flatten().notes if hasattr(n, 'pitch')]
        elif 'Cello' in part.partName:
            parts['cello'] = [n.pitch.midi for n in part.flatten().notes if hasattr(n, 'pitch')]
    
    # 성부 쌍별 검사
    pairs = [
        ('violin1', 'violin2'),
        ('violin1', 'viola'),
        ('violin1', 'cello'),
        ('violin2', 'viola'),
        ('violin2', 'cello'),
        ('viola', 'cello')
    ]
    
    for voice1_name, voice2_name in pairs:
        if voice1_name not in parts or voice2_name not in parts:
            continue
            
        voice1 = parts[voice1_name]
        voice2 = parts[voice2_name]
        
        min_len = min(len(voice1), len(voice2))
        for i in range(1, min_len):
            prev_interval = abs(voice1[i-1] - voice2[i-1]) % 12
            curr_interval = abs(voice1[i] - voice2[i]) % 12
            
            # 5도(7반음) 또는 8도(0반음)
            if (prev_interval == 7 and curr_interval == 7) or (prev_interval == 0 and curr_interval == 0):
                # 같은 방향 이동 확인
                prev_dir = voice1[i] - voice1[i-1]
                curr_dir = voice2[i] - voice2[i-1]
                if prev_dir * curr_dir > 0:  # 같은 방향
                    violations.append({
                        'voices': (voice1_name, voice2_name),
                        'position': i,
                        'interval': '5th' if prev_interval == 7 else '8ve'
                    })
    
    return violations

def evaluate_harmonic_progression(score):
    """
    화성 진행 패턴 평가 (기능화음 진행 적절성)
    """
    # 간단한 구현: 주요 화음(I, IV, V) 사용 비율
    cello_part = None
    for part in score.parts:
        if 'Cello' in part.partName:
            cello_part = part
            break
    
    if not cello_part:
        return 50
    
    # Cello의 루트 음 추출 (간단화)
    cello_notes = [n for n in cello_part.flatten().notes if hasattr(n, 'pitch')]
    if len(cello_notes) < 4:
        return 50
    
    # 첫 4개 음의 pitch class
    root_pcs = [n.pitch.midi % 12 for n in cello_notes[:4]]
    
    # I, IV, V 화음 판별 (C major 기준)
    tonic_pcs = {0, 4, 7}  # C, E, G
    subdominant_pcs = {5, 9, 0}  # F, A, C
    dominant_pcs = {7, 11, 2}  # G, B, D
    
    score = 0
    for pc in root_pcs:
        if pc in tonic_pcs:
            score += 25
        elif pc in subdominant_pcs:
            score += 25
        elif pc in dominant_pcs:
            score += 25
    
    return min(score, 100)

def evaluate_range_classical(score):
    """
    클래식 음역 적절성 평가
    """
    # 클래식 현악기 이상적 음역
    CLASSICAL_RANGES = {
        'violin': {'min': 55, 'max': 88, 'ideal_min': 60, 'ideal_max': 80},  # G3-E6
        'viola': {'min': 48, 'max': 79, 'ideal_min': 52, 'ideal_max': 72},   # C3-G5
        'cello': {'min': 36, 'max': 72, 'ideal_min': 40, 'ideal_max': 65}    # C2-C5
    }
    
    total_score = 0
    part_count = 0
    
    for part in score.parts:
        part_name = part.partName.lower()
        inst_type = None
        
        if 'violin i' in part_name or 'violin ii' in part_name:
            inst_type = 'violin'
        elif 'viola' in part_name:
            inst_type = 'viola'
        elif 'cello' in part_name:
            inst_type = 'cello'
        
        if not inst_type:
            continue
        
        notes = [n for n in part.flatten().notes if hasattr(n, 'pitch')]
        if not notes:
            continue
        
        range_info = CLASSICAL_RANGES[inst_type]
        in_range_count = 0
        
        for n in notes:
            midi = n.pitch.midi
            if range_info['ideal_min'] <= midi <= range_info['ideal_max']:
                in_range_count += 1
        
        part_score = (in_range_count / len(notes)) * 100
        total_score += part_score
        part_count += 1
    
    if part_count == 0:
        return 0
    
    return total_score / part_count

def evaluate_blending(score):
    """
    블렌딩 평가 (화음 배치 적절성)
    """
    # 간단한 구현: 각 시간대별 음 간격 적절성
    # 저음역 넓은 간격, 중음역 밀집 배치 확인
    
    # 모든 성부의 음을 시간대별로 수집
    time_slots = defaultdict(list)
    
    for part in score.parts:
        part_name = part.partName
        for n in part.flatten().notes:
            if hasattr(n, 'pitch'):
                time_slots[round(n.offset, 2)].append({
                    'part': part_name,
                    'midi': n.pitch.midi
                })
    
    if not time_slots:
        return 50
    
    blending_scores = []
    
    for time, notes in time_slots.items():
        if len(notes) < 2:
            continue
        
        # MIDI 값 정렬
        midis = sorted([n['midi'] for n in notes])
        
        # 간격 계산
        intervals = []
        for i in range(1, len(midis)):
            intervals.append(midis[i] - midis[i-1])
        
        if not intervals:
            continue
        
        # 저음역 간격 평가 (첫 두 음 간격)
        bass_interval = intervals[0] if intervals else 0
        bass_score = 100 - min(abs(bass_interval - 12), 50) * 2  # 12반음(8도) 근처면 높은 점수
        
        # 중음역 간격 평가 (중간 간격들)
        if len(intervals) > 1:
            middle_intervals = intervals[1:-1] if len(intervals) > 2 else intervals[1:]
            if middle_intervals:
                avg_middle = sum(middle_intervals) / len(middle_intervals)
                middle_score = 100 - min(abs(avg_middle - 4), 20) * 5  # 4반음(3도) 근처면 높은 점수
            else:
                middle_score = 50
        else:
            middle_score = 50
        
        time_score = (bass_score + middle_score) / 2
        blending_scores.append(time_score)
    
    if not blending_scores:
        return 50
    
    return sum(blending_scores) / len(blending_scores)

def main():
    if len(sys.argv) < 2:
        print("사용법: python evaluate_v10.py <musicxml_file>")
        sys.exit(1)
    
    input_file = sys.argv[1]
    
    print("=" * 70)
    print("🎻 V10 편곡 평가 (클래식 원칙 통합)")
    print("=" * 70)
    
    # 기존 평가 함수 실행
    print("\n[1단계] 기본 평가 항목...")
    basic_result = evaluate_arrangement(input_file)
    
    print("\n[2단계] 클래식 원칙 평가...")
    score = converter.parse(input_file)
    classical_result = evaluate_classical_principles(score)
    
    print("\n" + "=" * 70)
    print("📊 종합 평가 결과")
    print("=" * 70)
    
    print("\n📈 기본 평가 항목:")
    print(f"  1. 멜로디 명확성: {basic_result['melody']:.1f}/100")
    print(f"  2. 베이스 라인 강도: {basic_result['bass']:.1f}/100")
    print(f"  3. 화성 풍부도: {basic_result['harmony']:.1f}/100")
    print(f"  4. 음역 적절성: {basic_result['range']:.1f}/100")
    print(f"  5. 리듬 정확성: {basic_result['rhythm']:.1f}/100")
    print(f"  6. Voice Leading: {basic_result['voice']:.1f}/100")
    print(f"  ⭐️ 기본 총점: {basic_result['total']:.1f}/100")
    
    print("\n🎼 클래식 원칙 평가:")
    print(f"  1. 평행 5도/8도 위반: {classical_result['parallel_violations']}건")
    parallel_score = max(0, 100 - classical_result['parallel_violations'] * 10)
    print(f"     → 점수: {parallel_score:.1f}/100")
    print(f"  2. 화성 진행 적절성: {classical_result['harmonic_progression']:.1f}/100")
    print(f"  3. 클래식 음역 적절성: {classical_result['range_classical']:.1f}/100")
    print(f"  4. 블렌딩 적절성: {classical_result['blending']:.1f}/100")
    
    # 클래식 총점 계산
    classical_total = (
        parallel_score * 0.3 +
        classical_result['harmonic_progression'] * 0.2 +
        classical_result['range_classical'] * 0.3 +
        classical_result['blending'] * 0.2
    )
    print(f"  🎵 클래식 총점: {classical_total:.1f}/100")
    
    # 최종 종합 점수
    final_total = (basic_result['total'] * 0.7 + classical_total * 0.3)
    print(f"\n🏆 최종 종합 점수: {final_total:.1f}/100")
    
    print("\n" + "=" * 70)
    print("🔍 개선 제안")
    print("=" * 70)
    
    if classical_result['parallel_violations'] > 0:
        print(f"\n❌ 평행 5도/8도 위반 {classical_result['parallel_violations']}건 발견")
        print("   → Voice Leading 규칙 엄격 적용 필요")
        print("   → detect_parallel_fifths_octaves() 함수 활용")
    
    if classical_result['harmonic_progression'] < 70:
        print(f"\n⚠️ 화성 진행 적절성 낮음 ({classical_result['harmonic_progression']:.1f}/100)")
        print("   → 기능화음(I, IV, V) 사용 비율 증가")
        print("   → 전통적 화성 진행 패턴(II-V-I 등) 적용")
    
    if classical_result['range_classical'] < 70:
        print(f"\n⚠️ 클래식 음역 적절성 낮음 ({classical_result['range_classical']:.1f}/100)")
        print("   → 각 악기 고전적 이상적 음역 내 연주 강제")
        print("   → 음역: Violin(G3-E6), Viola(C3-G5), Cello(C2-C5)")
    
    if classical_result['blending'] < 70:
        print(f"\n⚠️ 블렌딩 적절성 낮음 ({classical_result['blending']:.1f}/100)")
        print("   → 저음역 넓은 간격(8도 이상), 중음역 밀집 배치(3-4도)")
        print("   → 화음 배치 최적화 알고리즘 적용")
    
    print(f"\n🎯 V11 설계 방향:")
    print("  1. 평행 5도/8도 자동 수정 알고리즘 강화")
    print("  2. 클래식 화성 진행 패턴 템플릿 도입")
    print("  3. 엄격한 클래식 음역 제한 적용")
    print("  4. 블렌딩 원칙 기반 화음 배치 최적화")
    
    return {
        'basic': basic_result,
        'classical': classical_result,
        'classical_total': classical_total,
        'final_total': final_total
    }

if __name__ == '__main__':
    main()