"""
04_S2toS5_tables_regressions.py
Phase 5: 포트폴리오 수익률 분석 (Portfolio Return Analysis)
📖 논문 참조: Section II + Section III.A
📖 산출물 → Table I, II, III, IV

Phase 6+7: Fama-MacBeth 횡단면 회귀 + 통계 검증
📖 논문 참조: Section III.B
📖 산출물 → Table V, VI

Fama-French (1992) "The Cross-Section of Expected Stock Returns"
"""

import pandas as pd
import numpy as np
from scipy import stats as sp_stats  # 현재 직접 미사용, 향후 확장용
import os
import warnings
warnings.filterwarnings('ignore')

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(BASE_DIR, 'output')

print("=" * 70)
print("Phase 5: 포트폴리오 수익률 분석")
print("=" * 70)

# ============================================================
# 데이터 로드
# ============================================================
crsp = pd.read_parquet(os.path.join(OUTPUT_DIR, '04_crsp_monthly.parquet'))
beta_data = pd.read_parquet(os.path.join(OUTPUT_DIR, '05_beta_assigned.parquet'))
ff = pd.read_parquet(os.path.join(OUTPUT_DIR, '03_ff_factors.parquet'))
port_returns = pd.read_parquet(os.path.join(OUTPUT_DIR, '05_port_returns.parquet'))
sum_beta_df = pd.read_parquet(os.path.join(OUTPUT_DIR, '05_sum_betas.parquet'))

crsp['date'] = pd.to_datetime(crsp['date'])

# 분석 기간 CRSP 필터
crsp_analysis = crsp[
    (crsp['date'] >= '1963-07-01') & (crsp['date'] <= '1990-12-31')
].copy()

# ============================================================
# 5-1. Size × β 포트폴리오 (Table I 재현)
# ============================================================
print("\n📖 [Table I] Size × β 포트폴리오 (10x10)")

# 포트폴리오별 평균 수익률
port_avg = port_returns.groupby('port_id').agg(
    avg_ret=('port_ret', 'mean'),
    n_months=('port_ret', 'count')
).reset_index()

port_avg['size_decile'] = port_avg['port_id'] // 10
port_avg['beta_decile'] = port_avg['port_id'] % 10

pivot = port_avg.pivot_table(values='avg_ret', index='size_decile', columns='beta_decile', aggfunc='mean') * 100
pivot['All'] = pivot.mean(axis=1)
pivot.loc['All'] = pivot.mean(axis=0)
pivot['H-L'] = pivot[9] - pivot[0]

size_labels = ['Small'] + [str(i) for i in range(2, 10)] + ['Big', 'All']
beta_labels = [f'β{i+1}' for i in range(10)] + ['All', 'H-L']
pivot.index = size_labels
pivot.columns = beta_labels

print("\n  Panel A — 평균 월 수익률 (%, 1963.07-1990.12):")
print(pivot.round(2).to_string())

# ============================================================
# 5-2. Table II: Size × BE/ME 포트폴리오
# ============================================================
print("\n\n📖 [Table II] Size × BE/ME 포트폴리오 평균 수익률")

stock_monthly = crsp_analysis.merge(
    beta_data[['PERMNO', 'jdate', 'ME_June', 'BEME', 'EXCHCD', 'sum_beta',
               'ln_ME', 'ln_BEME', 'ln_A_ME', 'ln_A_BE', 'EP_dummy', 'EP_positive', 'E']],
    on=['PERMNO', 'jdate'],
    how='inner',
    suffixes=('', '_annual')
)

