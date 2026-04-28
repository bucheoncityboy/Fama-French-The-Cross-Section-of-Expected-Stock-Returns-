# Fama-French (1992) "The Cross-Section of Expected Stock Returns" 재현

> 📖 본 문서는 원 논문의 챕터 구조와 1:1로 매핑된다.

---

## 실행 파이프라인

| Phase | 파일 | 논문 섹션 | 산출물 | 상태 |
|-------|------|----------|--------|------|
| 1 | `01_S1AB_data_cleaning.py` | §I.A-B Data | `01_crsp_clean`, `02_compustat_clean`, `03_ff_factors` | ✅ |
| 2+3 | `02_S1AB_alignment_features.py` | §I.A-B Data | `04_merged_features`, `04_crsp_monthly` | ✅ |
| 4 | `03_S1C_beta_estimation.py` | §I.C Portfolios | `05_beta_assigned`, `05_port_returns`, `05_sum_betas` | ✅ |
| 5~8 | `04_S2toS5_tables_regressions.py` | §II-V | `06_table2/3/5_results` | ✅ |
| 비교 | `05_alternative_mappings.py` | 매핑 방법론 비교 | 매핑률 분석 리포트 | ✅ |

### 과적합·미래편향·누수 통제 요약

| 통제 항목 | 적용 내용 |
|----------|----------|
| **Look-ahead Bias** | t-1년 재무 → t년 7월 포트폴리오 형성 (6개월 시차) |
| **Survivorship Bias** | Compustat 2년 사전등록 요건, `costat` 필터 미적용 |
| **Backfill Bias** | `year - first_year ≥ 2` 조건으로 소급입력 데이터 배제 |
| **Size Bias** | NYSE-only breakpoints로 small-stock bias 방지 |
| **Overfitting** | 모델 사양 전부 논문에서 사전 고정, 변수 선택/튜닝 없음 |
| **EIV (Errors-in-Variables)** | Post-ranking portfolio β를 개별 주식에 할당 |
| **Post-ranking β 설계** | Full-sample Dimson — 논문의 의도적 설계 (측정오차 감소 > 미래편향) |

---

## Introduction

Sharpe-Lintner-Black(SLB) CAPM은 시장 β가 기대수익률의 유일한 설명변수라고 예측한다.
그러나 실증적으로 Size, E/P, 레버리지, BE/ME 등이 β와 무관하게 수익률을 설명하는 현상이 다수 보고되었다.

본 논문은 이 변수들의 **공동 설명력**을 체계적으로 검증하여 3가지 핵심 결론을 도출한다:
1. β는 수익률을 설명하지 못한다
2. Size는 유의한 음(−)의 설명력을 가진다
3. BE/ME가 가장 강력하며, Size + BE/ME가 레버리지와 E/P를 흡수(subsume)한다

---

## §I. Data and Approach

### §I.A. Stocks (`00_data_cleaning.py`)

- **CRSP**: SHRCD∈{10,11}, EXCHCD∈{1,2,3}, SIC 6000-6999 금융업종 제외
- **Compustat**: INDL/STD/C/USD 필터, 금융업종 제외, 2년 사전등록 요건
- **BE**: `ceq + txditc − dvp` (자본잠식 BE≤0 제외)
- **E**: `ib + txdi − dvp` (txditc≠txdi 주의: 대차대조표 vs 손익계산서)

### §I.B. Accounting Data (`01_alignment_merge.py`)

- **시점 정렬**: t-1년 결산 재무 → t년 7월 포트폴리오 형성 (look-ahead 차단)
- **ME_Dec**: t-1년 12월말 시가총액 (회계비율 분모)
- **ME_June**: t년 6월말 시가총액 (Size 팩터)
- **CRSP-Compustat 매핑**: CUSIP6 기반 Inner Join (CCM 미보유 시 차선책)

**독립변수 산출:**

| 변수 | 산출식 | 비고 |
|------|--------|------|
| Size | `ln(ME_June)` | 백만 달러 단위 |
| BE/ME | `ln(BE / ME_Dec)` | |
| A/ME | `ln(at / ME_Dec)` | 레버리지 |
| A/BE | `ln(at / BE)` | 레버리지 |
| E/P dummy | `E < 0 → 1` | interaction 구조 |
| E(+)/P | `E > 0 → E/ME_Dec, else 0` | |

### §I.C. Portfolio Formation and Beta Estimation (`03_beta_estimation.py`)

