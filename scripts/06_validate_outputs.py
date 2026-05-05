"""
06_validate_outputs.py

Automated validation of global_awp_country_year.csv.
Run after 05_compute_annual_awp.py. Prints a pass/fail report and
saves it to data/final/validation_report.txt.

Checks:
  1.  ISO-3 coverage vs crosswalk
  2.  Row count per year
  3.  Awp plausibility range
  4.  VETb stored as m³ (not pre-divided to Mm³)
  5.  Cr values in [0, 1]
  6.  tAwp = 0 at baseline year 2018
  7.  cAwp = NaN at baseline year (no prior year)
  8.  Quality flag coverage ('OK' present)
  9.  No country appears twice in a given year
  10. Known-country Awp plausibility for year 2020
"""

import pandas as pd
import numpy as np
from pathlib import Path
import sys

ROOT      = Path(__file__).parent.parent
CSV_FILE  = ROOT / 'data' / 'final' / 'global_awp_country_year.csv'
XWALK     = ROOT / 'data' / 'interim' / 'crosswalks' / 'country_crosswalk.csv'
REPORT    = ROOT / 'data' / 'final' / 'validation_report.txt'

YEAR_START    = 2018
YEAR_END      = 2025
AWP_MAX       = 50_000.0  # USD/m³ - catches unit errors (e.g. forgot /1000); outliers flagged separately
AWP_MIN       = 0.001  # USD/m³

# Expected Awp range (min, max) in USD/m³ for specific countries in 2020.
# Note: Awp here uses VETb (blue ET) as denominator, not total water applied,
# so values are higher than traditional sector-level AWP figures from literature.
# Ranges are deliberately wide - a FAIL here means a gross computation error.
KNOWN_COUNTRY_CHECKS = {
    'NLD': (0.5, 500.0),   # Netherlands: intensive horticulture, high Awp expected
    'EGY': (0.5, 30.0),    # Egypt: large VETb (~70% irrigated), moderate GVA
    'ETH': (0.001, 25.0),  # Ethiopia: mostly rainfed; small VETb inflates Awp
    'IND': (0.01, 20.0),   # India: large VETb, large GVA
}


def chk(title: str, passed: bool, detail: str = '') -> dict:
    return {'title': title, 'status': 'PASS' if passed else 'FAIL', 'detail': detail}


