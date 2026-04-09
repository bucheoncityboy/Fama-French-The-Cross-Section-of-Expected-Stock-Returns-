"""
03_beta_estimation.py
Phase 4: 베타 추정 (Beta Estimation)
📖 논문 참조: Section I.B. Portfolio Formation and Estimation of Beta

Fama-French (1992) "The Cross-Section of Expected Stock Returns"
"""

import pandas as pd
import numpy as np
# scipy 미사용 — np.linalg.lstsq 직접 사용
import os
import warnings
warnings.filterwarnings('ignore')

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(BASE_DIR, 'output')

print("=" * 70)
print("Phase 4: 베타 추정")
print("=" * 70)

# ============================================================
# 데이터 로드
# ============================================================
print("\n[데이터 로드]")
crsp = pd.read_parquet(os.path.join(OUTPUT_DIR, '04_crsp_monthly.parquet'))
merged = pd.read_parquet(os.path.join(OUTPUT_DIR, '04_merged_features.parquet'))
ff = pd.read_parquet(os.path.join(OUTPUT_DIR, '03_ff_factors.parquet'))

print(f"  CRSP monthly: {len(crsp):,}")
print(f"  Merged features: {len(merged):,}")
print(f"  FF Factors: {len(ff):,}")

# CRSP에 FF Factors 병합 (RF, Rm, Mkt-RF)
crsp['date'] = pd.to_datetime(crsp['date'])
ff['date'] = pd.to_datetime(ff['date'])

# FF 테이블에서 전월 시장초과수익률을 사전 산출 (M-NEW-3 해결)
# 주식별 shift가 아닌 달력 기준 shift → 비거래월 결측 시에도 정확한 t-1 값 사용
ff_sorted = ff.sort_values('date').copy()
ff_sorted['mkt_excess_lag'] = ff_sorted['Mkt-RF'].shift(1)

crsp = crsp.merge(ff_sorted[['date', 'RF', 'Rm', 'Mkt-RF', 'mkt_excess_lag']], on='date', how='left')

# 초과 수익률 계산
crsp['excess_ret'] = crsp['RET'] - crsp['RF']
crsp['mkt_excess'] = crsp['Mkt-RF']

# ============================================================
# 4-1. Pre-ranking Beta
# ============================================================
print("\n[4-1] Pre-ranking Beta 추정")

# analysis period의 jdate 범위
# 논문: 1963.07 ~ 1990.12 → jdate 1963 ~ 1990
analysis_jdates = range(1963, 1991)

pre_betas = []
for jd in analysis_jdates:
    # jd년 6월 기준, 과거 24~60개월 수익률 데이터
    end_date = pd.Timestamp(f'{jd}-06-30')
    start_date_60 = end_date - pd.DateOffset(months=60)
    start_date_24 = end_date - pd.DateOffset(months=24)
    
    # 해당 기간의 CRSP 데이터
    mask = (crsp['date'] > start_date_60) & (crsp['date'] <= end_date)
    sub = crsp[mask].dropna(subset=['excess_ret', 'mkt_excess'])
    
    # PERMNO별 회귀
    for permno, grp in sub.groupby('PERMNO'):
        # Dimson Sum Beta: Ri = α + β1*Rm_t + β2*Rm_{t-1}
        grp = grp.sort_values('date')
        
        # mkt_excess_lag는 FF 테이블 기준 전월값 (주식별 shift 대신)
        valid = grp['mkt_excess_lag'].notna() & grp['excess_ret'].notna() & grp['mkt_excess'].notna()
        grp_valid = grp[valid]
        
        if len(grp_valid) < 24:  # 최소 24개월
            continue
        
        y_v = grp_valid['excess_ret'].values
        X_v = np.column_stack([
            np.ones(len(grp_valid)),
            grp_valid['mkt_excess'].values,
            grp_valid['mkt_excess_lag'].values
        ])
        
        # OLS: y = α + β1*Rm_t + β2*Rm_{t-1}
        try:
            coeffs = np.linalg.lstsq(X_v, y_v, rcond=None)[0]
            pre_beta = coeffs[1] + coeffs[2]
        except:
            continue
        
        pre_betas.append({
            'PERMNO': permno,
            'jdate': jd,
            'pre_beta': pre_beta,
            'n_months': len(grp_valid)
        })

pre_beta_df = pd.DataFrame(pre_betas)
print(f"  Pre-ranking beta 산출: {len(pre_beta_df):,} (기업-연도)")
print(f"  연도 범위: {pre_beta_df['jdate'].min()} ~ {pre_beta_df['jdate'].max()}")
print(f"  beta 분포: mean={pre_beta_df['pre_beta'].mean():.3f}, "
      f"std={pre_beta_df['pre_beta'].std():.3f}, "
      f"median={pre_beta_df['pre_beta'].median():.3f}")