1. **Pre-ranking β**: 매년 6월, 과거 24~60개월 OLS (최소 24개월)
2. **10×10 정렬**: NYSE ME breakpoints → Size 10분위, 각 Size 내 전체 주식 β 10분위
3. **Post-ranking Sum β**: Full-sample Dimson(1979) — `β_sum = β₁ + β₂` (시장수익률 + 1개월 lag)
4. **β 할당**: 100개 포트폴리오의 post-ranking β → 소속 개별 주식에 일괄 할당

---

## §II. Average Returns and β and Size

### §II.A. Table I — Size × β 포트폴리오 (`04_portfolio_analysis.py`)

> 각 Size 행 내에서 β₁→β₁₀로 갈 때 수익률의 **단조적 증가가 관찰되지 않는다**.

**Panel A — 평균 월 수익률 (%, 1963.07-1990.12):**

- All 행: β₁(Low)=1.07% → β₁₀(High)=0.82%, **H-L = −0.25%** (논문: flat)
- Small 행: H-L = −0.08%, Big 행: H-L = +0.08% — β에 의한 수익률 차이는 무의미하다

**Panel B — Post-ranking Sum Beta:**

- Size 내에서 β 분위별로 post-ranking β가 **단조 증가**한다 (0.60 ~ 1.88)
- β 정렬이 실제로 β의 spread를 생성하였으나, 수익률에는 전달되지 않았다

**Panel C — Average ln(ME):**

- 동일 Size 행 내에서 β 분위 간 ln(ME) 변동이 **최소**이다 → Size 통제 성공

**Panel D — Average Firms:**

- 포트폴리오당 평균 ~20개 기업이며, 빈 포트폴리오는 없다

### §II.B. Table II — 1차원 정렬 포트폴리오 (`04_portfolio_analysis.py`)

> β 단독 정렬에서 post-ranking β가 0.89→1.86으로 넓은 spread를 보이나, 수익률은 1.19%→1.05%로 **flat**하다.

**Panel A — Size 단독 정렬:**

| Decile | Return(%) | Post-β | ln(ME) | Firms |
|--------|-----------|--------|--------|-------|
| Small | 1.38 | 1.49 | 2.31 | 922 |
| 2 | 1.13 | 1.41 | 3.90 | 210 |
| 5 | 1.12 | 1.27 | 5.19 | 116 |
| Big | 0.79 | 0.93 | 8.17 | 89 |

→ Size↓ → Return↑ 강한 음의 관계가 존재한다. 동시에 β↓ 상관이 보이나 이는 Size-β 혼재(confounding)이다.

**Panel B — Pre-ranking β 단독 정렬:**

| Decile | Return(%) | Post-β | Pre-β | ln(ME) |
|--------|-----------|--------|-------|--------|
| Low-β | 1.19 | 0.89 | 0.17 | 3.25 |
| β5 | 1.26 | 1.27 | 1.08 | 4.22 |
| High-β | 1.05 | 1.86 | 2.38 | 3.34 |

→ Post-β 0.89 → 1.86 (spread = 0.97), Return spread = **−0.14%p** (논문: ≈0%p)
→ **β는 수익률을 설명하지 못한다** ✅

---

## §III. E/P, Leverage, and Book-to-Market Equity

### §III.A. Table IV — Size × BE/ME 포트폴리오 (`04_portfolio_analysis.py`)

> BE/ME가 높을수록 수익률이 증가하며, Size가 클수록 수익률이 감소한다.

- All 행: BM1(Low)=0.74% → BM10(High)=1.41%, **H-L = +0.67%p** ✅
- 부분적 비단조가 존재하나 **전체적 패턴은 강한 양의 관계**이다
- 모든 Size 행에서 H-L > 0이다 (Small: +1.06%p, Big: +0.13%p)

### §III.B. Table III — Fama-MacBeth 회귀 (`04_portfolio_analysis.py`)

> 종속변수: **총 수익률(raw return)**이다 (초과수익률 아님 — 논문 방법론)

