"""
utils.py - shared constants and helpers for the Streamlit dashboard.
"""

import pandas as pd
import json
from pathlib import Path

# ── Paths ─────────────────────────────────────────────────────────────────────
ROOT       = Path(__file__).parent.parent
DATA_FINAL = ROOT / 'data' / 'final' / 'global_awp_country_year.csv'
GEOJSON    = ROOT / 'data' / 'raw' / 'boundaries' / 'global_boundaries_iso3.geojson'

# ── Indicator catalogue ───────────────────────────────────────────────────────
INDICATORS = {
    'awp_usd_per_m3': {
        'label':    'Agricultural Water Productivity (Awp)',
        'unit':     'USD/m³',
        'format':   ',.3f',
        'colorscale': 'YlGn',
        'higher_is': 'better',
        'description': (
            'Value of irrigated agricultural production per cubic metre '
            'of blue evapotranspiration consumed.'
        ),
    },
    'cawp_pct': {
        'label':    'Year-to-year change in Awp (cAwp)',
        'unit':     '%',
        'format':   '+,.1f',
        'colorscale': 'RdYlGn',
        'higher_is': 'better',
        'description': 'Percentage change in Awp relative to the previous year.',
    },
    'tawp_pct': {
        'label':    'Trend in Awp since 2018 (tAwp)',
        'unit':     '%',
        'format':   '+,.1f',
        'colorscale': 'RdYlGn',
        'higher_is': 'better',
        'description': 'Percentage change in Awp relative to the 2018 baseline.',
    },
    'vetb_Mm3': {
        'label':    'Blue ET volume over irrigated land (VETb)',
        'unit':     'Mm³/year',
        'format':   ',.1f',
        'colorscale': 'Blues',
        'higher_is': None,
        'description': (
            'Annual volume of blue evapotranspiration over '
            'irrigation-weighted pixels. Stored as m³ in the CSV; displayed as Mm³.'
        ),
    },
    'gva_agriculture_usd': {
        'label':    'Agricultural GVA',
        'unit':     'USD/year',
        'format':   ',.0f',
        'colorscale': 'Oranges',
        'higher_is': None,
        'description': (
            'Agriculture, forestry and fishing value added (current US$). '
            'Note: includes forestry and fishing.'
        ),
    },
    'irr_area_ha': {
        'label':    'Irrigation-weighted area',
        'unit':     'ha',
        'format':   ',.0f',
        'colorscale': 'Greens',
        'higher_is': None,
        'description': (
            'Effective irrigated area derived from the irrigation weight layer '
            '(Σ pixel_area_ha × irrigation_weight). Source recorded in '
            'landuse_source column.'
        ),
    },
    'ETb_annual_mm': {
        'label':    'Annual blue ET depth (ETb)',
        'unit':     'mm/year',
        'format':   ',.0f',
        'colorscale': 'PuBu',
        'higher_is': None,
        'description': (
            'Area-weighted mean annual blue evapotranspiration depth '
            'over irrigation-weighted pixels.'
        ),
    },
    'AETI_annual_mm': {
        'label':    'Annual AETI depth',
        'unit':     'mm/year',
        'format':   ',.0f',
        'colorscale': 'GnBu',
        'higher_is': None,
        'description': (
            'Area-weighted mean annual actual evapotranspiration and '
            'interception over irrigation-weighted pixels.'
        ),
    },
}

INDICATOR_OPTIONS = {v['label']: k for k, v in INDICATORS.items()}

# ── Quality flag descriptions ─────────────────────────────────────────────────
QUALITY_FLAGS = {
    'OK':                    'All key inputs available; indicator calculated normally.',
    'MISSING_GVA':           'GVA data missing - Awp not calculated.',
    'MISSING_CR':            'Cr unavailable and no fallback applied - Awp not calculated.',
    'CR_COUNTRY_FIXED':      'Country fixed Cr used (no annual value available).',
    'CR_REGIONAL_DEFAULT':   'Regional average Cr used - moderate confidence.',
    'CR_GLOBAL_DEFAULT':     'Global default Cr used - low confidence.',
    'ZERO_VETB':             'VETb ≤ 0 - Awp not calculated.',
    'LOW_GMIE_AREA':         'Irrigated area below minimum threshold.',
    'NO_GMIE_IRRIGATION':    'No irrigated area detected in this country.',
    'GVA_FORESTRY_FISHING':  'Country has a large forestry/fishing sector; '
                             'GVA numerator likely overestimates irrigated ag value.',
    'BOUNDARY_MISMATCH':     'Country boundary or ISO-3 code mismatch suspected.',
    'PARTIAL_YEAR':          'WaPOR or PCP data incomplete for this year.',
    'OUTLIER_AWP':           'Awp is unusually high or low - review recommended.',
}

# ── Regions ───────────────────────────────────────────────────────────────────
REGIONS = [
    'Sub-Saharan Africa',
    'Middle East & North Africa',
    'South Asia',
    'East Asia & Pacific',
    'Europe & Central Asia',
    'Latin America & Caribbean',
    'North America',
]

INCOME_GROUPS = [
    'Low income',
    'Lower middle income',
    'Upper middle income',
    'High income',
]

# ── Unit helpers ──────────────────────────────────────────────────────────────
def to_Mm3(m3_series: pd.Series) -> pd.Series:
    """Convert m³ column to million m³ for display."""
    return m3_series / 1_000_000


def fmt_Mm3(val: float) -> str:
    """Format a Mm³ value for display."""
    if pd.isna(val):
        return '-'
    return f"{val:,.1f} Mm³"


def fmt_awp(val: float) -> str:
    """Format an Awp value for display."""
    if pd.isna(val):
        return '-'
    return f"${val:.4f}/m³"


def fmt_usd(val: float) -> str:
    """Format a USD value (GVA) for display."""
    if pd.isna(val):
        return '-'
    if val >= 1e9:
        return f"${val/1e9:.1f}B"
    if val >= 1e6:
        return f"${val/1e6:.1f}M"
    return f"${val:,.0f}"


# ── Data loader ───────────────────────────────────────────────────────────────
def load_data() -> tuple[pd.DataFrame, dict]:
    """Load the main CSV and (optionally) GeoJSON. Returns (df, geojson_dict).

    GeoJSON is optional: choropleth pages use Plotly's built-in Natural Earth
    boundaries (locations='iso3'), so they work without the file.  Pages that
    need custom polygons should check ``geojson is not None`` before using it.
    """
    df = pd.read_csv(DATA_FINAL, dtype={'iso3': str})

    # Derived display column: VETb in Mm³
    if 'vetb_m3' in df.columns:
        df['vetb_Mm3'] = to_Mm3(df['vetb_m3'])
    elif 'VETb_m3' in df.columns:
        df['vetb_Mm3'] = to_Mm3(df['VETb_m3'])

    # Backward-compat: rename old gmie_area_ha column if present
    if 'gmie_area_ha' in df.columns and 'irr_area_ha' not in df.columns:
        df = df.rename(columns={'gmie_area_ha': 'irr_area_ha'})

    # Column-name normalisation for case differences
    col_map = {c.lower(): c for c in df.columns}
    for expected in ('ETb_annual_mm', 'AETI_annual_mm', 'VETb_m3'):
        lower = expected.lower()
        if expected not in df.columns and lower in col_map:
            df = df.rename(columns={col_map[lower]: expected})

    geojson: dict | None = None
    if GEOJSON.exists():
        with open(GEOJSON, encoding='utf-8') as f:
            geojson = json.load(f)

    return df, geojson
