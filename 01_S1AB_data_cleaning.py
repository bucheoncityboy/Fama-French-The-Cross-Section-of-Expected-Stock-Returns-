"""
01_S1AB_data_cleaning.py
Phase 1: 데이터 로드 및 정제 (Data Ingestion & Cleaning)
📖 논문 참조: Section I.A. Data

Fama-French (1992) "The Cross-Section of Expected Stock Returns"
"""

import pandas as pd
import numpy as np
import os
import warnings
warnings.filterwarnings('ignore')

# ============================================================
# 경로 설정
# ============================================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(BASE_DIR, 'output')
os.makedirs(OUTPUT_DIR, exist_ok=True)

CRSP_FILE = os.path.join(BASE_DIR, 'ldubue8x0da4ccwn.csv')
COMPUSTAT_FILE = os.path.join(BASE_DIR, 'idwgnwjre7hxwkoo.csv')
FF_FILE = os.path.join(BASE_DIR, 'F-F_Research_Data_Factors.csv')

print("=" * 70)
print("Phase 1: 데이터 로드 및 정제")
print("=" * 70)

# ============================================================
# 1-1. CRSP 수익률 데이터 정제
# ============================================================
print("\n[1-1] CRSP 데이터 로드 중...")
crsp_raw = pd.read_csv(CRSP_FILE)
print(f"  Raw 관측치 수: {len(crsp_raw):,}")
print(f"  컬럼: {crsp_raw.columns.tolist()}")

# 1. date 변환
crsp_raw['date'] = pd.to_datetime(crsp_raw['date'])
crsp_raw['year'] = crsp_raw['date'].dt.year
crsp_raw['month'] = crsp_raw['date'].dt.month

# 2. 샘플 유니버스 필터링
print("\n  [필터링]")
n_before = len(crsp_raw)

# 보통주만 (SHRCD ∈ {10, 11})
crsp = crsp_raw[crsp_raw['SHRCD'].isin([10, 11])].copy()
print(f"  - SHRCD {{10,11}} 필터 후: {len(crsp):,} ({n_before - len(crsp):,} 제거)")

n_before = len(crsp)
# 거래소 필터 (EXCHCD ∈ {1, 2, 3})
crsp = crsp[crsp['EXCHCD'].isin([1, 2, 3])]
print(f"  - EXCHCD {{1,2,3}} 필터 후: {len(crsp):,} ({n_before - len(crsp):,} 제거)")

n_before = len(crsp)
# 금융업종 제외 (SICCD 6000-6999)
crsp['SICCD'] = pd.to_numeric(crsp['SICCD'], errors='coerce')
crsp = crsp[~((crsp['SICCD'] >= 6000) & (crsp['SICCD'] <= 6999))]
print(f"  - 금융업종 제외 후: {len(crsp):,} ({n_before - len(crsp):,} 제거)")

# 3. RET, PRC 비정상 문자열 처리
n_ret_bad = crsp['RET'].apply(lambda x: isinstance(x, str) and not x.replace('.','').replace('-','').replace('+','').replace('e','').replace('E','').isdigit()).sum() if crsp['RET'].dtype == object else 0
crsp['RET'] = pd.to_numeric(crsp['RET'], errors='coerce')
crsp['PRC'] = pd.to_numeric(crsp['PRC'], errors='coerce')
print(f"\n  RET/PRC 문자열→NaN 변환: RET {n_ret_bad:,}건")

# 4. PRC 절대값 (음수 PRC = Bid/Ask 평균)
n_neg_prc = (crsp['PRC'] < 0).sum()
crsp['PRC'] = crsp['PRC'].abs()
print(f"  음수 PRC 절대값 처리: {n_neg_prc:,}건")

# 5. 시가총액 계측
# SHROUT는 천주 단위, ME = |PRC| × SHROUT (천 달러 단위)
crsp['ME'] = crsp['PRC'] * crsp['SHROUT']
# 백만 달러 단위로 변환 (Compustat와 스케일 통일)
crsp['ME_millions'] = crsp['ME'] / 1000

