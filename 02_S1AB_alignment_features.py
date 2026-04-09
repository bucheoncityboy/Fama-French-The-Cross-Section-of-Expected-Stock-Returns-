"""
02_S1AB_alignment_features.py
Phase 2: 시점 정렬 및 병합 (Alignment & Merging)
📖 논문 참조: Section I.A. Data

Phase 3: 팩터 엔지니어링 (Feature Engineering)
📖 논문 참조: Section I.A. Data (변수 정의)

Fama-French (1992) "The Cross-Section of Expected Stock Returns"
"""

import pandas as pd
import numpy as np
import os
import warnings
warnings.filterwarnings('ignore')

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(BASE_DIR, 'output')

print("=" * 70)
print("Phase 2: 시점 정렬 및 병합 + Phase 3: 팩터 산출")
print("=" * 70)

# ============================================================
# 데이터 로드
# ============================================================
print("\n[데이터 로드]")
crsp = pd.read_parquet(os.path.join(OUTPUT_DIR, '01_crsp_clean.parquet'))
comp = pd.read_parquet(os.path.join(OUTPUT_DIR, '02_compustat_clean.parquet'))
ff = pd.read_parquet(os.path.join(OUTPUT_DIR, '03_ff_factors.parquet'))
print(f"  CRSP: {len(crsp):,} rows")
print(f"  Compustat: {len(comp):,} rows")
print(f"  FF Factors: {len(ff):,} rows")

# ============================================================
# 2-1. 포트폴리오 형성 시점 — jdate 파생 변수
# ============================================================
print("\n[2-1] jdate 파생 변수 생성")

# jdate: 포트폴리오 형성 연도
# 7~12월 → jdate = year, 1~6월 → jdate = year - 1
crsp['jdate'] = np.where(crsp['month'] >= 7, crsp['year'], crsp['year'] - 1)

# ============================================================
# 2-1a. ME_June (t년 6월 말) — Size 팩터용
# ============================================================
print("[2-1a] ME_June 추출 (t년 6월 말)")
crsp_june = crsp[crsp['month'] == 6][['PERMNO', 'year', 'ME_millions', 'EXCHCD']].copy()
crsp_june = crsp_june.rename(columns={
    'ME_millions': 'ME_June',
    'year': 'jdate'  # 6월의 year가 곧 jdate
})
print(f"  6월 관측치: {len(crsp_june):,}")

# ============================================================
# 2-1b. ME_Dec (t-1년 12월 말) — 회계 비율 분모용
# ============================================================
print("[2-1b] ME_Dec 추출 (t-1년 12월 말)")
crsp_dec = crsp[crsp['month'] == 12][['PERMNO', 'year', 'ME_millions', 'CUSIP6']].copy()
crsp_dec = crsp_dec.rename(columns={
    'ME_millions': 'ME_Dec',
    'year': 'dec_year'
})
print(f"  12월 관측치: {len(crsp_dec):,}")

# ============================================================
# 2-2. CRSP-Compustat 매핑 (CUSIP6 기반)
# ============================================================
# NOTE: 현재 CUSIP6 기반 매핑 사용 (성공률 ~70%)
# 개선안: CRSP-Compustat Merged (CCM) 링크 테이블 사용 시 매핑률 90%+ 가능
# CCM 테이블은 WRDS에서 'crsp.ccmxpf_linktable' 또는 'comp.names'에서 획득 가능
# 주요 컬럼: gvkey, lpermno, lpermco, linktype, linkprim, linkdt, linkenddt
# ============================================================
print("\n[2-2] CRSP-Compustat 병합 (CUSIP6 기반)")

# Compustat의 year = t-1년 결산 데이터
# 이를 t년 포트폴리오 형성 기간(jdate=t)에 매핑
# 즉 comp의 year(=t-1)에 +1 해서 jdate(=t)로 대응
comp['jdate'] = comp['year'] + 1

# 12월 ME와 Compustat를 CUSIP6 + 연도로 매핑
# ME_Dec의 dec_year = comp의 year (= t-1년)
comp_with_me = comp.merge(
    crsp_dec[['PERMNO', 'CUSIP6', 'ME_Dec', 'dec_year']],
    left_on=['cusip6', 'year'],
    right_on=['CUSIP6', 'dec_year'],
    how='inner'
)

# 중복 처리: 동일 PERMNO-jdate에 여러 gvkey 매핑 시 가장 최근 datadate 우선
comp_with_me = comp_with_me.sort_values(['PERMNO', 'jdate', 'datadate'])
n_before = len(comp_with_me)
comp_with_me = comp_with_me.drop_duplicates(subset=['PERMNO', 'jdate'], keep='last')
print(f"  CUSIP6 매칭 후: {len(comp_with_me):,} (중복 {n_before - len(comp_with_me):,} 제거)")

# 매핑 성공률 확인
n_comp_unique = comp['cusip6'].nunique()
n_matched = comp_with_me['cusip6'].nunique()
match_rate = n_matched / n_comp_unique * 100
print(f"  매핑 성공률: {match_rate:.1f}% ({n_matched:,}/{n_comp_unique:,} CUSIP6)")

