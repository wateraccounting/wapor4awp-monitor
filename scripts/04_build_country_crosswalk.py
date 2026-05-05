"""
04_build_country_crosswalk.py

Builds country_crosswalk.csv — the ISO-3 master alignment table
across World Bank, AQUASTAT, GEE boundaries, and the dashboard GeoJSON.

Flags known problem cases and generates an include/exclude list.

Output: data/interim/crosswalks/country_crosswalk.csv
        data/interim/crosswalks/crosswalk_flags.csv

Usage:
    python scripts/04_build_country_crosswalk.py

Requirements:
    pip install pandas requests
"""

import json
import pandas as pd
import requests
from pathlib import Path

OUT_DIR   = Path(__file__).parent.parent / 'data' / 'interim' / 'crosswalks'
GEOJSON   = Path(__file__).parent.parent.parent.parent / 'wapor4awp_web-main' / 'awp_map_new.json'
OUT_FILE  = OUT_DIR / 'country_crosswalk.csv'
FLAG_FILE = OUT_DIR / 'crosswalk_flags.csv'

OUT_DIR.mkdir(parents=True, exist_ok=True)

# ── Known problem cases requiring manual review ──────────────────────────────
PROBLEM_CASES = {
    'COD': 'Democratic Republic of Congo — often split from COG in datasets',
    'CIV': "Côte d'Ivoire — name varies (Ivory Coast)",
    'TUR': 'Turkey — officially renamed Türkiye in 2022; World Bank may lag',
    'SWZ': 'Eswatini — formerly Swaziland; older data use SWZ/SWZ or SZ',
    'PSE': 'Palestine / West Bank and Gaza — incomplete World Bank data',
    'SDN': 'Sudan — split from South Sudan (SSD) in 2011; pre-2011 data combined',
    'SSD': 'South Sudan — independent 2011; no pre-2011 data',
    'XKX': 'Kosovo — not an ISO-3 member; World Bank uses XKX',
    'ESH': 'Western Sahara — no World Bank or AQUASTAT data',
    'TWN': 'Taiwan — not in World Bank API',
    'CUB': 'Cuba — World Bank data often missing',
    'PRK': 'North Korea — World Bank data absent',
}

# ── World Bank country list ──────────────────────────────────────────────────
def fetch_wb_countries() -> pd.DataFrame:
    print("Fetching World Bank country list…")
    url = 'https://api.worldbank.org/v2/country?format=json&per_page=500'
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    meta, data = resp.json()
    rows = []
    for c in data:
        if c.get('region', {}).get('id') == 'NA':
            continue  # skip aggregates
        rows.append({
            'iso3':         c['id'],
            'wb_name':      c['name'],
            'wb_iso2':      c.get('iso2Code', ''),
            'wb_region':    c.get('region', {}).get('value', ''),
            'wb_income':    c.get('incomeLevel', {}).get('value', ''),
        })
    return pd.DataFrame(rows)


# ── Load existing GeoJSON ISO-3 codes ────────────────────────────────────────
def load_geojson_iso3(geojson_path: Path) -> pd.DataFrame:
    if not geojson_path.exists():
        print(f"  GeoJSON not found at {geojson_path} — skipping")
        return pd.DataFrame(columns=['iso3', 'geojson_name'])
    with open(geojson_path, encoding='utf-8') as f:
        gj = json.load(f)
    rows = []
    for feat in gj.get('features', []):
        props = feat.get('properties', {})
        iso3  = props.get('ISO-3') or props.get('iso3') or props.get('ISO3') or ''
        name  = props.get('NAME_EN') or props.get('WB_NAME') or props.get('name') or ''
        if iso3:
            rows.append({'iso3': iso3, 'geojson_name': name})
    return pd.DataFrame(rows).drop_duplicates('iso3')


def main():
    wb  = fetch_wb_countries()
    print(f"World Bank countries: {len(wb)}")

    gj  = load_geojson_iso3(GEOJSON)
    print(f"GeoJSON ISO-3 codes: {len(gj)}")

    # ── Merge ────────────────────────────────────────────────────────────────
    xwalk = wb.merge(gj, on='iso3', how='outer', indicator='_src')
    xwalk['source'] = xwalk['_src'].map({
        'both':       'wb+geojson',
        'left_only':  'wb_only',
        'right_only': 'geojson_only',
    })
    xwalk.drop(columns=['_src'], inplace=True)

    # ── Standard name: prefer WB name, fall back to GeoJSON ─────────────────
    xwalk['country_name_standard'] = xwalk['wb_name'].fillna(xwalk['geojson_name'])

    # ── Dashboard name (same as standard for now) ─────────────────────────────
    xwalk['dashboard_name'] = xwalk['country_name_standard']

    # ── Include flag ─────────────────────────────────────────────────────────
    # Exclude if no World Bank data AND no GeoJSON entry, or if known non-sovereign
    xwalk['include_flag'] = xwalk['source'].apply(
        lambda s: 'YES' if s in ('wb+geojson', 'wb_only', 'geojson_only') else 'NO'
    )

    # ── Problem case notes ───────────────────────────────────────────────────
    xwalk['notes'] = xwalk['iso3'].map(PROBLEM_CASES).fillna('')

    # Flag problem cases
    xwalk.loc[xwalk['notes'] != '', 'include_flag'] = 'REVIEW'

    # ── AQUASTAT name placeholder (filled manually from AQUASTAT data) ────────
    xwalk['aquastat_name']  = ''
    xwalk['faostat_code']   = ''
    xwalk['gee_boundary_name'] = xwalk['geojson_name']

    # ── Final column order ────────────────────────────────────────────────────
    cols = [
        'iso3', 'country_name_standard', 'dashboard_name',
        'wb_name', 'wb_region', 'wb_income',
        'aquastat_name', 'faostat_code',
        'geojson_name', 'gee_boundary_name',
        'include_flag', 'source', 'notes',
    ]
    xwalk = xwalk[cols].sort_values('iso3').reset_index(drop=True)

    xwalk.to_csv(OUT_FILE, index=False)
    print(f"Crosswalk saved: {OUT_FILE}  ({len(xwalk)} rows)")

    # ── Flag report ───────────────────────────────────────────────────────────
    flags = xwalk[xwalk['include_flag'] == 'REVIEW'][
        ['iso3', 'country_name_standard', 'notes']
    ]
    flags.to_csv(FLAG_FILE, index=False)
    print(f"Problem cases flagged: {len(flags)}")
    print("\nCountries requiring manual review:")
    for _, row in flags.iterrows():
        print(f"  {row['iso3']:6s}  {row['country_name_standard']:40s}  {row['notes']}")

    # ── Coverage summary ──────────────────────────────────────────────────────
    print(f"\nCoverage summary:")
    print(xwalk['include_flag'].value_counts().to_string())


if __name__ == '__main__':
    main()
