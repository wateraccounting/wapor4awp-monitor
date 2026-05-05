"""
02_download_worldbank_gva.py

Downloads World Bank indicator NV.AGR.TOTL.CD
(Agriculture, forestry and fishing, value added, current US$)
for all countries, years 2010-2024.

Output: data/raw/worldbank/worldbank_gva_agriculture.csv
        data/raw/worldbank/worldbank_gva_coverage.csv  (missing-data report)

Usage:
    python scripts/02_download_worldbank_gva.py

Requirements:
    pip install requests pandas
"""

import requests
import pandas as pd
from pathlib import Path
import time
import sys

# ── Config ───────────────────────────────────────────────────────────────────
INDICATOR   = 'NV.AGR.TOTL.CD'
YEARS_START = 2010
YEARS_END   = 2025
OUT_DIR     = Path(__file__).parent.parent / 'data' / 'raw' / 'worldbank'
OUT_FILE    = OUT_DIR / 'worldbank_gva_agriculture.csv'
COV_FILE    = OUT_DIR / 'worldbank_gva_coverage.csv'
BASE_URL    = 'https://api.worldbank.org/v2/country/all/indicator'

OUT_DIR.mkdir(parents=True, exist_ok=True)


def fetch_all_pages(indicator: str, year_start: int, year_end: int) -> list[dict]:
    """Fetch all pages for a World Bank indicator query."""
    url = f"{BASE_URL}/{indicator}"
    params = {
        'format':   'json',
        'per_page': 1000,
        'date':     f"{year_start}:{year_end}",
        'page':     1,
    }
    rows = []
    while True:
        resp = requests.get(url, params=params, timeout=30)
        resp.raise_for_status()
        payload = resp.json()

        # World Bank API returns [metadata, data]
        if not isinstance(payload, list) or len(payload) < 2:
            print(f"Unexpected response format: {payload}", file=sys.stderr)
            break

        meta, data = payload
        if not data:
            break

        rows.extend(data)
        total_pages = meta.get('pages', 1)
        current     = meta.get('page', 1)
        print(f"  page {current}/{total_pages} — {len(data)} records")

        if current >= total_pages:
            break
        params['page'] += 1
        time.sleep(0.3)

    return rows


def parse_rows(raw: list[dict]) -> pd.DataFrame:
    records = []
    for r in raw:
        if r.get('value') is None:
            continue
        iso3 = r.get('countryiso3code', '')
        if not iso3 or len(iso3) != 3:
            continue
        records.append({
            'iso3':                iso3,
            'country_name':        r['country']['value'],
            'year':                int(r['date']),
            'gva_agriculture_usd': float(r['value']),
        })
    df = pd.DataFrame(records)
    if df.empty:
        return df
    df = df.sort_values(['iso3', 'year']).reset_index(drop=True)
    return df


def coverage_report(df: pd.DataFrame) -> pd.DataFrame:
    """Which country-years are missing."""
    all_iso3  = df['iso3'].unique()
    all_years = list(range(YEARS_START, YEARS_END + 1))
    full_idx  = pd.MultiIndex.from_product(
        [all_iso3, all_years], names=['iso3', 'year']
    )
    full_df   = pd.DataFrame(index=full_idx).reset_index()
    merged    = full_df.merge(df[['iso3', 'year', 'gva_agriculture_usd']],
                              on=['iso3', 'year'], how='left')
    missing   = merged[merged['gva_agriculture_usd'].isna()]
    return missing[['iso3', 'year']].copy()


def main():
    print(f"Downloading World Bank {INDICATOR} ({YEARS_START}–{YEARS_END})…")
    raw  = fetch_all_pages(INDICATOR, YEARS_START, YEARS_END)
    print(f"Total raw records fetched: {len(raw)}")

    df = parse_rows(raw)
    print(f"Parsed records (non-null, ISO-3 countries): {len(df)}")

    if df.empty:
        print("ERROR: No records parsed. Printing first raw record for diagnosis:")
        if raw:
            print(raw[0])
        sys.exit(1)

    print(f"Countries covered: {df['iso3'].nunique()}")
    print(f"Year range: {df['year'].min()}–{df['year'].max()}")

    df.to_csv(OUT_FILE, index=False)
    print(f"Saved: {OUT_FILE}")

    cov = coverage_report(df)
    cov.to_csv(COV_FILE, index=False)
    print(f"Missing country-years: {len(cov)}")
    print(f"Coverage report: {COV_FILE}")

    # Quick sanity check
    sample = df[df['iso3'] == 'ETH'].sort_values('year')
    if not sample.empty:
        print("\nSanity check — Ethiopia GVA (USD):")
        print(sample[['year', 'gva_agriculture_usd']].to_string(index=False))
    else:
        print("\nWarning: Ethiopia (ETH) not found in results — check ISO-3 codes.")


if __name__ == '__main__':
    main()