beme_port_returns = []
for jd in range(1963, 1991):
    yr_data = stock_monthly[stock_monthly['jdate'] == jd].copy()
    if len(yr_data) == 0:
        continue
    
    # 보유기간 필터: jd년 7월 ~ jd+1년 6월 (H-NEW-2 해결)
    hold_start = pd.Timestamp(f'{jd}-07-01')
    hold_end = pd.Timestamp(f'{jd+1}-06-30')
    yr_data = yr_data[(yr_data['date'] >= hold_start) & (yr_data['date'] <= hold_end)]
    if len(yr_data) == 0:
        continue
    
    # 6월 시점 특성값 (시간순 정렬 후 첫 관측치 = 7월 = 포트폴리오 형성 직후)
    yr_data = yr_data.sort_values('date')
    chars = yr_data.groupby('PERMNO').first()[['ME_June', 'BEME', 'EXCHCD_annual']].reset_index()
    
    nyse = chars[chars['EXCHCD_annual'] == 1]
    if len(nyse) < 10:
        continue
    
    size_bp = nyse['ME_June'].quantile([i/10 for i in range(1, 10)]).values
    beme_bp = nyse['BEME'].dropna().quantile([i/10 for i in range(1, 10)]).values
    
    chars['size_d'] = np.digitize(chars['ME_June'], size_bp)
    chars['beme_d'] = np.digitize(chars['BEME'], beme_bp)
    chars['beme_port'] = chars['size_d'] * 10 + chars['beme_d']
    
    yr_monthly = yr_data.merge(chars[['PERMNO', 'beme_port', 'size_d', 'beme_d']], on='PERMNO')
    port_ret = yr_monthly.groupby(['date', 'beme_port']).agg(ret=('RET', 'mean')).reset_index()
    beme_port_returns.append(port_ret)

beme_all = pd.concat(beme_port_returns, ignore_index=True)
beme_avg = beme_all.groupby('beme_port')['ret'].mean().reset_index()
beme_avg['size_d'] = beme_avg['beme_port'] // 10
beme_avg['beme_d'] = beme_avg['beme_port'] % 10

pivot2 = beme_avg.pivot_table(values='ret', index='size_d', columns='beme_d') * 100
pivot2['All'] = pivot2.mean(axis=1)
pivot2.loc['All'] = pivot2.mean(axis=0)
pivot2['H-L'] = pivot2[9] - pivot2[0]

beme_col_labels = [f'BM{i+1}' for i in range(10)] + ['All', 'H-L']
pivot2.index = size_labels
pivot2.columns = beme_col_labels

print("\n  평균 월 수익률 (%, 1963.07-1990.12):")
print(pivot2.round(2).to_string())


# ============================================================
# 5-2b. Table II: 1차원 정렬 포트폴리오 (Size만, β만)
# ============================================================
print("\n\n📖 [Table II] 1차원 정렬 포트폴리오 평균 수익률")

# Panel A: Size 단독 10분위 정렬
size_only_returns = []
for jd in range(1963, 1991):
    yr_data = stock_monthly[stock_monthly['jdate'] == jd].copy()
    if len(yr_data) == 0:
        continue
    
    # 보유기간 필터
    hold_start = pd.Timestamp(f'{jd}-07-01')
    hold_end = pd.Timestamp(f'{jd+1}-06-30')
    yr_data = yr_data[(yr_data['date'] >= hold_start) & (yr_data['date'] <= hold_end)]
    if len(yr_data) == 0:
        continue
    
    yr_data = yr_data.sort_values('date')
    first_obs = yr_data.groupby('PERMNO').first().reset_index()
    chars = first_obs[['PERMNO', 'ME_June', 'sum_beta', 'ln_ME', 'EXCHCD']].copy()
    
    nyse = chars[chars['EXCHCD'] == 1]
    if len(nyse) < 10:
        continue
    
    size_bp = nyse['ME_June'].quantile([i/10 for i in range(1, 10)]).values
    chars['size_d'] = np.digitize(chars['ME_June'], size_bp)
    
    # yr_monthly에 size_d 병합
    yr_monthly = yr_data.merge(chars[['PERMNO', 'size_d']], on='PERMNO')
    port_ret = yr_monthly.groupby(['date', 'size_d']).agg(
        ret=('RET', 'mean')
    ).reset_index()
    port_ret['jdate'] = jd
    size_only_returns.append(port_ret)

size_only_all = pd.concat(size_only_returns, ignore_index=True)
size_only_avg = size_only_all.groupby('size_d')['ret'].mean().reset_index()

