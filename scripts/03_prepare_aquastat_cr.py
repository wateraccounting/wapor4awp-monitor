"""
03_prepare_aquastat_cr.py

Prepares the crop ratio (Cr) lookup table used in the Awp formula:

    Awp = GVAa × (1 − Cr) / VETb   [USD/m³]

Cr is the fraction of World Bank total agricultural GVA (which includes
forestry and fishing, WB indicator NV.AGR.TOTL.CD) that represents
non-irrigated production. It converts GVAa to approximate irrigated-crop GVA.

Fallback hierarchy:
  1. AQUASTAT-derived: Cr = 1 − (irrigated_area / total_cultivated_area)
     (best available proxy; requires AQUASTAT manual download — see below)
  2. Country-fixed: literature-based values for countries with known irrigation
     intensity (embedded in COUNTRY_FIXED_CR dict below)
  3. Regional default: World Bank region average (REGIONAL_CR_DEFAULTS below)
  4. Global default: Cr = 0.80

AQUASTAT data download:
    https://www.fao.org/aquastat/statistics/query/index.html
    Select: Country → All countries
    Variables:
      - "Total area equipped for irrigation" (ha)
      - "Cultivated area" (ha)
    Years: 2010–2023, export as CSV.

Expected input filenames (place in data/raw/aquastat/):
    aquastat_irrigated_area.csv   — columns: iso3, year, irrigated_area_ha
    aquastat_cultivated_area.csv  — columns: iso3, year, cultivated_area_ha

    Note: AQUASTAT uses ISO-3 codes. If the download uses country names,
    use the country_crosswalk.csv to map names to ISO-3 before saving.

Output: data/interim/aquastat_cr.csv
    iso3, year, cr_value, cr_source, cr_notes, wb_region
"""

import pandas as pd
import numpy as np
from pathlib import Path

# ── Paths ─────────────────────────────────────────────────────────────────────
ROOT        = Path(__file__).parent.parent
RAW_DIR     = ROOT / 'data' / 'raw' / 'aquastat'
INTERIM_DIR = ROOT / 'data' / 'interim'
OUT_FILE    = INTERIM_DIR / 'aquastat_cr.csv'
XWALK_FILE  = ROOT / 'data' / 'interim' / 'crosswalks' / 'country_crosswalk.csv'

INTERIM_DIR.mkdir(parents=True, exist_ok=True)

# ── Year range ────────────────────────────────────────────────────────────────
YEAR_START = 2018
YEAR_END   = 2025

# ── Constants ─────────────────────────────────────────────────────────────────
GLOBAL_DEFAULT_CR = 0.80

# Regional defaults: fraction of GVA attributable to non-irrigated agriculture.
# Values derived from literature (IFPRI SPAM, FAO reports). Review annually.
REGIONAL_CR_DEFAULTS = {
    'Sub-Saharan Africa':         0.85,  # mostly rainfed
    'Middle East & North Africa': 0.55,  # irrigation-intensive
    'South Asia':                 0.62,  # large irrigated sector
    'East Asia & Pacific':        0.72,
    'Europe & Central Asia':      0.78,
    'Latin America & Caribbean':  0.80,  # mostly rainfed
    'North America':              0.76,
}