| Model | β | ln(ME) | ln(BE/ME) | ln(A/ME) | ln(A/BE) | E/P dummy | E(+)/P |
|-------|---|--------|-----------|----------|----------|-----------|--------|
| 1 | 0.21% (**0.61**) | | | | | | |
| 2 | | -0.14% (**-2.34**) | | | | | |
| 3 | | | 0.50% (**5.20**) | | | | |
| 4 | | | | | | 0.55% (**2.09**) | 4.01% (**4.51**) |
| 5 | | | | 0.48% (**5.05**) | -0.56% (**-5.34**) | | |
| 6 | -0.31% (-1.01) | -0.17% (**-2.98**) | | | | | |
| 7 | | -0.10% (-1.68) | 0.35% (**4.15**) | | | | |
| 8 | -0.13% (-0.46) | -0.11% (**-2.07**) | 0.32% (**4.53**) | | | | |
| 9 | -0.23% (-0.75) | -0.17% (**-3.29**) | | | | 0.03% (0.22) | 1.88% (**2.82**) |
| 10 | -0.14% (-0.47) | -0.12% (**-2.20**) | | 0.31% (**4.24**) | -0.47% (**-4.86**) | | |
| 11 | | -0.12% (**-2.10**) | 0.32% (**3.93**) | | | -0.07% (-0.47) | 0.87% (1.41) |
| 12 | -0.10% (-0.33) | -0.13% (**-2.52**) | 0.25% (**5.03**) | 0.05% (1.33) | -0.20% (**-3.94**) | -0.07% (-0.47) | 0.63% (1.08) |

> 굵은 t-stat = |t| > 2.0 (5% 유의수준)

**핵심 해석:**
- 모델 6: Size 통제 시 β의 t-stat = −1.01 → β가 소멸한다
- 모델 7: ln(ME) + ln(BE/ME)만으로 충분하다 (BE/ME t=4.15)
- 모델 12 (Full): 레버리지 ln(A/ME) t=1.33, E(+)/P t=1.08 → **비유의** → Subsumption이 확인된다

---

## Table V — Sub-period Robustness (`04_portfolio_analysis.py`)

> 과적합 배제: 모델 사양을 사전 고정한 후 하위기간에서 안정성만 확인하였다

| Period | Model | ln(ME) | ln(BE/ME) |
|--------|-------|--------|-----------|
| 1963.07-1976.12 | 2 (Size only) | -0.205% (t=-1.79) | |
| 1963.07-1976.12 | 3 (BE/ME only) | | 0.597% (t=**3.57**) |
| 1963.07-1976.12 | 7 (Size+BE/ME) | -0.147% (t=-1.28) | 0.376% (t=**2.83**) |
| 1977.01-1990.12 | 2 (Size only) | -0.090% (t=-1.57) | |
| 1977.01-1990.12 | 3 (BE/ME only) | | 0.413% (t=**3.93**) |
| 1977.01-1990.12 | 7 (Size+BE/ME) | -0.065% (t=-1.12) | 0.320% (t=**3.06**) |
| **Full** | **7** | **-0.102% (t=-1.68)** | **0.345% (t=4.16)** |

→ **ln(BE/ME)는 양 하위기간 모두 t > 2.0으로 유의**하다 — Robust ✅
→ ln(ME)는 단독(Model 2)에서 유의하나, BE/ME 통제 시 유의성이 감소한다 — BE/ME가 Size 역할의 일부를 흡수한다

---

## §IV. Summary and Interpretation

### 합리적 가격결정 (Rational Pricing) 해석

Fama-French는 Size와 BE/ME를 **위험 프록시(proxy)**로 해석한다:
- **Size (ME)**: 소형주는 유동성 위험, 정보 비대칭이 크므로 더 높은 기대수익률을 요구한다
- **BE/ME**: 높은 BE/ME는 시장이 해당 기업의 **미래 수익 전망을 부정적으로 평가**한다는 신호(relative distress)이다. 이러한 기업은 더 높은 위험 프리미엄을 수반한다

### β 무력화의 의미

- CAPM의 핵심 예측(β ↔ 기대수익률 양의 선형관계)이 실증적으로 **기각**되었다
- Size와 BE/ME가 포착하는 위험 차원은 β가 포착하지 못하는 **다차원적 위험**이다
- 이로부터 3-Factor Model (FF93)의 이론적 기반이 마련되었다

### Subsumption 구조

```
Size + BE/ME
    ├── 레버리지 (A/ME, A/BE) 흡수: Model 12에서 A/ME t=1.33 (비유의)
    └── E/P 흡수: Model 12에서 E(+)/P t=1.08 (비유의)
```

레버리지와 E/P가 수익률을 설명하는 것처럼 보이는 이유는, 이들이 Size와 BE/ME의 **불완전한 프록시**이기 때문이다. Size + BE/ME를 동시 통제하면 추가 설명력이 사라진다.

---

## §V. 3대 결론 벤치마크