# Post-ranking beta와 ln_ME 계산 (별도로)
size_chars = stock_monthly.groupby('PERMNO').first()[['sum_beta', 'ln_ME', 'EXCHCD']].reset_index()
size_portfolio_chars = []
for jd in range(1963, 1991):
    yr_data = stock_monthly[stock_monthly['jdate'] == jd].copy()
    if len(yr_data) == 0:
        continue
    first_obs = yr_data.groupby('PERMNO').first().reset_index()
    chars = first_obs[['PERMNO', 'ME_June', 'sum_beta', 'ln_ME', 'EXCHCD']].copy()
    
    nyse = chars[chars['EXCHCD'] == 1]
    if len(nyse) < 10:
        continue
    
    size_bp = nyse['ME_June'].quantile([i/10 for i in range(1, 10)]).values
    chars['size_d'] = np.digitize(chars['ME_June'], size_bp)
    size_portfolio_chars.append(chars)

if size_portfolio_chars:
    size_chars_all = pd.concat(size_portfolio_chars, ignore_index=True)
    size_beta_lnme = size_chars_all.groupby('size_d')[['sum_beta', 'ln_ME']].mean().reset_index()
    size_only_avg = size_only_avg.merge(size_beta_lnme, on='size_d', how='left')

print("\n  Panel A — Size 단독 정렬 평균 월 수익률 (%, 1963.07-1990.12):")
print(f"  {'Decile':<8} {'Return(%)':>10} {'Post-β':>8} {'ln(ME)':>8}")
print("  " + "-" * 40)
for _, row in size_only_avg.iterrows():
    decile = int(row['size_d'])
    label = ['Small', '2', '3', '4', '5', '6', '7', '8', '9', 'Big'][decile if decile < 10 else 9]
    avg_beta = row.get('sum_beta', np.nan)
    avg_lnme = row.get('ln_ME', np.nan)
    print(f"  {label:<8} {row['ret']*100:>10.2f} {avg_beta:>8.2f} {avg_lnme:>8.2f}")

# Panel B: β 단독 10분위 정렬
beta_only_returns = []
for jd in range(1963, 1991):
    yr_data = stock_monthly[stock_monthly['jdate'] == jd].copy()
    if len(yr_data) == 0:
        continue
    
    # 보유기간 필터
    hold_start = pd.Timestamp(f'{jd}-07-01')
    hold_end = pd.Timestamp(f'{jd+1}-06-30')
    yr_data = yr_data[(yr_data['date'] >= hold_start) & (yr_data['date'] <= hold_end)]
    if len(yr_data) == 0:
        continue
    
    yr_data = yr_data.sort_values('date')
    first_obs = yr_data.groupby('PERMNO').first().reset_index()
    chars = first_obs[['PERMNO', 'ME_June', 'sum_beta', 'ln_ME', 'EXCHCD']].copy()
    
    nyse = chars[chars['EXCHCD'] == 1]
    if len(nyse) < 10:
        continue
    
    # 전체 주식의 β 분위수 (NYSE breakpoints)
    beta_bp = nyse['sum_beta'].quantile([i/10 for i in range(1, 10)]).values
    chars['beta_d'] = np.digitize(chars['sum_beta'], beta_bp)
    
    yr_monthly = yr_data.merge(chars[['PERMNO', 'beta_d']], on='PERMNO')
    port_ret = yr_monthly.groupby(['date', 'beta_d']).agg(
        ret=('RET', 'mean')
    ).reset_index()
    port_ret['jdate'] = jd
    beta_only_returns.append(port_ret)

beta_only_all = pd.concat(beta_only_returns, ignore_index=True)
beta_only_avg = beta_only_all.groupby('beta_d')['ret'].mean().reset_index()