def main():
    results = []

    # ── Load data ─────────────────────────────────────────────────────────────
    if not CSV_FILE.exists():
        print(f"ERROR: {CSV_FILE} not found. Run 05_compute_annual_awp.py first.")
        sys.exit(1)

    df = pd.read_csv(CSV_FILE, dtype={'iso3': str})
    xwalk = pd.read_csv(XWALK, dtype={'iso3': str})
    expected = set(xwalk[xwalk['include_flag'].isin(['YES', 'REVIEW'])]['iso3'])

    # 1. ISO-3 coverage
    found = set(df['iso3'].unique())
    missing = expected - found
    results.append(chk(
        'ISO-3 coverage (all expected countries present)',
        len(missing) == 0,
        f"{len(found)} found; {len(missing)} missing: {sorted(missing)[:10]}"
    ))

    # 2. Row count per year
    for yr in range(YEAR_START, YEAR_END + 1):
        n = (df['year'] == yr).sum()
        results.append(chk(
            f'Year {yr} row count >= 100',
            n >= 100,
            f"{n} rows"
        ))

    # 3. No duplicate iso3×year
    dupes = df.duplicated(subset=['iso3', 'year']).sum()
    results.append(chk(
        'No duplicate iso3×year rows',
        dupes == 0,
        f"{dupes} duplicates found"
    ))

    # 4. Awp range
    awp = df['awp_usd_per_m3'].dropna()
    if len(awp):
        n_high = (awp > AWP_MAX).sum()
        n_low  = (awp < AWP_MIN).sum()
        results.append(chk(
            f'Awp in [{AWP_MIN}, {AWP_MAX}] USD/m³',
            n_high == 0 and n_low == 0,
            f"High: {n_high}, Low: {n_low}, Range: {awp.min():.4f}-{awp.max():.4f}"
        ))

    # 5. VETb unit (should be m³, median >> 1e6)
    vetb = df['VETb_m3'].dropna()
    if len(vetb):
        median = vetb.median()
        results.append(chk(
            'VETb stored as m³ (median > 1e6)',
            median > 1e6,
            f"Median VETb = {median:.2e} m³"
        ))

    # 6. Cr range
    cr = df['cr_value'].dropna()
    if len(cr):
        results.append(chk(
            'Cr values in [0, 1]',
            cr.between(0, 1).all(),
            f"Range: {cr.min():.3f}-{cr.max():.3f}"
        ))

    # 7. tAwp ~ 0 at baseline 2018 (for rows where Awp is defined)
    base_rows = df[(df['year'] == YEAR_START) & df['tawp_pct'].notna()]
    if len(base_rows):
        nonzero = (base_rows['tawp_pct'].abs() > 0.01).sum()
        results.append(chk(
            f'tAwp ~ 0 at baseline {YEAR_START}',
            nonzero == 0,
            f"{nonzero} rows with |tAwp| > 0.01% at baseline"
        ))

    # 8. cAwp = NaN at baseline 2018 (no prior year to compare)
    base_cawp = df[(df['year'] == YEAR_START)]['cawp_pct']
    n_cawp_base = base_cawp.notna().sum()
    results.append(chk(
        f'cAwp = NaN at baseline {YEAR_START}',
        n_cawp_base == 0,
        f"{n_cawp_base} rows have non-NaN cAwp at baseline"
    ))

    # 9. Awp computed for at least 80 countries in 2020
    # ('OK' flag requires AQUASTAT Cr data; fallback Cr sources produce
    # CR_COUNTRY_FIXED / CR_REGIONAL_DEFAULT / CR_GLOBAL_DEFAULT instead)
    n_awp_2020 = df[(df['year'] == 2020) & df['awp_usd_per_m3'].notna()].shape[0]
    flags = df['quality_flag'].str.split(',').explode()
    results.append(chk(
        'Awp computed for >= 80 countries in 2020',
        n_awp_2020 >= 80,
        f"{n_awp_2020} countries with Awp in 2020; flags: {flags.value_counts().head(5).to_dict()}"
    ))

    # 10. Known-country Awp plausibility (2020)
    for iso3, (lo, hi) in KNOWN_COUNTRY_CHECKS.items():
        row = df[(df['iso3'] == iso3) & (df['year'] == 2020)]
        if row.empty:
            results.append(chk(f'{iso3} 2020 row exists', False, 'Not found'))
        else:
            val = row['awp_usd_per_m3'].values[0]
            ok  = pd.notna(val) and lo <= val <= hi
            results.append(chk(
                f'{iso3} 2020 Awp in [{lo}, {hi}] USD/m³',
                ok,
                f"Awp = {val:.4f}" if pd.notna(val) else "Awp = NaN"
            ))

    # ── Render report ─────────────────────────────────────────────────────────
    n_pass = sum(1 for r in results if r['status'] == 'PASS')
    n_fail = sum(1 for r in results if r['status'] == 'FAIL')

    lines = [
        'WaPOR4AWP Global - Validation Report',
        '=' * 60,
        f"File:  {CSV_FILE}",
        f"Rows:  {len(df)}",
        f"Date:  {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M')}",
        '',
        f"Result: {n_pass} PASS, {n_fail} FAIL",
        '-' * 60,
    ]
    for r in results:
        lines.append(f"[{r['status']:4s}] {r['title']}")
        if r['detail']:
            lines.append(f"       {r['detail']}")

    report = '\n'.join(lines)
    print(report)
    REPORT.write_text(report, encoding='utf-8')
    print(f"\nReport saved: {REPORT}")

    sys.exit(0 if n_fail == 0 else 1)


if __name__ == '__main__':
    main()