# ============================================================
# 4-2. 10×10 포트폴리오 정렬
# ============================================================
print("\n[4-2] 10×10 포트폴리오 구성")

# merged에 pre_beta 병합
merged_beta = merged.merge(pre_beta_df[['PERMNO', 'jdate', 'pre_beta']], 
                           on=['PERMNO', 'jdate'], how='inner')
print(f"  Pre-beta 병합 후: {len(merged_beta):,}")

portfolio_assignments = []

for jd in analysis_jdates:
    yr_data = merged_beta[merged_beta['jdate'] == jd].copy()
    if len(yr_data) == 0:
        continue
    
    # NYSE 주식만의 ME 분위수로 Size Breakpoint
    nyse_data = yr_data[yr_data['EXCHCD'] == 1]
    if len(nyse_data) < 10:
        continue
    
    size_breakpoints = nyse_data['ME_June'].quantile(
        [i/10 for i in range(1, 10)]
    ).values
    
    # Size 10분위 할당 (0~9)
    yr_data['size_decile'] = np.digitize(yr_data['ME_June'], size_breakpoints)
    
    # 각 Size 그룹 내에서 β 10분위
    for sd in range(10):
        sd_data = yr_data[yr_data['size_decile'] == sd]
        sd_nyse = sd_data[sd_data['EXCHCD'] == 1]
        
        if len(sd_nyse) < 10:
            # β breakpoint를 만들 수 없으면 전체 주식으로 대체, 그것도 안되면 균등 분배
            if len(sd_data) >= 10:
                beta_breakpoints = sd_data['pre_beta'].quantile([i/10 for i in range(1, 10)]).values
                yr_data.loc[sd_data.index, 'beta_decile'] = np.digitize(sd_data['pre_beta'], beta_breakpoints)
            else:
                yr_data.loc[sd_data.index, 'beta_decile'] = np.floor(np.linspace(0, 9, len(sd_data))).astype(int)
            continue
        
        beta_breakpoints = sd_nyse['pre_beta'].quantile([i/10 for i in range(1, 10)]).values
        yr_data.loc[sd_data.index, 'beta_decile'] = np.digitize(
            sd_data['pre_beta'], beta_breakpoints
        )
    
    # 포트폴리오 ID: size_decile * 10 + beta_decile
    yr_data['port_id'] = yr_data['size_decile'] * 10 + yr_data['beta_decile'].astype(int)
    
    portfolio_assignments.append(yr_data[['PERMNO', 'jdate', 'port_id', 'size_decile', 'beta_decile']])

port_df = pd.concat(portfolio_assignments, ignore_index=True)
print(f"  포트폴리오 할당: {len(port_df):,} (기업-연도)")
print(f"  고유 포트폴리오 수: {port_df['port_id'].nunique()}")
print(f"  포트폴리오별 평균 기업 수: {port_df.groupby(['jdate', 'port_id'])['PERMNO'].count().mean():.1f}")

# ============================================================
# 4-3. Post-ranking Sum Beta (Full-sample, Dimson)
# ============================================================
print("\n[4-3] Post-ranking Sum Beta 추정 (Full-sample)")

# CRSP에 포트폴리오 할당 정보 병합
# 각 PERMNO-jdate의 port_id를 해당 보유 기간(jdate년 7월 1일 ~ jdate+1년 6월 30일)에 매핑
crsp_with_port = crsp.merge(port_df[['PERMNO', 'jdate', 'port_id']], 
                            on=['PERMNO', 'jdate'], how='inner')
crsp_with_port['hold_start'] = pd.to_datetime((crsp_with_port['jdate']).astype(str) + '-07-01')
crsp_with_port['hold_end'] = pd.to_datetime((crsp_with_port['jdate'] + 1).astype(str) + '-06-30')
crsp_with_port = crsp_with_port[
    (crsp_with_port['date'] >= crsp_with_port['hold_start']) &
    (crsp_with_port['date'] <= crsp_with_port['hold_end'])
]
crsp_with_port = crsp_with_port.dropna(subset=['RET', 'RF', 'mkt_excess'])

# 분석 기간 필터 (1963.07 ~ 1990.12)
crsp_analysis = crsp_with_port[
    (crsp_with_port['date'] >= '1963-07-01') &
    (crsp_with_port['date'] <= '1990-12-31')
].copy()