# Post-ranking beta와 ln_ME 계산 (별도로)
beta_portfolio_chars = []
for jd in range(1963, 1991):
    yr_data = stock_monthly[stock_monthly['jdate'] == jd].copy()
    if len(yr_data) == 0:
        continue
    first_obs = yr_data.groupby('PERMNO').first().reset_index()
    chars = first_obs[['PERMNO', 'ME_June', 'sum_beta', 'ln_ME', 'EXCHCD']].copy()
    
    nyse = chars[chars['EXCHCD'] == 1]
    if len(nyse) < 10:
        continue
    
    beta_bp = nyse['sum_beta'].quantile([i/10 for i in range(1, 10)]).values
    chars['beta_d'] = np.digitize(chars['sum_beta'], beta_bp)
    beta_portfolio_chars.append(chars)

if beta_portfolio_chars:
    beta_chars_all = pd.concat(beta_portfolio_chars, ignore_index=True)
    beta_beta_lnme = beta_chars_all.groupby('beta_d')[['sum_beta', 'ln_ME']].mean().reset_index()
    beta_only_avg = beta_only_avg.merge(beta_beta_lnme, on='beta_d', how='left')

print("\n  Panel B — β 단독 정렬 평균 월 수익률 (%, 1963.07-1990.12):")
print(f"  {'Decile':<8} {'Return(%)':>10} {'Post-β':>8} {'ln(ME)':>8}")
print("  " + "-" * 40)
for _, row in beta_only_avg.iterrows():
    decile = int(row['beta_d'])
    label = ['Low-β', '2', '3', '4', '5', '6', '7', '8', '9', 'High-β'][decile if decile < 10 else 9]
    avg_beta = row.get('sum_beta', np.nan)
    avg_lnme = row.get('ln_ME', np.nan)
    print(f"  {label:<8} {row['ret']*100:>10.2f} {avg_beta:>8.2f} {avg_lnme:>8.2f}")

# H-L 계산
if len(size_only_avg) > 0:
    size_small = size_only_avg[size_only_avg['size_d'] == size_only_avg['size_d'].min()]['ret'].values
    size_big = size_only_avg[size_only_avg['size_d'] == size_only_avg['size_d'].max()]['ret'].values
    if len(size_small) > 0 and len(size_big) > 0:
        size_hl = (size_big[0] - size_small[0]) * 100
        print(f"\n  Size H-L (Big - Small): {size_hl:.2f}%")

if len(beta_only_avg) > 0:
    beta_low = beta_only_avg[beta_only_avg['beta_d'] == beta_only_avg['beta_d'].min()]['ret'].values
    beta_high = beta_only_avg[beta_only_avg['beta_d'] == beta_only_avg['beta_d'].max()]['ret'].values
    if len(beta_low) > 0 and len(beta_high) > 0:
        beta_hl = (beta_high[0] - beta_low[0]) * 100
        print(f"  β H-L (High - Low): {beta_hl:.2f}%")


# ============================================================
# 5-3. Table III: Size × Leverage (A/ME) 포트폴리오
# ============================================================
print("\n\n📖 [Table III] Size × Leverage(A/ME) 포트폴리오 평균 수익률")

stock_monthly['A_ME'] = np.exp(stock_monthly['ln_A_ME'])

ame_port_returns = []
for jd in range(1963, 1991):
    yr_data = stock_monthly[stock_monthly['jdate'] == jd].copy()
    if len(yr_data) == 0: continue
    
    # 보유기간 필터
    hold_start = pd.Timestamp(f'{jd}-07-01')
    hold_end = pd.Timestamp(f'{jd+1}-06-30')
    yr_data = yr_data[(yr_data['date'] >= hold_start) & (yr_data['date'] <= hold_end)]
    if len(yr_data) == 0: continue
    
    yr_data = yr_data.sort_values('date')
    chars = yr_data.groupby('PERMNO').first()[['ME_June', 'A_ME', 'EXCHCD_annual']].reset_index()
    
    nyse = chars[chars['EXCHCD_annual'] == 1]
    if len(nyse) < 10: continue
    
    size_bp = nyse['ME_June'].quantile([i/10 for i in range(1, 10)]).values
    ame_bp = nyse['A_ME'].dropna().quantile([i/10 for i in range(1, 10)]).values
    
    chars['size_d'] = np.digitize(chars['ME_June'], size_bp)
    chars['ame_d'] = np.digitize(chars['A_ME'], ame_bp)
    chars['ame_port'] = chars['size_d'] * 10 + chars['ame_d']
    
    yr_monthly = yr_data.merge(chars[['PERMNO', 'ame_port', 'size_d', 'ame_d']], on='PERMNO')
    port_ret = yr_monthly.groupby(['date', 'ame_port']).agg(ret=('RET', 'mean')).reset_index()
    ame_port_returns.append(port_ret)