# ME가 유효한 관측치만 유지
n_before = len(crsp)
crsp = crsp.dropna(subset=['ME'])
crsp = crsp[crsp['ME'] > 0]
print(f"  ME > 0 필터 후: {len(crsp):,} ({n_before - len(crsp):,} 제거)")

# CUSIP 6자리 추출
crsp['CUSIP6'] = crsp['CUSIP'].astype(str).str[:6]

print(f"\n  ✅ CRSP 최종 관측치: {len(crsp):,}")
print(f"  기간: {crsp['date'].min().strftime('%Y-%m')} ~ {crsp['date'].max().strftime('%Y-%m')}")
print(f"  고유 PERMNO 수: {crsp['PERMNO'].nunique():,}")

# ============================================================
# 1-2. Compustat 재무 데이터 정제
# ============================================================
print("\n" + "=" * 70)
print("[1-2] Compustat 데이터 로드 중...")
comp_raw = pd.read_csv(COMPUSTAT_FILE)
print(f"  Raw 관측치 수: {len(comp_raw):,}")
print(f"  컬럼: {comp_raw.columns.tolist()}")

# 1. datadate 변환
comp_raw['datadate'] = pd.to_datetime(comp_raw['datadate'])
comp_raw['year'] = comp_raw['datadate'].dt.year

# 2. Compustat 필터링
print("\n  [필터링]")
n_before = len(comp_raw)
comp = comp_raw[
    (comp_raw['indfmt'] == 'INDL') &
    (comp_raw['datafmt'] == 'STD') &
    (comp_raw['consol'] == 'C') &
    (comp_raw['curcd'] == 'USD')
].copy()
print(f"  - 포맷 필터 (INDL/STD/C/USD) 후: {len(comp):,} ({n_before - len(comp):,} 제거)")

n_before = len(comp)
# 금융업종 제외
comp = comp[~((comp['sic'] >= 6000) & (comp['sic'] <= 6999))]
print(f"  - 금융업종 제외 후: {len(comp):,} ({n_before - len(comp):,} 제거)")

# costat 필터 미적용 (논문은 상장폐지 기업도 포함)
print(f"  - costat 필터 미적용 (논문 준수)")

# 3. Survivorship Bias 통제 — 2년 사전 등록 요건
# 1962년 이전 데이터 제외
n_before = len(comp)
comp = comp[comp['year'] >= 1962]
print(f"  - 1962년 이전 데이터 제외 후: {len(comp):,} ({n_before - len(comp):,} 제거)")

# gvkey별 최초 등장 연도
first_year = comp.groupby('gvkey')['year'].min().reset_index()
first_year.columns = ['gvkey', 'first_year']
comp = comp.merge(first_year, on='gvkey', how='left')

n_before = len(comp)
comp = comp[comp['year'] - comp['first_year'] >= 2]
print(f"  - 2년 사전 등록 요건 적용 후: {len(comp):,} ({n_before - len(comp):,} 제거)")

# 4. Fiscal Year End 처리
# 동일 gvkey 내 같은 calendar year에 여러 결산 존재 시, 가장 최근 datadate 우선
comp = comp.sort_values(['gvkey', 'year', 'datadate'])
n_before = len(comp)
comp = comp.drop_duplicates(subset=['gvkey', 'year'], keep='last')
print(f"  - Fiscal year 중복 제거 후: {len(comp):,} ({n_before - len(comp):,} 제거)")

# 5. BE 산출: BE = ceq + txditc - dvp
# 원래 논문: BE = SEQ + TXDITC - PSTK (우선주)
# 현재 데이터: CEQ + TXDITC - DVP (우선주 배당금을 차감하여 우선주 가치 근사)
comp['txditc'] = comp['txditc'].fillna(0)
comp['dvp'] = comp['dvp'].fillna(0)
comp['BE'] = comp['ceq'] + comp['txditc'] - comp['dvp']

# BE <= 0 제외
n_before = len(comp)
comp = comp[comp['BE'] > 0]
print(f"  - BE > 0 필터 후: {len(comp):,} ({n_before - len(comp):,} 제거)")