if match_rate < 70:
    print("  ⚠️ 매핑 성공률 70% 미만 — 데이터 품질 경고!")

# ============================================================
# 2-2a. 6월 ME (Size) 병합
# ============================================================
print("\n[2-2a] ME_June 병합")
merged = comp_with_me.merge(
    crsp_june[['PERMNO', 'jdate', 'ME_June', 'EXCHCD']],
    on=['PERMNO', 'jdate'],
    how='inner'
)
print(f"  ME_June 병합 후: {len(merged):,}")

# ============================================================
# 2-3. 최소 데이터 요건 확인
# ============================================================
print("\n[2-3] 최소 데이터 요건 적용")
n_before = len(merged)

# ME_Dec > 0, ME_June > 0, BE > 0 (이미 적용됨), at 존재
merged = merged[
    (merged['ME_Dec'] > 0) &
    (merged['ME_June'] > 0) &
    (merged['BE'] > 0) &
    (merged['at'].notna()) &
    (merged['at'] > 0)
]
print(f"  최소 요건 적용 후: {len(merged):,} ({n_before - len(merged):,} 제거)")

# ============================================================
# Phase 3: 팩터 변수 산출
# ============================================================
print("\n" + "=" * 70)
print("Phase 3: 팩터 변수 산출")
print("=" * 70)

# 3-1. 독립 변수 산출
print("\n[3-1] 독립 변수 산출")

# Size: ln(ME_June)
merged['ln_ME'] = np.log(merged['ME_June'])

# Book-to-Market: ln(BE / ME_Dec)
merged['BEME'] = merged['BE'] / merged['ME_Dec']
merged['ln_BEME'] = np.log(merged['BEME'])

# Leverage
merged['ln_A_ME'] = np.log(merged['at'] / merged['ME_Dec'])
merged['ln_A_BE'] = np.log(merged['at'] / merged['BE'])

# E/P (E = ib + txdi - dvp, 이미 Phase 1에서 산출)
merged['EP_dummy'] = (merged['E'] < 0).astype(int)
merged['EP_positive'] = np.where(merged['E'] > 0, merged['E'] / merged['ME_Dec'], 0)

# inf/nan 처리
for col in ['ln_ME', 'ln_BEME', 'ln_A_ME', 'ln_A_BE', 'EP_positive']:
    n_inf = np.isinf(merged[col]).sum()
    if n_inf > 0:
        print(f"  {col}: {n_inf} inf 값 → NaN 변환")
    merged[col] = merged[col].replace([np.inf, -np.inf], np.nan)

# inf/nan이 있는 행 제거
n_before = len(merged)
merged = merged.dropna(subset=['ln_ME', 'ln_BEME', 'ln_A_ME', 'ln_A_BE'])
print(f"  inf/NaN 제거 후: {len(merged):,} ({n_before - len(merged):,} 제거)")

# 변수별 기초 통계
print("\n[3-1] 변수별 기초 통계:")
stats_cols = ['ln_ME', 'ln_BEME', 'ln_A_ME', 'ln_A_BE', 'EP_dummy', 'EP_positive']
stats = merged[stats_cols].describe(percentiles=[.05, .25, .5, .75, .95]).T
stats = stats[['mean', 'std', '5%', '25%', '50%', '75%', '95%']]
print(stats.round(4).to_string())

# 연도별 기업 수
print("\n[진단] 연도별 기업 수:")
yearly_counts = merged.groupby('jdate')['PERMNO'].nunique()
print(f"  평균: {yearly_counts.mean():.0f}, 최소: {yearly_counts.min()}, 최대: {yearly_counts.max()}")
print(f"  처음 5년: {yearly_counts.head().to_dict()}")
print(f"  마지막 5년: {yearly_counts.tail().to_dict()}")

# ============================================================
# 저장
# ============================================================
print("\n" + "=" * 70)
print("[저장]")

# 핵심 컬럼만 선택하여 저장
keep_cols = [
    'PERMNO', 'gvkey', 'jdate', 'EXCHCD',
    'ME_June', 'ME_Dec', 'BE', 'at', 'E',
    'ln_ME', 'ln_BEME', 'ln_A_ME', 'ln_A_BE',
    'EP_dummy', 'EP_positive', 'BEME'
]
merged_out = merged[keep_cols].copy()
merged_out.to_parquet(os.path.join(OUTPUT_DIR, '04_merged_features.parquet'), index=False)
print(f"  → 04_merged_features.parquet ({len(merged_out):,} rows)")

# CRSP 전체 (jdate 포함)를 따로 저장 (Phase 4에서 수익률 시계열 필요)
crsp_out = crsp[['PERMNO', 'date', 'year', 'month', 'jdate', 'RET', 'EXCHCD', 'ME_millions']].copy()
crsp_out.to_parquet(os.path.join(OUTPUT_DIR, '04_crsp_monthly.parquet'), index=False)
print(f"  → 04_crsp_monthly.parquet ({len(crsp_out):,} rows)")

print(f"\n✅ Phase 2+3 완료!")
print(f"   최종 기업-연도 관측치: {len(merged_out):,}")
print(f"   분석 기간 (jdate): {merged_out['jdate'].min()} ~ {merged_out['jdate'].max()}")