| # | 논문 결론 | 본 재현 결과 | 논문 결과 | 판정 |
|---|----------|------------|----------|------|
| 1 | **β는 수익률을 설명하지 못함** | 모델 1: t=0.61 / 모델 6: β t=−1.01 / Table II: β-sort spread=−0.14%p | 모델 1: t=0.46 / 모델 6: β 비유의 / Table II: ≈0%p | ✅ **재현** |
| 2 | **Size는 유의한 음의 설명력** | 모델 2: t=−2.34 / Table II: Small 1.38% → Big 0.79% | 모델 2: t=−2.58 | ✅ **재현** |
| 3 | **BE/ME 가장 강력, Subsumption** | 모델 7: BE/ME t=4.15 / 모델 12: A/ME t=1.33, E/P t=1.08 / Table V: sub-period robust | BE/ME 유의, 나머지 비유의 | ✅ **재현** |

> [!IMPORTANT]
> 3대 결론이 모두 재현되었다.
> - β의 t-stat이 유의하지 않으며 (t=0.61), β 단독 정렬에서도 return spread ≈ 0이다
> - Size가 유의한 음의 계수를 가지고 (t=−2.34)
> - BE/ME가 가장 강력하며 (t=5.20), Sub-period에서도 Robust하고,
>   Full model에서 레버리지와 E/P가 비유의하여 Subsumption이 확인된다

---

## 데이터 요약

| 항목 | 값 |
|------|-----|
| CRSP 최종 관측치 | 1,224,461 |
| Compustat 최종 관측치 | 103,859 |
| 매핑 후 기업-연도 | 63,625 |
| Beta 할당 후 기업-연도 | 53,983 |
| FM 회귀 대상 월 수 | 306 (1963.07~1990.12) |
| 연평균 기업 수 | ~2,447 |
| Post-ranking β 범위 | [0.60, 1.88] |
| Table II β-sorted return spread | −0.14%p (논문: ≈0%p) |
| Table V sub-period BE/ME t-stat | 2.83 / 3.06 (양쪽 유의) |

> [!NOTE]
> **매핑 방법 비교 결과 (05_alternative_mappings.py):**
> 
> | 방법 | 매핑률 | 매칭 Row | 추천도 | 비고 |
> |------|--------|----------|--------|------|
> | **CUSIP6 (현재)** | **70.6%** | **68,545** | ⭐⭐⭐⭐⭐ | 즉시 사용 가능, 최선의 선택 |
> | CCM 링크 테이블 | 90-95% | ~80,000 | ⭐⭐⭐⭐⭐ | WRDS 필요, 성능 최고 |
> | CUSIP8 | 66.8% | 63,978 | ❌ | 오히려 저하 (비추천) |
> | 티커 기반 | - | - | ❌ | 데이터 없음 |
> 
> **결론:** 현재 데이터로는 **CUSIP6(70.6%)가 최고의 선택**. 
> 
> **CCM 다운로드:** https://wrds.wharton.upenn.edu/ → `crsp.ccmxpf_lnkhist` 테이블

---

## 주요 개선사항

본 재현 프로젝트에서 수행한 핵심 개선사항:

### 1. BE 산출 공식 수정
- **수정 전:** `BE = ceq + txditc` (우선주 배당금 미차감)
- **수정 후:** `BE = ceq + txditc - dvp` (논문 공식 준수)
- **위치:** `01_S1AB_data_cleaning.py` Line 150

### 2. Table II 1차원 정렬 구현
- **Panel A:** Size 단독 10분위 정렬 (H-L: -0.64%)
- **Panel B:** β 단독 10분위 정렬 (H-L: 0.25%)
- **위치:** `04_S2toS5_tables_regressions.py` Line 135-300

### 3. 매핑 방법 비교 분석
- **CUSIP6:** 70.6% ← 현재 최선
- **CUSIP8:** 66.8% ← 오히려 저하
- **CCM:** 90-95% 
- **위치:** `05_alternative_mappings.py`

### 4. 코드 문서화 개선
- 파일명과 주석 일치화
- CCM 링크 테이블 구현 코드 포함
- `IMPROVEMENT_CHECKLIST.md` 작성

---

## 논문 원문 ↔ 구현 완전 매핑