# 6. Earnings 산출: E = ib + txdi - dvp
comp['txdi'] = comp['txdi'].fillna(0)
comp['dvp'] = comp['dvp'].fillna(0)
comp['E'] = comp['ib'] + comp['txdi'] - comp['dvp']

# CUSIP 6자리 추출
comp['cusip6'] = comp['cusip'].astype(str).str[:6]

print(f"\n  ✅ Compustat 최종 관측치: {len(comp):,}")
print(f"  기간: {comp['datadate'].min().strftime('%Y-%m')} ~ {comp['datadate'].max().strftime('%Y-%m')}")
print(f"  고유 gvkey 수: {comp['gvkey'].nunique():,}")

# BE 기초 통계
print(f"\n  BE 기초 통계:")
print(f"    mean:   {comp['BE'].mean():.2f}")
print(f"    median: {comp['BE'].median():.2f}")
print(f"    std:    {comp['BE'].std():.2f}")

# E 기초 통계
print(f"\n  E(Earnings) 기초 통계:")
print(f"    mean:   {comp['E'].mean():.2f}")
print(f"    median: {comp['E'].median():.2f}")
print(f"    E < 0 비율: {(comp['E'] < 0).mean():.1%}")

# ============================================================
# 1-3. F-F Factors 처리
# ============================================================
print("\n" + "=" * 70)
print("[1-3] Fama-French Factors 로드 중...")

# 헤더 행 건너뛰기 (처음 3줄은 설명)
ff_raw = pd.read_csv(FF_FILE, skiprows=3)
# 첫 번째 컬럼이 날짜 (YYYYMM 형식)
ff_raw.columns = ['date', 'Mkt-RF', 'SMB', 'HML', 'RF']

# 연간 데이터가 뒤에 섞여 있을 수 있으므로, 6자리(YYYYMM)인 행만 유지
ff_raw['date'] = ff_raw['date'].astype(str).str.strip()
ff = ff_raw[ff_raw['date'].str.len() == 6].copy()

# 숫자 변환
for col in ['Mkt-RF', 'SMB', 'HML', 'RF']:
    ff[col] = pd.to_numeric(ff[col], errors='coerce')

# 날짜 변환
ff['date'] = pd.to_datetime(ff['date'], format='%Y%m') + pd.offsets.MonthEnd(0)
ff['year'] = ff['date'].dt.year
ff['month'] = ff['date'].dt.month

# 퍼센트 → 소수점 변환
for col in ['Mkt-RF', 'SMB', 'HML', 'RF']:
    ff[col] = ff[col] / 100

# 시장 수익률 복원
ff['Rm'] = ff['Mkt-RF'] + ff['RF']

# 분석 기간 필터 (pre-ranking beta를 위해 1958-06부터 확보)
ff_analysis = ff[(ff['date'] >= '1958-06-01') & (ff['date'] <= '1990-12-31')].copy()

print(f"  ✅ F-F Factors 최종 관측치: {len(ff_analysis):,}")
print(f"  기간: {ff_analysis['date'].min().strftime('%Y-%m')} ~ {ff_analysis['date'].max().strftime('%Y-%m')}")
print(f"  RF 평균: {ff_analysis['RF'].mean():.4f} ({ff_analysis['RF'].mean()*12:.2%} 연환산)")
print(f"  Mkt-RF 평균: {ff_analysis['Mkt-RF'].mean():.4f} ({ff_analysis['Mkt-RF'].mean()*12:.2%} 연환산)")

# ============================================================
# 저장
# ============================================================
print("\n" + "=" * 70)
print("[저장]")

crsp.to_parquet(os.path.join(OUTPUT_DIR, '01_crsp_clean.parquet'), index=False)
print(f"  → 01_crsp_clean.parquet ({len(crsp):,} rows)")

comp.to_parquet(os.path.join(OUTPUT_DIR, '02_compustat_clean.parquet'), index=False)
print(f"  → 02_compustat_clean.parquet ({len(comp):,} rows)")

ff_analysis.to_parquet(os.path.join(OUTPUT_DIR, '03_ff_factors.parquet'), index=False)
print(f"  → 03_ff_factors.parquet ({len(ff_analysis):,} rows)")

print("\n✅ Phase 1 완료!")