ame_all = pd.concat(ame_port_returns, ignore_index=True)
ame_avg = ame_all.groupby('ame_port')['ret'].mean().reset_index()
ame_avg['size_d'] = ame_avg['ame_port'] // 10
ame_avg['ame_d'] = ame_avg['ame_port'] % 10

pivot3 = ame_avg.pivot_table(values='ret', index='size_d', columns='ame_d') * 100
pivot3['All'] = pivot3.mean(axis=1)
pivot3.loc['All'] = pivot3.mean(axis=0)
pivot3['H-L'] = pivot3[9] - pivot3[0]

ame_col_labels = [f'Lev{i+1}' for i in range(10)] + ['All', 'H-L']
pivot3.index = size_labels
pivot3.columns = ame_col_labels

print("\n  평균 월 수익률 (%, 1963.07-1990.12):")
print(pivot3.round(2).to_string())


# ============================================================
# 5-4. Table IV: Size × E/P 포트폴리오
# ============================================================
print("\n\n📖 [Table IV] Size × E/P 포트폴리오 평균 수익률")

ep_port_returns = []
for jd in range(1963, 1991):
    yr_data = stock_monthly[stock_monthly['jdate'] == jd].copy()
    if len(yr_data) == 0: continue
    
    # 보유기간 필터
    hold_start = pd.Timestamp(f'{jd}-07-01')
    hold_end = pd.Timestamp(f'{jd+1}-06-30')
    yr_data = yr_data[(yr_data['date'] >= hold_start) & (yr_data['date'] <= hold_end)]
    if len(yr_data) == 0: continue
    
    yr_data = yr_data.sort_values('date')
    chars = yr_data.groupby('PERMNO').first()[['ME_June', 'EP_positive', 'E', 'EXCHCD_annual']].reset_index()
    
    nyse = chars[chars['EXCHCD_annual'] == 1]
    if len(nyse) < 10: continue
    
    size_bp = nyse['ME_June'].quantile([i/10 for i in range(1, 10)]).values
    
    # E/P 정렬: E < 0은 그룹 0, E > 0은 NYSE breakpoints로 10분위
    nyse_pos = nyse[nyse['E'] > 0]
    if len(nyse_pos) < 10: continue
    ep_bp = nyse_pos['EP_positive'].quantile([i/10 for i in range(1, 10)]).values
    
    chars['size_d'] = np.digitize(chars['ME_June'], size_bp)
    
    # E/P 그룹: E < 0은 0, E > 0은 1~10
    chars['ep_d'] = np.where(chars['E'] <= 0, 0, np.digitize(chars['EP_positive'], ep_bp) + 1)
    chars['ep_port'] = chars['size_d'] * 100 + chars['ep_d']
    
    yr_monthly = yr_data.merge(chars[['PERMNO', 'ep_port', 'size_d', 'ep_d']], on='PERMNO')
    port_ret = yr_monthly.groupby(['date', 'ep_port']).agg(ret=('RET', 'mean')).reset_index()
    ep_port_returns.append(port_ret)

ep_all = pd.concat(ep_port_returns, ignore_index=True)
ep_avg = ep_all.groupby('ep_port')['ret'].mean().reset_index()
ep_avg['size_d'] = ep_avg['ep_port'] // 100
ep_avg['ep_d'] = ep_avg['ep_port'] % 100

pivot4 = ep_avg.pivot_table(values='ret', index='size_d', columns='ep_d') * 100
pivot4['All'] = pivot4.mean(axis=1)
pivot4.loc['All'] = pivot4.mean(axis=0)

