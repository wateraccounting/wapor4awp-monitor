"""
05_compute_annual_awp.py

Merges GEE country summaries, World Bank GVA, and AQUASTAT Cr to compute
annual Agricultural Water Productivity (Awp) and derived indicators.

Core formula:
    Awp = GVAa × (1 − Cr) / VETb   [USD/m³]

    GVAa = World Bank NV.AGR.TOTL.CD (USD, current prices)
    Cr   = crop ratio (0–1) from aquastat_cr.csv
    VETb = annual blue ET volume (m³/year) from GEE export

Derived indicators:
    cAwp (%) = (Awp_t − Awp_{t−1}) / Awp_{t−1} × 100
    tAwp (%) = (Awp_t − Awp_2018)  / Awp_2018  × 100

GEE exports may have multiple rows per country (LSIB multi-polygon countries).
This script aggregates to one row per iso3×year before computing Awp.

Output: data/final/global_awp_country_year.csv
"""

import pandas as pd
import numpy as np
from pathlib import Path

# ── Paths ─────────────────────────────────────────────────────────────────────
ROOT       = Path(__file__).parent.parent
GEE_DIR    = ROOT / 'data' / 'raw' / 'gee_exports'
WB_FILE    = ROOT / 'data' / 'raw' / 'worldbank' / 'worldbank_gva_agriculture.csv'
CR_FILE    = ROOT / 'data' / 'interim' / 'aquastat_cr.csv'
XWALK_FILE = ROOT / 'data' / 'interim' / 'crosswalks' / 'country_crosswalk.csv'
OUT_DIR    = ROOT / 'data' / 'final'
OUT_FILE   = OUT_DIR / 'global_awp_country_year.csv'

OUT_DIR.mkdir(parents=True, exist_ok=True)

# ── Thresholds ────────────────────────────────────────────────────────────────
BASELINE_YEAR    = 2018
MIN_GMIE_AREA_HA = 1_000     # minimum GMIE-weighted irrigated area (ha) to compute Awp
MIN_ETB_MM       = 1.0       # minimum annual ETb depth (mm); excludes humid countries
                              # where Pe covers all crop water need and VETb ≈ 0
AWP_OUTLIER_HIGH = 50.0      # USD/m³ — flag as outlier if Awp exceeds this
AWP_OUTLIER_LOW  = 0.001     # USD/m³ — flag if below this

# ── LSIB name → ISO-3 mapping ─────────────────────────────────────────────────
# USDOS/LSIB_SIMPLE/2017 has no iso_alpha3 property; the GEE script exports
# country_name instead.  This dict maps LSIB country_na strings to ISO-3.
# Sub-national LSIB polygons (e.g. 'Spain (Canary Is)') are mapped to their
# parent ISO-3 so they aggregate correctly in groupby().
_LSIB_NAME_TO_ISO3 = {
    # sovereign states with non-standard LSIB names
    'Burma':                        'MMR',
    'Laos':                         'LAO',
    'Vietnam':                      'VNM',
    'Iran':                         'IRN',
    'Turkey':                       'TUR',
    'Syria':                        'SYR',
    'Yemen':                        'YEM',
    'Russia':                       'RUS',
    'Somalia':                      'SOM',
    'Egypt':                        'EGY',
    'Venezuela':                    'VEN',
    'Kyrgyzstan':                   'KGZ',
    'Brunei':                       'BRN',
    'Korea, South':                 'KOR',
    'Korea, North':                 'PRK',
    'Rep of the Congo':             'COG',
    'Dem Rep of the Congo':         'COD',
    'Central African Rep':          'CAF',
    'Sao Tome & Principe':          'STP',
    'Trinidad & Tobago':            'TTO',
    'Antigua & Barbuda':            'ATG',
    'St Kitts & Nevis':             'KNA',
    'St Vincent & the Grenadines':  'VCT',
    'Saint Lucia':                  'LCA',
    'Cook Is':                      'COK',
    'Marshall Is':                  'MHL',
    'Fed States of Micronesia':     'FSM',
    'Solomon Is':                   'SLB',
    'Hong Kong':                    'HKG',
    'Macau':                        'MAC',
    'Taiwan':                       'TWN',
    'Swaziland':                    'SWZ',
    'Bosnia & Herzegovina':         'BIH',
    'Macedonia':                    'MKD',
    'Slovakia':                     'SVK',
    'Western Sahara':               'ESH',
    'Gaza Strip':                   'PSE',
    'West Bank':                    'PSE',
    # overseas territories / dependencies with ISO-3 codes
    'Puerto Rico':                  'PRI',
    'Guadeloupe':                   'GLP',
    'Martinique':                   'MTQ',
    'Reunion':                      'REU',
    'French Guiana':                'GUF',
    'US Virgin Is':                 'VIR',
    'British Virgin Is':            'VGB',
    'St Barthelemy':                'BLM',
    'Anguilla':                     'AIA',
    'St Martin':                    'MAF',
    'Sint Maarten':                 'SXM',
    'Montserrat':                   'MSR',
    'Faroe Is':                     'FRO',
    'Svalbard':                     'SJM',
    'Jan Mayen':                    'SJM',
    'Turks & Caicos Is':            'TCA',
    'St Pierre & Miquelon':         'SPM',
    'Cayman Is':                    'CYM',
    'Falkland Islands':             'FLK',
    'Norfolk I':                    'NFK',
    'Mayotte':                      'MYT',
    'St Helena':                    'SHN',
    'British Indian Ocean Terr':    'IOT',
    'Christmas I':                  'CXR',
    'Cocos (Keeling) Is':           'CCK',
    'Pitcairn Is':                  'PCN',
    'Tokelau':                      'TKL',
    'Wallis & Futuna':              'WLF',
    'Niue':                         'NIU',
    'Northern Mariana Is':          'MNP',
    'Vatican City':                 'VAT',
    'Jersey':                       'JEY',
    'Guernsey':                     'GGY',
    'Bouvet Island':                'BVT',
    'S Georgia & S Sandwich Is':    'SGS',
    'Heard I & McDonald Is':        'HMD',
    'French S & Antarctic Lands':   'ATF',
    'Antarctica':                   'ATA',
    # sub-national LSIB polygons — map to parent country ISO-3
    'Spain (Canary Is)':            'ESP',
    'Spain (Africa)':               'ESP',
    'Portugal (Madeira Is)':        'PRT',
    'Portugal (Azores)':            'PRT',
    'United States (Hawaii)':       'USA',
    'United States (Alaska)':       'USA',
    'Netherlands (Caribbean)':      'BES',
    'Coral Sea Is':                 'AUS',
    'Ashmore & Cartier Is':         'AUS',
    'Wake I':                       'UMI',
    'US Minor Pacific Is. Refuges': 'UMI',
}