# 포트폴리오별 Equal-weighted 월별 수익률
port_returns = crsp_analysis.groupby(['date', 'port_id']).agg(
    port_ret=('RET', 'mean'),
    n_stocks=('PERMNO', 'count')
).reset_index()

# FF factors 병합
port_returns = port_returns.merge(ff[['date', 'RF', 'Mkt-RF', 'Rm']], on='date', how='left')
port_returns['port_excess'] = port_returns['port_ret'] - port_returns['RF']

# 전월 시장 초과수익률 (Dimson Sum Beta용)
ff_sorted = ff.sort_values('date')
ff_sorted['mkt_excess_lag'] = ff_sorted['Mkt-RF'].shift(1)
port_returns = port_returns.merge(
    ff_sorted[['date', 'mkt_excess_lag']], on='date', how='left'
)
port_returns = port_returns.dropna(subset=['mkt_excess_lag'])

# 각 포트폴리오에 대해 Dimson Sum Beta 추정
sum_betas = []
for pid in sorted(port_returns['port_id'].unique()):
    pdata = port_returns[port_returns['port_id'] == pid]
    if len(pdata) < 24:
        continue
    
    y = pdata['port_excess'].values
    X = np.column_stack([
        np.ones(len(pdata)),
        pdata['Mkt-RF'].values,
        pdata['mkt_excess_lag'].values
    ])
    
    # OLS: y = α + β₁*Mkt_t + β₂*Mkt_{t-1}
    try:
        coeffs = np.linalg.lstsq(X, y, rcond=None)[0]
        sum_beta = coeffs[1] + coeffs[2]  # β₁ + β₂
    except:
        continue
    
    sum_betas.append({
        'port_id': pid,
        'sum_beta': sum_beta,
        'beta1': coeffs[1],
        'beta2': coeffs[2],
        'n_months': len(pdata)
    })

sum_beta_df = pd.DataFrame(sum_betas)
print(f"  Post-ranking Sum Beta 산출: {len(sum_beta_df)} 포트폴리오")
print(f"  Sum Beta 분포: mean={sum_beta_df['sum_beta'].mean():.3f}, "
      f"std={sum_beta_df['sum_beta'].std():.3f}")
print(f"  min={sum_beta_df['sum_beta'].min():.3f}, max={sum_beta_df['sum_beta'].max():.3f}")

# ============================================================
# 4-4. Beta 할당
# ============================================================
print("\n[4-4] Beta 할당 (포트폴리오 → 개별 주식)")

# port_df에 sum_beta 병합
beta_assigned = port_df.merge(sum_beta_df[['port_id', 'sum_beta']], 
                              on='port_id', how='left')

# sum_beta가 없는 포트폴리오 제거
n_before = len(beta_assigned)
beta_assigned = beta_assigned.dropna(subset=['sum_beta'])
print(f"  Beta 할당: {len(beta_assigned):,} ({n_before - len(beta_assigned):,} 미할당 제거)")

# merged_beta에 sum_beta 병합
final = merged_beta.merge(
    beta_assigned[['PERMNO', 'jdate', 'sum_beta', 'port_id', 'size_decile', 'beta_decile']],
    on=['PERMNO', 'jdate'],
    how='inner'
)

print(f"\n  ✅ Beta 할당 완료: {len(final):,} (기업-연도)")
print(f"  Post-ranking β 분포:")
print(f"    mean:   {final['sum_beta'].mean():.4f}")
print(f"    std:    {final['sum_beta'].std():.4f}")
print(f"    p5:     {final['sum_beta'].quantile(0.05):.4f}")
print(f"    median: {final['sum_beta'].median():.4f}")
print(f"    p95:    {final['sum_beta'].quantile(0.95):.4f}")

# ============================================================
# 저장
# ============================================================
print("\n" + "=" * 70)
print("[저장]")

final.to_parquet(os.path.join(OUTPUT_DIR, '05_beta_assigned.parquet'), index=False)
print(f"  → 05_beta_assigned.parquet ({len(final):,} rows)")

# 포트폴리오 수익률도 저장 (Phase 5에서 사용)
port_returns.to_parquet(os.path.join(OUTPUT_DIR, '05_port_returns.parquet'), index=False)
print(f"  → 05_port_returns.parquet ({len(port_returns):,} rows)")

sum_beta_df.to_parquet(os.path.join(OUTPUT_DIR, '05_sum_betas.parquet'), index=False)
print(f"  → 05_sum_betas.parquet ({len(sum_beta_df)} rows)")

print(f"\n✅ Phase 4 완료!")