ep_col_labels = ['E<0'] + [f'E/P {i}' for i in range(1, 11)] + ['All']
pivot4.index = size_labels
pivot4.columns = ep_col_labels[:len(pivot4.columns)]

print("\n  평균 월 수익률 (%, 1963.07-1990.12):")
print(pivot4.round(2).to_string())

# ============================================================
# Phase 6+7: Fama-MacBeth 횡단면 회귀
# ============================================================
print("\n" + "=" * 70)
print("Phase 6+7: Fama-MacBeth 횡단면 회귀 + 통계 검증")
print("📖 산출물 → 논문 Table V, VI")
print("=" * 70)

models = {
    1: ['sum_beta'],
    2: ['ln_ME'],
    3: ['ln_BEME'],
    4: ['EP_dummy', 'EP_positive'],
    5: ['ln_A_ME', 'ln_A_BE'],
    6: ['sum_beta', 'ln_ME'],
    7: ['ln_ME', 'ln_BEME'],
    8: ['sum_beta', 'ln_ME', 'ln_BEME'],
    9: ['sum_beta', 'ln_ME', 'EP_dummy', 'EP_positive'],
    10: ['sum_beta', 'ln_ME', 'ln_A_ME', 'ln_A_BE'],
    11: ['ln_ME', 'ln_BEME', 'EP_dummy', 'EP_positive'],
    12: ['sum_beta', 'ln_ME', 'ln_BEME', 'EP_dummy', 'EP_positive'],
    13: ['ln_ME', 'ln_A_ME', 'ln_A_BE'],  
    14: ['sum_beta', 'ln_ME', 'ln_BEME', 'ln_A_ME', 'ln_A_BE', 'EP_dummy', 'EP_positive'],
}

dates = sorted(stock_monthly['date'].unique())
all_results = {m: [] for m in models}

for dt in dates:
    month_data = stock_monthly[stock_monthly['date'] == dt].copy()
    month_data = month_data.drop_duplicates(subset=['PERMNO'])
    
    if len(month_data) < 30: continue
    y = month_data['RET'].values
    
    for model_id, vars_list in models.items():
        X_cols = month_data[vars_list].values
        valid = ~np.isnan(y) & ~np.any(np.isnan(X_cols), axis=1)
        if valid.sum() < 30: continue
        
        y_valid = y[valid]
        X_valid = np.column_stack([np.ones(valid.sum()), X_cols[valid]])
        
        try:
            coeffs = np.linalg.lstsq(X_valid, y_valid, rcond=None)[0]
            result = {'date': dt, 'intercept': coeffs[0]}
            for i, var in enumerate(vars_list):
                result[var] = coeffs[i + 1]
            result['n_stocks'] = valid.sum()
            result['r2'] = 1 - np.sum((y_valid - X_valid @ coeffs)**2) / np.sum((y_valid - y_valid.mean())**2)
            all_results[model_id].append(result)
        except:
            pass

print("\n📖 [Table V] Fama-MacBeth 14 Models (리스크 프리미엄 및 t-통계량)")
all_vars = ['sum_beta', 'ln_ME', 'ln_BEME', 'ln_A_ME', 'ln_A_BE', 'EP_dummy', 'EP_positive']
var_labels = ['β', 'ln(ME)', 'ln(BE/ME)', 'ln(A/ME)', 'ln(A/BE)', 'E/P dummy', 'E(+)/P']

print("\n" + "=" * 110)
print(f"{'Model':>6}  ", end="")
for label in var_labels:
    print(f"{'':>2}{label:>12}", end="")
print(f"  {'R²':>6}  {'N':>6}")
print("-" * 110)

def newey_west_tstat(series, lag=6):
    """Newey-West HAC t-statistic. lag=6은 int(0.75*T^(1/3)) ≈ 5.2에서 반올림 (T≈330)"""
    T = len(series)
    mean = series.mean()
    if T == 0: return 0
    demeaned = series - mean
    gamma_0 = np.sum(demeaned**2) / T
    nw_var = gamma_0
    for j in range(1, lag + 1):
        weight = 1 - j / (lag + 1)
        gamma_j = np.sum(demeaned[j:] * demeaned[:-j]) / T
        nw_var += 2 * weight * gamma_j
    nw_se = np.sqrt(nw_var / T) if nw_var > 0 else 1
    return mean / nw_se