# Country-fixed Cr from literature. Applied when AQUASTAT data absent.
# Source: AQUASTAT country profiles, IFPRI SPAM 2010, FAO FAOSTAT.
# Values are intentionally conservative — review each country's AQUASTAT profile.
COUNTRY_FIXED_CR = {
    'EGY': 0.30,  # Egypt: ~95% of cultivated area is irrigated
    'IRN': 0.45,  # Iran: large irrigation sector
    'IRQ': 0.45,  # Iraq: historically heavily irrigated
    'PAK': 0.48,  # Pakistan: Indus canal system
    'UZB': 0.42,  # Uzbekistan: Soviet-era intensive irrigation
    'TKM': 0.42,  # Turkmenistan: similar
    'KAZ': 0.60,  # Kazakhstan: mixed
    'IND': 0.60,  # India: ~50% cultivated area irrigated
    'CHN': 0.62,  # China: north irrigated, south rainfed
    'VNM': 0.50,  # Vietnam: extensive rice irrigation
    'THA': 0.55,  # Thailand: rice irrigation
    'PHL': 0.60,  # Philippines
    'IDN': 0.65,  # Indonesia
    'USA': 0.76,  # USA: ~15% harvested area irrigated
    'AUS': 0.70,  # Australia: mix; large dryland wheat sector
    'NLD': 0.48,  # Netherlands: intensive greenhouse/horticultural
    'ESP': 0.52,  # Spain: substantial Mediterranean irrigation
    'ITA': 0.58,  # Italy: Po Valley and southern irrigation
    'GRC': 0.55,  # Greece
    'PRT': 0.60,  # Portugal
    'MAR': 0.55,  # Morocco: significant irrigation
    'TUN': 0.62,  # Tunisia
    'DZA': 0.68,  # Algeria
    'SDN': 0.55,  # Sudan: Gezira scheme
    'ETH': 0.88,  # Ethiopia: mostly rainfed smallholders
    'NGA': 0.87,  # Nigeria: mostly rainfed
    'TZA': 0.88,  # Tanzania: mostly rainfed
    'GHA': 0.87,  # Ghana
    'MOZ': 0.89,  # Mozambique
    'BRA': 0.82,  # Brazil: large rainfed soy/sugarcane sector
    'ARG': 0.80,  # Argentina: mostly rainfed
    'MEX': 0.65,  # Mexico: significant irrigation in north
    'CHL': 0.58,  # Chile: arid north, irrigated valleys
    'PER': 0.52,  # Peru: coastal irrigation strips
}


# ── Load AQUASTAT data ────────────────────────────────────────────────────────
def load_aquastat() -> tuple:
    irr_file  = RAW_DIR / 'aquastat_irrigated_area.csv'
    cult_file = RAW_DIR / 'aquastat_cultivated_area.csv'

    irr_df = cult_df = None

    if irr_file.exists():
        irr_df = pd.read_csv(irr_file, dtype={'iso3': str})
        print(f"  Irrigated area: {len(irr_df)} records, "
              f"{irr_df['iso3'].nunique()} countries")
    else:
        print(f"  aquastat_irrigated_area.csv not found — skipping Level 1")

    if cult_file.exists():
        cult_df = pd.read_csv(cult_file, dtype={'iso3': str})
        print(f"  Cultivated area: {len(cult_df)} records, "
              f"{cult_df['iso3'].nunique()} countries")
    else:
        print(f"  aquastat_cultivated_area.csv not found — skipping Level 1")

    return irr_df, cult_df


def derive_cr_from_areas(irr_df: pd.DataFrame, cult_df: pd.DataFrame) -> pd.DataFrame:
    """Cr ≈ 1 − (irrigated_ha / cultivated_ha), clipped to [0.10, 0.99]."""
    merged = irr_df.merge(cult_df, on=['iso3', 'year'], how='inner')
    merged = merged[merged['cultivated_area_ha'] > 0].copy()
    merged['irr_frac'] = (
        merged['irrigated_area_ha'] / merged['cultivated_area_ha']
    ).clip(0.01, 0.99)
    merged['cr_value']  = (1.0 - merged['irr_frac']).clip(0.10, 0.99)
    merged['cr_source'] = 'AQUASTAT_area_ratio'
    merged['cr_notes']  = '1 − (irr_ha / cult_ha)'
    return merged[['iso3', 'year', 'cr_value', 'cr_source', 'cr_notes']]