def _fill_iso3_from_name(raw: pd.DataFrame) -> pd.DataFrame:
    """Fill null iso3 values from country_name using crosswalk + LSIB name map."""
    xwalk = pd.read_csv(XWALK_FILE, dtype={'iso3': str})
    name_cols = ['country_name_standard', 'dashboard_name', 'wb_name',
                 'aquastat_name', 'geojson_name', 'gee_boundary_name']
    lookup: dict[str, str] = {}
    for _, row in xwalk.iterrows():
        for col in name_cols:
            v = row[col]
            if pd.notna(v) and str(v).strip():
                lookup[str(v).strip()] = row['iso3']
    lookup.update(_LSIB_NAME_TO_ISO3)

    mask = raw['iso3'].isna()
    raw.loc[mask, 'iso3'] = raw.loc[mask, 'country_name'].str.strip().map(lookup)

    n_dropped = raw['iso3'].isna().sum()
    if n_dropped:
        unknown = sorted(raw.loc[raw['iso3'].isna(), 'country_name'].unique())
        print(f"  Dropping {n_dropped} rows with unmapped country_name "
              f"(disputed areas / uninhabited territories):")
        for nm in unknown[:20]:
            print(f"    '{nm}'")
    return raw[raw['iso3'].notna()].copy()


# ── Load and aggregate GEE exports ───────────────────────────────────────────
def load_gee_exports() -> pd.DataFrame:
    files = sorted(GEE_DIR.glob('awp_gee_country_*.csv'))
    if not files:
        raise FileNotFoundError(
            f"No GEE CSV files found in {GEE_DIR}\n"
            "Run GEE script 02_export_country_awp.js,\n"
            "download from Google Drive, and place CSVs in data/raw/gee_exports/"
        )

    dfs = []
    for f in files:
        df = pd.read_csv(f, dtype={'iso3': str})
        if 'year' not in df.columns:
            df['year'] = int(f.stem.split('_')[-1])
        dfs.append(df)
        print(f"  Loaded: {f.name}  ({len(df)} rows)")

    raw = pd.concat(dfs, ignore_index=True)

    # LSIB_SIMPLE has no iso_alpha3 property — derive iso3 from country_name
    if raw['iso3'].isna().any():
        n_null = raw['iso3'].isna().sum()
        print(f"  {n_null} rows have null iso3 — deriving from country_name…")
        raw = _fill_iso3_from_name(raw)

    print(f"  Total GEE rows (before aggregation): {len(raw)}")

    # Aggregate multi-polygon countries: sum raw quantities
    # Accept both old column name (gmie_area_m2) and new (irr_area_m2)
    if 'gmie_area_m2' in raw.columns and 'irr_area_m2' not in raw.columns:
        raw = raw.rename(columns={'gmie_area_m2': 'irr_area_m2'})

    agg = raw.groupby(['iso3', 'year'], as_index=False).agg({
        'VETb_m3':    'sum',
        'irr_area_m2': 'sum',
        'AETI_wsum':  'sum',
        'ETb_wsum':   'sum',
    })

    # Compute area-weighted mean depths from pre-aggregated sums
    safe_area = agg['irr_area_m2'].replace(0, np.nan)
    agg['AETI_annual_mm'] = agg['AETI_wsum'] / safe_area
    agg['ETb_annual_mm']  = agg['ETb_wsum']  / safe_area
    agg['irr_area_ha']    = agg['irr_area_m2'] / 10_000

    agg.drop(columns=['irr_area_m2', 'AETI_wsum', 'ETb_wsum'], inplace=True)
    print(f"  After aggregation: {len(agg)} country-year rows")
    return agg


