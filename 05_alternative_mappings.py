"""
05_alternative_mappings.py
Alternative mapping strategies comparison:
- Alternative 1: CCM Link Table (90%+ mapping rate)
- Alternative 2: CUSIP8-based mapping (current implementation enhancement)
- Alternative 3: Ticker-based mapping (not available in current data)

This script compares all mapping alternatives and selects the best one.
"""

import pandas as pd
import numpy as np
import os
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(BASE_DIR, 'output')

print("=" * 70)
print("Alternative Mapping Strategies Comparison")
print("=" * 70)

# Load cleaned data
print("\n[Loading Data]")
comp = pd.read_parquet(os.path.join(OUTPUT_DIR, '02_compustat_clean.parquet'))
crsp = pd.read_parquet(os.path.join(OUTPUT_DIR, '01_crsp_clean.parquet'))

print(f"  Compustat: {len(comp):,} rows")
print(f"  CRSP: {len(crsp):,} rows")

# ============================================================
# BASELINE: Original CUSIP6 Mapping (for comparison)
# ============================================================
print("\n" + "=" * 70)
print("BASELINE: Original CUSIP6 Mapping")
print("=" * 70)

comp['cusip6'] = comp['cusip'].astype(str).str[:6]
crsp['CUSIP6'] = crsp['CUSIP'].astype(str).str[:6]

# Replicate original mapping logic
comp['jdate'] = comp['year'] + 1
crsp['jdate'] = np.where(crsp['month'] >= 7, crsp['year'], crsp['year'] - 1)

# 12월 ME
crsp_dec = crsp[crsp['month'] == 12][['PERMNO', 'year', 'ME_millions', 'CUSIP6']].copy()
crsp_dec = crsp_dec.rename(columns={'ME_millions': 'ME_Dec', 'year': 'dec_year'})

# CUSIP6 mapping
comp_cusip6 = comp.merge(
    crsp_dec[['PERMNO', 'CUSIP6', 'ME_Dec', 'dec_year']],
    left_on=['cusip6', 'year'],
    right_on=['CUSIP6', 'dec_year'],
    how='inner'
)
comp_cusip6 = comp_cusip6.sort_values(['PERMNO', 'jdate', 'datadate'])
comp_cusip6 = comp_cusip6.drop_duplicates(subset=['PERMNO', 'jdate'], keep='last')

n_comp_unique = comp['cusip6'].nunique()
n_matched_cusip6 = comp_cusip6['cusip6'].nunique()
cusip6_rate = n_matched_cusip6 / n_comp_unique * 100

print(f"\n  CUSIP6 Mapping Results:")
print(f"    - Total Compustat CUSIP6: {n_comp_unique:,}")
print(f"    - Matched CUSIP6: {n_matched_cusip6:,}")
print(f"    - Mapping Rate: {cusip6_rate:.1f}%")
print(f"    - Total matched rows: {len(comp_cusip6):,}")

# ============================================================
# ALTERNATIVE 2: CUSIP8-based Mapping
# ============================================================
print("\n" + "=" * 70)
print("ALTERNATIVE 2: CUSIP8-based Mapping")
print("=" * 70)

# Use first 8 digits of CUSIP
comp['cusip8'] = comp['cusip'].astype(str).str[:8]
crsp['CUSIP8'] = crsp['CUSIP'].astype(str).str[:8]

# 12월 ME with CUSIP8
crsp_dec_c8 = crsp[crsp['month'] == 12][['PERMNO', 'year', 'ME_millions', 'CUSIP8']].copy()
crsp_dec_c8 = crsp_dec_c8.rename(columns={'ME_millions': 'ME_Dec', 'year': 'dec_year'})

# CUSIP8 mapping
comp_cusip8 = comp.merge(
    crsp_dec_c8[['PERMNO', 'CUSIP8', 'ME_Dec', 'dec_year']],
    left_on=['cusip8', 'year'],
    right_on=['CUSIP8', 'dec_year'],
    how='inner'
)
comp_cusip8 = comp_cusip8.sort_values(['PERMNO', 'jdate', 'datadate'])
comp_cusip8 = comp_cusip8.drop_duplicates(subset=['PERMNO', 'jdate'], keep='last')

n_comp_unique_c8 = comp['cusip8'].nunique()
n_matched_cusip8 = comp_cusip8['cusip8'].nunique()
cusip8_rate = n_matched_cusip8 / n_comp_unique_c8 * 100

print(f"\n  CUSIP8 Mapping Results:")
print(f"    - Total Compustat CUSIP8: {n_comp_unique_c8:,}")
print(f"    - Matched CUSIP8: {n_matched_cusip8:,}")
print(f"    - Mapping Rate: {cusip8_rate:.1f}%")
print(f"    - Total matched rows: {len(comp_cusip8):,}")

# Compare CUSIP6 vs CUSIP8
additional_matches = len(comp_cusip8) - len(comp_cusip6)
print(f"\n  Comparison:")
print(f"    - Additional rows with CUSIP8: {additional_matches:,} ({additional_matches/len(comp_cusip6)*100:.1f}%)")

# ============================================================
# ALTERNATIVE 3: Ticker-based Mapping (NOT AVAILABLE)
# ============================================================
print("\n" + "=" * 70)
print("ALTERNATIVE 3: Ticker-based Mapping")
print("=" * 70)
print("\n  Status: NOT AVAILABLE")
print("  Reason: Current dataset does not contain 'ticker' field")
print("  Required: Compustat 'tic' column or CRSP 'TICKER' column")
print("  Alternative: Download ticker data from WRDS or other sources")