for model_id, vars_list in models.items():
    if len(all_results[model_id]) == 0: continue
    results_df = pd.DataFrame(all_results[model_id])
    T = len(results_df)
    
    print(f"  {model_id:>3}   ", end="")
    for var, label in zip(all_vars, var_labels):
        if var in vars_list:
            gamma_series = results_df[var]
            gamma_mean = gamma_series.mean()
            t_stat = gamma_mean / (gamma_series.std() / np.sqrt(T)) if gamma_series.std() > 0 else 0
            print(f"  {gamma_mean*100:>6.3f}({t_stat:>5.2f})", end="")
        else:
            print(f"{'':>15}", end="")
    avg_r2 = results_df['r2'].mean()
    avg_n = results_df['n_stocks'].mean()
    print(f"  {avg_r2:>5.3f}  {avg_n:>5.0f}")


print("\n" + "=" * 70)
print("📖 [Table VI] Sub-period Fama-MacBeth 회귀 (Robustness)")

sub_periods = {
    '1963.07-1976.12': ('1963-07-01', '1976-12-31'),
    '1977.01-1990.12': ('1977-01-01', '1990-12-31'),
    'Full: 1963-1990': ('1963-07-01', '1990-12-31'),
}
sub_models = {
    7: ['ln_ME', 'ln_BEME'],
    8: ['sum_beta', 'ln_ME', 'ln_BEME'],  # 논문 Table VI Model (b)
}

for pname, (s, e) in sub_periods.items():
    pdata = stock_monthly[(stock_monthly['date'] >= s) & (stock_monthly['date'] <= e)]
    pdates = sorted(pdata['date'].unique())
    print(f"\n  === {pname} ===")
    for mid, mvars in sub_models.items():
        gammas = {v: [] for v in mvars}
        for dt in pdates:
            md = pdata[pdata['date'] == dt].drop_duplicates(subset=['PERMNO'])
            if len(md) < 30: continue
            y = md['RET'].values
            Xc = md[mvars].values
            valid = ~np.isnan(y) & ~np.any(np.isnan(Xc), axis=1)
            if valid.sum() < 30: continue
            Xv = np.column_stack([np.ones(valid.sum()), Xc[valid]])
            try:
                co = np.linalg.lstsq(Xv, y[valid], rcond=None)[0]
                for i, v in enumerate(mvars):
                    gammas[v].append(co[i+1])
            except:
                pass
        if len(gammas[mvars[0]]) > 0:
            T = len(gammas[mvars[0]])
            parts = [f"{v}: {np.mean(gammas[v])*100:.3f}% (t={np.mean(gammas[v])/(np.std(gammas[v])/np.sqrt(T)):.2f})" for v in mvars]
            print(f"    Model {mid}: {', '.join(parts)}")


print("\n" + "=" * 70)
print("[저장]")

table3_rows = []
for model_id, vars_list in models.items():
    if len(all_results[model_id]) == 0: continue
    results_df = pd.DataFrame(all_results[model_id])
    T = len(results_df)
    row = {'model': model_id}
    for var in all_vars:
        if var in vars_list:
            gamma = results_df[var]
            row[f'{var}_coef'] = gamma.mean()
            row[f'{var}_tstat'] = gamma.mean() / (gamma.std() / np.sqrt(T))
            row[f'{var}_nw_tstat'] = newey_west_tstat(gamma.values, lag=6)
    row['avg_r2'] = results_df['r2'].mean()
    row['avg_n'] = results_df['n_stocks'].mean()
    table3_rows.append(row)

table3 = pd.DataFrame(table3_rows)
table3.to_parquet(os.path.join(OUTPUT_DIR, '06_table5_results.parquet'), index=False)
print(f"  → 06_table5_results.parquet ({len(table3)} models)")

print(f"\n✅ Phase 5+6+7 완료!")