# ── Quality flag assignment ───────────────────────────────────────────────────
def assign_flags(row: pd.Series) -> str:
    flags = []

    if pd.isna(row.get('gva_agriculture_usd')):
        flags.append('MISSING_GVA')

    cr_src = row.get('cr_source', '')
    if pd.isna(row.get('cr_value')):
        flags.append('MISSING_CR')
    elif cr_src == 'COUNTRY_FIXED':
        flags.append('CR_COUNTRY_FIXED')
    elif cr_src == 'REGIONAL_DEFAULT':
        flags.append('CR_REGIONAL_DEFAULT')
    elif cr_src == 'GLOBAL_DEFAULT':
        flags.append('CR_GLOBAL_DEFAULT')

    vetb = row.get('VETb_m3', np.nan)
    etb_mm = row.get('ETb_annual_mm', np.nan)
    if pd.isna(vetb) or vetb <= 0:
        flags.append('ZERO_VETB')
    elif pd.notna(etb_mm) and etb_mm < MIN_ETB_MM:
        flags.append('ZERO_VETB')  # effective Pe covers all crop water; no blue ET

    area = row.get('irr_area_ha', np.nan)
    if pd.isna(area) or area <= 0:
        flags.append('NO_GMIE_IRRIGATION')
    elif area < MIN_GMIE_AREA_HA:
        flags.append('LOW_GMIE_AREA')

    awp = row.get('awp_usd_per_m3', np.nan)
    if pd.notna(awp) and (awp > AWP_OUTLIER_HIGH or awp < AWP_OUTLIER_LOW):
        flags.append('OUTLIER_AWP')

    return ','.join(flags) if flags else 'OK'