# ============================================================
# ALTERNATIVE 1: CCM Link Table (REQUIRES EXTERNAL DATA)
# ============================================================
print("\n" + "=" * 70)
print("ALTERNATIVE 1: CCM Link Table (WRDS)")
print("=" * 70)

print("\n  Implementation Code (requires CCM data):")
print("  " + "-" * 60)

ccm_code = '''
# Load CCM link table (download from WRDS: crsp.ccmxpf_linktable)
ccm_links = pd.read_csv('ccmxpf_linktable.csv')

# Filter link types
ccm_links = ccm_links[ccm_links['linktype'].isin(['LC', 'LU'])]
ccm_links = ccm_links[ccm_links['linkprim'] == 'P']  # Primary links only

# Convert dates
ccm_links['linkdt'] = pd.to_datetime(ccm_links['linkdt'])
ccm_links['linkenddt'] = pd.to_datetime(ccm_links['linkenddt'])

# Merge with Compustat
comp_ccm = comp.merge(
    ccm_links[['gvkey', 'lpermno', 'linkdt', 'linkenddt']],
    on='gvkey',
    how='left'
)

# Filter valid links (datadate within link period)
comp_ccm['datadate'] = pd.to_datetime(comp_ccm['datadate'])
comp_ccm = comp_ccm[
    (comp_ccm['datadate'] >= comp_ccm['linkdt']) &
    (comp_ccm['datadate'] <= comp_ccm['linkenddt'])
]

# Remove duplicates
comp_ccm = comp_ccm.sort_values(['gvkey', 'year', 'linkdt'])
comp_ccm = comp_ccm.drop_duplicates(subset=['gvkey', 'year'], keep='last')

# Merge with CRSP using PERMNO
comp_with_ccm = comp_ccm.merge(
    crsp_dec[['PERMNO', 'ME_Dec', 'dec_year']],
    left_on=['lpermno', 'year'],
    right_on=['PERMNO', 'dec_year'],
    how='inner'
)

# Expected mapping rate: 90-95%
'''

print(ccm_code)
print("  " + "-" * 60)

print("\n  Expected Results (based on literature):")
print("    - Mapping Rate: 90-95%")
print("    - Sample Size Increase: ~20-25%")
print("    - Data Source: WRDS crsp.ccmxpf_linktable")
print("    - Cost: WRDS subscription required")

# ============================================================
# COMPARISON SUMMARY
# ============================================================
print("\n" + "=" * 70)
print("COMPARISON SUMMARY")
print("=" * 70)

comparison_data = {
    'Method': [
        'CUSIP6 (Baseline)',
        'CUSIP8 (Alternative 2)',
        'CCM Link (Alternative 1)',
        'Ticker (Alternative 3)'
    ],
    'Mapping Rate': [
        f'{cusip6_rate:.1f}%',
        f'{cusip8_rate:.1f}%',
        '90-95% (expected)',
        'N/A (no data)'
    ],
    'Matched Rows': [
        f'{len(comp_cusip6):,}',
        f'{len(comp_cusip8):,}',
        '~80,000 (expected)',
        'N/A'
    ],
    'Implementation': [
        'Current',
        'Easy',
        'Medium (needs data)',
        'Hard (needs data)'
    ],
    'Cost': [
        'Free',
        'Free',
        'WRDS Subscription',
        'Data Purchase'
    ]
}

comparison_df = pd.DataFrame(comparison_data)
print("\n")
print(comparison_df.to_string(index=False))

# ============================================================
# RECOMMENDATION
# ============================================================
print("\n" + "=" * 70)
print("RECOMMENDATION")
print("=" * 70)

if cusip8_rate > cusip6_rate + 5:
    print(f"\n  ⭐ RECOMMENDED: CUSIP8-based Mapping")
    print(f"     - Mapping rate improved from {cusip6_rate:.1f}% to {cusip8_rate:.1f}%")
    print(f"     - Additional {additional_matches:,} observations")
    print(f"     - Easy implementation, no additional cost")
    
    # Save CUSIP8 version as recommended
    comp_cusip8.to_parquet(os.path.join(OUTPUT_DIR, '04_merged_features_cusip8.parquet'), index=False)
    print(f"\n  💾 Saved: 04_merged_features_cusip8.parquet ({len(comp_cusip8):,} rows)")
    
elif cusip8_rate > cusip6_rate:
    print(f"\n  ⭐ RECOMMENDED: CUSIP8-based Mapping (Marginal Improvement)")
    print(f"     - Mapping rate improved from {cusip6_rate:.1f}% to {cusip8_rate:.1f}%")
    print(f"     - Additional {additional_matches:,} observations")
    
else:
    print(f"\n  ⭐ RECOMMENDED: Stick with CUSIP6 (no significant improvement with CUSIP8)")
    print(f"     - CUSIP6 rate: {cusip6_rate:.1f}%")
    print(f"     - CUSIP8 rate: {cusip8_rate:.1f}%")

print("\n  📝 For maximum accuracy:")
print("     1. Use CCM Link Table if WRDS access available (90-95% mapping)")
print("     2. Otherwise, use CUSIP8 for slight improvement")
print("     3. Consider downloading ticker data for hybrid approach")

print("\n" + "=" * 70)
print("Comparison Complete!")
print("=" * 70)