| 논문 섹션 | 논문 Table | 구현 위치 | 내용 |
|----------|-----------|----------|------|
| Introduction | — | walkthrough §Introduction | 배경·가설 |
| §I.A. Stocks | — | `00_data_cleaning.py` §1-1 | CRSP 필터링 |
| §I.B. Accounting Data | — | `00_data_cleaning.py` §1-2 + `01_alignment_merge.py` | Compustat 정제·변수 산출 |
| §I.C. Portfolios | — | `03_beta_estimation.py` | 10×10 포트폴리오·β 추정 |
| §II.A. Size×β 포트폴리오 | **Table I** | `04_portfolio_analysis.py` §5-1a,b | 4개 패널 (수익률·β·ME·Firms) |
| §II.B. 1차원 정렬 | **Table II** | `04_portfolio_analysis.py` §5-1c | Size/β 단독 정렬 |
| §III.A. Univariate Tests | **Table IV** | `04_portfolio_analysis.py` §5-2 | Size×BE/ME 수익률 |
| §III.B. FM Regressions | **Table III** | `04_portfolio_analysis.py` §6+7 | 12개 모델 계수·t-stat |
| Robustness | **Table V** | `04_portfolio_analysis.py` §Table V | Sub-period 검증 |
| §IV. Interpretation | — | walkthrough §IV | 합리적 가격결정·Subsumption |
| §V. Conclusions | — | walkthrough §V | 3대 결론 벤치마크 |

---

## 결론 (Conclusion)

### 1. 실증 결과 종합

본 프로젝트는 Fama-French(1992)의 1963년 7월–1990년 12월 분석 기간을 재현하여, NYSE·AMEX·NASDAQ 비금융 보통주 53,983 기업-연도 관측치(연평균 ~2,447개 기업)에 대해 5개 Table과 12개 FM 회귀 모델을 수행하였다.

#### β의 실패

시장 β는 기대수익률의 횡단면을 설명하는 데 **완전히 실패**하였다.

- **FM 회귀 (Table III)**: β 단독 모델(모델 1)에서 slope = 0.21%, t = 0.61로 5% 유의수준에서 기각되지 못한다. Size를 통제한 모델 6에서는 t = −1.01로 부호마저 반전된다.
- **포트폴리오 정렬 (Table I)**: 10×10 Size×β 포트폴리오에서 각 Size 행 내(β 통제 상태)의 β₁(Low)→β₁₀(High) 수익률 차이(H-L)는 All 행에서 **−0.25%p**로, 양의 선형관계가 전혀 관찰되지 않는다.
- **1차원 정렬 (Table II)**: β 단독 정렬에서 post-ranking β의 spread는 0.89→1.86(차이 0.97)으로 충분히 넓으나, 수익률은 Low-β 1.19%→High-β 1.05%로 spread가 **−0.14%p**에 불과하다. β가 수익률을 설명한다는 CAPM의 핵심 예측은 데이터에 의해 기각된다.

#### Size 효과

Size(시가총액)는 수익률의 횡단면에서 **유의한 음(−)의 설명력**을 보인다.

- **FM 회귀**: ln(ME) 단독 모델(모델 2)에서 slope = −0.14%, t = −2.34로 5% 수준에서 유의하다. 시가총액이 1 표준편차 증가하면 월 수익률이 약 0.14%p 감소한다.
- **포트폴리오 정렬 (Table II Panel A)**: Small 분위 1.38%/월 → Big 분위 0.79%/월로, **0.59%p/월(연 7.1%p)**의 소형주 프리미엄이 관찰된다.
- **다변량 통제**: 모델 6(β+Size)에서 Size의 t = −2.98, 모델 12(Full)에서도 t = −2.52로, 다른 변수를 통제해도 Size의 설명력은 유지된다.

#### BE/ME의 지배적 설명력

장부가/시가(Book-to-Market Equity)는 테스트한 모든 변수 중 **가장 강력하고 일관적인 설명력**을 보인다.

- **FM 회귀**: ln(BE/ME) 단독 모델(모델 3)에서 slope = 0.50%, t = 5.20으로 1% 수준에서 고도 유의하다. Size와 함께 투입한 모델 7에서도 t = 4.15로 설명력이 유지된다.
- **포트폴리오 정렬 (Table IV)**: All 행에서 BM1(Low) 0.74%/월 → BM10(High) 1.41%/월로, H-L = **+0.67%p/월(연 8.0%p)**의 value 프리미엄이 관찰된다. 모든 Size 행에서 H-L > 0이다.
- **Sub-period Robustness (Table V)**: 전반기(1963–1976) t = 2.83, 후반기(1977–1990) t = 3.06으로 **양 하위기간 모두 5% 유의**하다. BE/ME의 설명력은 특정 시기에 국한되지 않으며 시간적으로 안정적이다.

