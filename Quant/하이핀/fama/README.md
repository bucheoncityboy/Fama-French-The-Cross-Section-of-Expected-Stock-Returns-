# Fama-French (1992) Replication

Complete replication of Fama-French (1992) "The Cross-Section of Expected Stock Returns" with improvements.

## Three Core Conclusions Reproduced

| # | Conclusion | Result | Status |
|---|------------|--------|--------|
| 1 | Beta fails to explain returns | t=0.65, spread=0.25% | Replicated |
| 2 | Size has negative effect | t=-2.34, H-L=-0.64% | Replicated |
| 3 | BE/ME strongest | t=5.20, sub-period robust | Replicated |

## Quick Start

```bash
python 01_S1AB_data_cleaning.py
python 02_S1AB_alignment_features.py
python 03_S1C_beta_estimation.py
python 04_S2toS5_tables_regressions.py
```

## Structure

- `01_S1AB_data_cleaning.py` - Data cleaning
- `02_S1AB_alignment_features.py` - Feature engineering
- `03_S1C_beta_estimation.py` - Beta estimation
- `04_S2toS5_tables_regressions.py` - Analysis
- `walkthrough.md` - Detailed docs (Korean)
- `IMPROVEMENT_CHECKLIST.md` - Improvements made

## Improvements

1. BE calculation fixed: `ceq + txditc - dvp`
2. Table II univariate sorts added
3. Code documentation updated

## Results

**Table III - Fama-MacBeth Regressions:**
- Model 1 (Beta): 0.225% (t=0.65) - Insignificant
- Model 2 (Size): -0.142% (t=-2.34) - Significant
- Model 3 (BE/ME): 0.496% (t=5.20) - Strongest

**Table V - Sub-period Robustness:**
- 1963-1976: BE/ME t=2.83
- 1977-1990: BE/ME t=3.06

## Reference

Fama, E. F., & French, K. R. (1992). "The Cross-Section of Expected Stock Returns." *The Journal of Finance*, 47(2), 427-465.