def main():
    # ── Load inputs ───────────────────────────────────────────────────────────
    print("Loading GEE exports…")
    gee = load_gee_exports()

    print("\nLoading World Bank GVA…")
    wb = pd.read_csv(WB_FILE, dtype={'iso3': str})
    print(f"  {len(wb)} records, {wb['iso3'].nunique()} countries")

    print("\nLoading Cr table…")
    cr = pd.read_csv(CR_FILE, dtype={'iso3': str})
    print(f"  {len(cr)} records")

    print("\nLoading country crosswalk…")
    xwalk = pd.read_csv(XWALK_FILE, dtype={'iso3': str})
    xwalk = xwalk[xwalk['include_flag'].isin(['YES', 'REVIEW'])].copy()
    meta_cols = ['iso3', 'country_name_standard', 'dashboard_name',
                 'wb_region', 'wb_income']
    xwalk = xwalk[meta_cols]

    # ── Merge ─────────────────────────────────────────────────────────────────
    df = gee.merge(wb[['iso3', 'year', 'gva_agriculture_usd']],
                   on=['iso3', 'year'], how='left')

    df = df.merge(cr[['iso3', 'year', 'cr_value', 'cr_source']],
                  on=['iso3', 'year'], how='left')

    df = df.merge(xwalk, on='iso3', how='left')

    print(f"\nMerged: {len(df)} country-year rows, {df['iso3'].nunique()} countries")

    # ── Compute Awp ───────────────────────────────────────────────────────────
    # ETb_annual_mm < MIN_ETB_MM means effective precipitation covers all crop
    # water needs in this country; VETb is near-zero and Awp would be meaningless.
    can_compute = (
        df['gva_agriculture_usd'].notna() & (df['gva_agriculture_usd'] > 0) &
        df['cr_value'].notna() &
        df['VETb_m3'].notna()  & (df['VETb_m3'] > 0) &
        df['ETb_annual_mm'].notna() & (df['ETb_annual_mm'] >= MIN_ETB_MM) &
        df['irr_area_ha'].notna() & (df['irr_area_ha'] >= MIN_GMIE_AREA_HA)
    )

    df['awp_usd_per_m3'] = np.where(
        can_compute,
        df['gva_agriculture_usd'] * (1.0 - df['cr_value']) / df['VETb_m3'],
        np.nan
    )

    print(f"Awp computed for: {can_compute.sum()} / {len(df)} country-years")

    # ── Quality flags ─────────────────────────────────────────────────────────
    df['quality_flag'] = df.apply(assign_flags, axis=1)

    # ── cAwp: year-to-year change ─────────────────────────────────────────────
    df = df.sort_values(['iso3', 'year']).reset_index(drop=True)
    df['awp_prev'] = df.groupby('iso3')['awp_usd_per_m3'].shift(1)
    df['cawp_pct'] = np.where(
        df['awp_prev'].notna() & (df['awp_prev'] > 0),
        (df['awp_usd_per_m3'] - df['awp_prev']) / df['awp_prev'] * 100,
        np.nan
    )
    df.drop(columns=['awp_prev'], inplace=True)

    # ── tAwp: change since 2018 baseline ─────────────────────────────────────
    baseline = (
        df[df['year'] == BASELINE_YEAR][['iso3', 'awp_usd_per_m3']]
        .rename(columns={'awp_usd_per_m3': 'awp_baseline'})
    )
    df = df.merge(baseline, on='iso3', how='left')
    df['tawp_pct'] = np.where(
        df['awp_baseline'].notna() & (df['awp_baseline'] > 0),
        (df['awp_usd_per_m3'] - df['awp_baseline']) / df['awp_baseline'] * 100,
        np.nan
    )
    df.drop(columns=['awp_baseline'], inplace=True)

    # ── VETb display column ────────────────────────────────────────────────────
    df['vetb_Mm3'] = df['VETb_m3'] / 1_000_000

    # ── Round for readability ─────────────────────────────────────────────────
    df['awp_usd_per_m3'] = df['awp_usd_per_m3'].round(6)
    df['cawp_pct']       = df['cawp_pct'].round(2)
    df['tawp_pct']       = df['tawp_pct'].round(2)
    df['vetb_Mm3']       = df['vetb_Mm3'].round(3)
    df['irr_area_ha']    = df['irr_area_ha'].round(1)
    df['AETI_annual_mm'] = df['AETI_annual_mm'].round(1)
    df['ETb_annual_mm']  = df['ETb_annual_mm'].round(1)

    # ── Final column order ────────────────────────────────────────────────────
    col_order = [
        'iso3', 'country_name_standard', 'dashboard_name', 'wb_region', 'wb_income',
        'year',
        'awp_usd_per_m3', 'cawp_pct', 'tawp_pct',
        'VETb_m3', 'vetb_Mm3',
        'gva_agriculture_usd',
        'cr_value', 'cr_source',
        'irr_area_ha',
        'ETb_annual_mm', 'AETI_annual_mm',
        'landuse_source',
        'quality_flag',
    ]
    col_order = [c for c in col_order if c in df.columns]
    df = df[col_order].sort_values(['iso3', 'year']).reset_index(drop=True)

    df.to_csv(OUT_FILE, index=False)
    print(f"\nSaved: {OUT_FILE}  ({len(df)} rows)")

    # ── Summary ───────────────────────────────────────────────────────────────
    awp_valid = df['awp_usd_per_m3'].notna()
    print(f"\nAwp statistics ({awp_valid.sum()} country-years):")
    print(df.loc[awp_valid, 'awp_usd_per_m3'].describe().round(4).to_string())

    print("\nQuality flag counts:")
    flag_counts = df['quality_flag'].str.split(',').explode().value_counts()
    print(flag_counts.to_string())

    print("\nSanity check (year 2020):")
    check_iso3 = ['EGY', 'IND', 'NLD', 'ETH', 'USA', 'BRA']
    sample = df[df['iso3'].isin(check_iso3) & (df['year'] == 2020)][
        ['iso3', 'awp_usd_per_m3', 'VETb_m3', 'irr_area_ha', 'cr_value', 'quality_flag']
    ].sort_values('awp_usd_per_m3', ascending=False)
    print(sample.to_string(index=False))


if __name__ == '__main__':
    main()