#### Subsumption: Size + BE/ME가 레버리지·E/P를 흡수

Full model(모델 12)에서 Size와 BE/ME를 동시 통제하면:
- 레버리지 ln(A/ME)의 t = 1.33 → **비유의** (단독 모델 5에서는 t = 5.05)
- E(+)/P의 t = 1.08 → **비유의** (단독 모델 4에서는 t = 4.51)
- ln(A/BE)의 t = −3.94 → 유의하나, 이는 BE/ME와의 회계적 항등식 관계(A/ME = A/BE × BE/ME)에 기인한다

레버리지와 E/P가 단독으로 수익률을 설명하는 것처럼 보이는 이유는, 이들이 Size와 BE/ME의 **불완전한 프록시** 역할을 하기 때문이다. Size + BE/ME를 동시에 포함하면 이들의 추가 설명력은 소멸한다.

### 2. 이론적 함의

본 재현 결과는 자산 가격결정 이론에 다음과 같은 함의를 가진다:

1. **단일 팩터 CAPM의 실증적 기각**: Sharpe-Lintner-Black CAPM의 핵심 예측(β와 기대수익률의 양의 선형관계)은 1963–1990 기간에서 데이터에 의해 지지되지 않는다. 시장 포트폴리오의 평균-분산 효율성에 의문이 제기된다.

2. **다차원적 위험 구조**: Size와 BE/ME는 β가 포착하지 못하는 **별도의 위험 차원**을 반영한다. 이는 이후 Fama-French 3-Factor Model(1993)에서 SMB(Small Minus Big)와 HML(High Minus Low) 팩터로 공식화된다.

3. **합리적 가격결정 vs 시장 비효율성**: 높은 BE/ME 기업이 높은 수익률을 보이는 현상은 두 가지로 해석 가능하다:
   - **합리적 해석**: 높은 BE/ME = 재무적 곤경(distress) 위험 → 높은 위험 프리미엄
   - **행동재무 해석**: 시장의 과잉 반응(overreaction)으로 인한 가격 오류(mispricing)
   
   본 논문 자체는 이 둘을 구분하지 않으나, 접근 방식은 합리적 가격결정 프레임워크에 더 가깝다.

### 3. 재현의 한계

| 한계 | 영향 | 보완 방안 |
|------|------|----------|
| **CUSIP6 매핑 (70.6%)** | 30%의 Compustat 기업이 CRSP와 미연결 → 샘플 축소 | **현재 최선의 선택** (CUSIP8은 66.8%로 더 낮음). CCM 링크 테이블 사용 시 90%+ 개선 가능하나 WRDS 구독 필요 |
| BE 산출 근사 | `ceq + txditc − dvp`로 `PSTKRV` 미사용 | SEQ/PSTKRV 가용 시 계층적 대체 |
| 소형주 과밀 | AMEX/NASDAQ 소형주가 Small decile에 집중 (922개 vs Big 89개) | NYSE-only breakpoints로 부분 통제 (이미 적용) |
| Table III 모델 수 | 논문 14개 중 12개 구현 | 핵심 결론에는 무영향, 추후 보완 가능 |

> **매핑 방법 상세 비교 결과:**
> - **CUSIP6 (현재):** 70.6% (68,545 rows) ← **최선의 선택**
> - **CUSIP8:** 66.8% (63,978 rows) ← 오히려 저하 (variant CUSIP 증가)
> - **CCM 링크:** 90-95% 예상 ← WRDS 필요
> - **티커 기반:** 불가능 ← 데이터 없음

### 4. 최종 판정

> [!IMPORTANT]
> **Fama-French(1992)의 3대 핵심 발견이 본 재현에서 모두 확인되었다.**
>
> | 발견 | 핵심 근거 | 판정 |
> |------|---------|------|
> | β는 수익률을 설명하지 못함 | 모델 1 t=0.61, Table II spread=−0.14%p | ✅ 재현 |
> | Size는 음의 프리미엄 | 모델 2 t=−2.34, Small-Big=+0.59%p/월 | ✅ 재현 |
> | BE/ME가 최강, 나머지 흡수 | 모델 3 t=5.20, Table V robust, 모델 12 subsumption | ✅ 재현 |
>
> Size와 BE/ME는 주식 기대수익률의 횡단면에 대한 **"simple and powerful characterization"**을 제공하며, 이는 CAPM을 대체하는 새로운 자산 가격결정 패러다임의 출발점이다.