def build_cr_table() -> pd.DataFrame:
    if not XWALK_FILE.exists():
        raise FileNotFoundError(
            f"Crosswalk not found: {XWALK_FILE}\n"
            "Run scripts/04_build_country_crosswalk.py first."
        )

    xwalk = pd.read_csv(XWALK_FILE, dtype={'iso3': str})
    iso3_list = xwalk[xwalk['include_flag'].isin(['YES', 'REVIEW'])]['iso3'].tolist()

    years = list(range(YEAR_START, YEAR_END + 1))
    full = pd.DataFrame(
        [(iso3, yr) for iso3 in iso3_list for yr in years],
        columns=['iso3', 'year']
    )

    print("\nLoading AQUASTAT data…")
    irr_df, cult_df = load_aquastat()

    # Level 1: AQUASTAT area-ratio
    level1 = pd.DataFrame()
    if irr_df is not None and cult_df is not None:
        level1 = derive_cr_from_areas(irr_df, cult_df)
        print(f"  Level 1 (AQUASTAT): {len(level1)} country-years")

    result = full.merge(
        level1[['iso3', 'year', 'cr_value', 'cr_source', 'cr_notes']]
        if not level1.empty
        else pd.DataFrame(columns=['iso3', 'year', 'cr_value', 'cr_source', 'cr_notes']),
        on=['iso3', 'year'], how='left'
    )

    # Level 2: Country-fixed
    fixed_series = pd.Series(COUNTRY_FIXED_CR, name='cr_fixed').reset_index()
    fixed_series.columns = ['iso3', 'cr_fixed']
    result = result.merge(fixed_series, on='iso3', how='left')

    mask2 = result['cr_value'].isna() & result['cr_fixed'].notna()
    result.loc[mask2, 'cr_value']  = result.loc[mask2, 'cr_fixed']
    result.loc[mask2, 'cr_source'] = 'COUNTRY_FIXED'
    result.loc[mask2, 'cr_notes']  = 'Country fixed Cr from literature'
    n2 = mask2.sum()
    print(f"  Level 2 (country fixed): {n2} country-years")

    # Level 3: Regional default
    region_map = xwalk.set_index('iso3')['wb_region'].to_dict()
    result['wb_region'] = result['iso3'].map(region_map)
    result['cr_regional'] = result['wb_region'].map(REGIONAL_CR_DEFAULTS)

    mask3 = result['cr_value'].isna() & result['cr_regional'].notna()
    result.loc[mask3, 'cr_value']  = result.loc[mask3, 'cr_regional']
    result.loc[mask3, 'cr_source'] = 'REGIONAL_DEFAULT'
    result.loc[mask3, 'cr_notes']  = (
        result.loc[mask3, 'wb_region'] + ' regional default'
    )
    n3 = mask3.sum()
    print(f"  Level 3 (regional default): {n3} country-years")

    # Level 4: Global default
    mask4 = result['cr_value'].isna()
    result.loc[mask4, 'cr_value']  = GLOBAL_DEFAULT_CR
    result.loc[mask4, 'cr_source'] = 'GLOBAL_DEFAULT'
    result.loc[mask4, 'cr_notes']  = f'Global default Cr = {GLOBAL_DEFAULT_CR}'
    n4 = mask4.sum()
    print(f"  Level 4 (global default {GLOBAL_DEFAULT_CR}): {n4} country-years")

    result['cr_value'] = result['cr_value'].round(4)
    return result[['iso3', 'year', 'cr_value', 'cr_source', 'cr_notes', 'wb_region']]


def main():
    print("Building Cr lookup table…")
    cr = build_cr_table()

    print(f"\nTotal records: {len(cr)}")
    print(f"Countries: {cr['iso3'].nunique()}")
    print(f"Cr range: {cr['cr_value'].min():.3f} – {cr['cr_value'].max():.3f}")
    print(f"Cr mean:  {cr['cr_value'].mean():.3f}")

    print("\nSource breakdown:")
    print(cr['cr_source'].value_counts().to_string())

    cr.to_csv(OUT_FILE, index=False)
    print(f"\nSaved: {OUT_FILE}")

    print("\nSanity check — selected countries (year 2020):")
    check_iso3 = ['EGY', 'IND', 'NLD', 'ETH', 'BRA', 'USA', 'PAK']
    sample = cr[cr['iso3'].isin(check_iso3) & (cr['year'] == 2020)].copy()
    sample = sample.sort_values('cr_value')
    print(sample[['iso3', 'cr_value', 'cr_source']].to_string(index=False))
    print("\nExpected order (low Cr = highly irrigated):")
    print("  EGY < PAK < NLD < IND < USA < BRA < ETH")


if __name__ == '__main__':
    main()
