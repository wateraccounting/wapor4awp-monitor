"""
4_Methodology_and_Download.py - full methodology, quality flags, data download.
"""

import streamlit as st
import pandas as pd
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from utils import load_data, INDICATORS, QUALITY_FLAGS
import branding

branding.apply(subtitle='Methodology & Data Download', show_logo=False)

# ── Load data for download ────────────────────────────────────────────────────
@st.cache_data
def get_data():
    return load_data()

try:
    df, _ = get_data()
    data_available = True
except FileNotFoundError:
    data_available = False

# ── Tabs ──────────────────────────────────────────────────────────────────────
tab_about, tab_method, tab_flags, tab_manual, tab_data = st.tabs([
    'About', 'Methodology', 'Quality Flags', 'Manual', 'Download'
])

# ══════════════════════════════════════════════════════════════════════════════
with tab_about:
    st.header('WaPOR4Awp Monitor - Agricultural Water Productivity')
    st.markdown("""
Agricultural Water Productivity (Awp) measures the economic value of irrigated
crop production per unit of blue water consumed:
""")
    st.latex(r'Awp = \dfrac{GVA_a \times (1 - C_r)}{V_{ETb}} \quad [\text{USD/m}^3]')
    st.markdown("""
| Symbol | Description |
|--------|-------------|
| *GVA_a* | Agriculture, forestry & fishing value added (current USD) |
| *C_r* | Crop ratio - non-irrigated fraction of *GVA_a* |
| *V_ETb* | Annual blue ET volume over irrigated land (m³/year) |

---

### Dashboard pages

| Page | What you can do |
|------|----------------|
| **Global Overview** | Animated choropleth map across all years; click any country for a detailed pop-out |
| **Country Explorer** | Time-series charts for one or more selected countries |
| **Rankings & Comparison** | Top/bottom rankings, regional box plots, income-group comparisons |
| **Methodology & Download** | Full derivation, quality flags, and filtered data export |

---

### About this dataset

This dashboard presents country-level Agricultural Water Productivity (Awp)
derived from WaPOR satellite remote-sensing data (FAO) for the period
2018–present. The **Awp methodology was developed by IHE Delft in
collaboration with FAO**.

For the full derivation and data quality information, see the **Methodology**
and **Quality Flags** tabs above.
""")

# ══════════════════════════════════════════════════════════════════════════════
with tab_method:
    st.header('Agricultural Water Productivity - Derivation')

    # ── Concept ───────────────────────────────────────────────────────────────
    st.subheader('Concept')
    st.markdown("""
Agricultural Water Productivity (Awp) measures the **economic value of
irrigated crop production per unit of blue water consumed**.

*Blue water* refers to water from rivers, lakes, and aquifers - the water
that irrigation actually withdraws and consumes. *Green water* (rainfall
stored in soil) is shared by rainfed and irrigated systems and is excluded
from the productivity ratio so the indicator isolates the value generated
specifically by irrigation.

**SDG 6.4.1 alignment.** SDG 6.4.1 measures water-use efficiency as USD
value added per m³ of water withdrawn. WaPOR4Awp Monitor adapts this concept
for the agricultural sector, using satellite-derived consumption (blue ET)
instead of withdrawals - a more accurate indicator of net water use in
regions where return flows are significant.
""")

    st.divider()

    # ── Core formula ──────────────────────────────────────────────────────────
    st.subheader('Core formula')
    st.latex(r'Awp = \dfrac{GVA_a \times (1 - C_r)}{V_{ETb}} \quad [\text{USD/m}^3]')
    st.markdown("""
| Symbol | Description |
|--------|-------------|
| *GVA_a* | Agriculture, forestry & fishing value added (current USD) |
| *C_r* | Crop ratio: non-irrigated fraction of *GVA_a* |
| *V_ETb* | Annual blue ET volume over irrigated land (m³/year) |
""")

    st.divider()

    # ── Component derivation: GVAa ────────────────────────────────────────────
    st.subheader('Agricultural value added: GVAa')
    st.markdown("""
Annual, country-level agricultural value added in current US dollars.
Includes forestry and fishing alongside agriculture, which inflates Awp in
countries with large forestry or fishing sectors. Such cases are flagged
with `GVA_FORESTRY_FISHING` and should be interpreted with caution.
""")

    st.divider()

    # ── Component derivation: Cr ──────────────────────────────────────────────
    st.subheader('Crop ratio: Cr')
    st.markdown("""
Cr is the fraction of agricultural value added that comes from
**non-irrigated** activities (rainfed crops, forestry, fishing, livestock).
The factor (1 − Cr) extracts the irrigated share of GVAa.

**Fallback hierarchy** (each step recorded in the `cr_source` column and
the corresponding `CR_*` quality flag):

1. **AQUASTAT-derived** *(preferred)*: Cr = 1 − (irrigated area / total
   cultivated area), computed per country-year.
2. **Country fixed**: literature-based value when no annual data is available.
3. **Regional default**: World Bank region average.
4. **Global default**: Cr = 0.80 *(last resort)*.

Country-level uncertainty is approximately ±15–25%.
""")

    st.divider()

    # ── VETb derivation ───────────────────────────────────────────────────────
    st.subheader('Blue ET volume: VETb')

    st.markdown('**Step 1 - Effective precipitation** (Brouwer & Heibloem 1986, per pixel per month):')
    st.markdown("""
| Monthly rainfall *P* (mm) | Effective precipitation *Pe* |
|---------------------------|------------------------------|
| *P* ≤ 16.67 | *Pe* = 0 |
| 16.67 < *P* ≤ 75 | *Pe* = 0.6 × *P* − 10 |
| *P* > 75 | *Pe* = 0.8 × *P* − 25 |

The two segments are continuous at *P* = 75 mm/month (*Pe* = 35 mm).
The zero-threshold at *P* = 16.67 mm ensures *Pe* ≥ 0.
""")

    st.markdown('**Step 2 - Monthly blue ET** (per pixel):')
    st.latex(r'ET_{b,\text{month}} = \max\!\left(AETI_{\text{month}} - P_{e,\text{month}},\ 0\right)')

    st.markdown('**Step 3 - Annual sum** (per pixel):')
    st.latex(r'ET_{b,\text{annual}} = \sum_{m=1}^{12} ET_{b,m} \quad [\text{mm/year}]')

    st.markdown(
        '**Step 4 - Irrigation-weighted volume** (per pixel), where *A_pixel* is the '
        'pixel area in m² and *f_irr* ∈ [0, 1] is the irrigation fraction:'
    )
    st.latex(
        r'V_{ETb,\text{pixel}} = \dfrac{ET_{b,\text{annual}}}{1000}'
        r'\times A_{\text{pixel}} \times f_{\text{irr}}'
    )

    st.markdown('**Step 5 - Country total:**')
    st.latex(r'V_{ETb} = \sum_{\text{pixels} \in \text{country}} V_{ETb,\text{pixel}} \quad [\text{m}^3/\text{year}]')

    st.divider()

    # ── Derived indicators ────────────────────────────────────────────────────
    st.subheader('Derived indicators')
    st.markdown("""
| Indicator | Formula | Unit |
|-----------|---------|------|
| cAwp - year-to-year change | *(Awp_t − Awp_{t−1}) / Awp_{t−1} × 100* | % |
| tAwp - trend since 2018 | *(Awp_t − Awp_2018) / Awp_2018 × 100* | % |

Baseline year: **2018** (first full year of WaPOR data coverage).
""")

    st.divider()

    # ── Data sources ──────────────────────────────────────────────────────────
    st.subheader('Data sources')
    st.markdown("""
| Dataset | Used for | Resolution | GEE asset / Source |
|---------|----------|-----------|---------------------|
| [WaPOR v3 L1-AETI-D](https://data.apps.fao.org/wapor) | Crop water consumption (AETI, dekadal) | 300 m | `FAO/WAPOR/3/L1_AETI_D` |
| [CHIRPS Daily](https://www.chc.ucsb.edu/data/chirps) | Effective precipitation *Pe* | ~5 km | `UCSB-CHG/CHIRPS/DAILY` |
| [GMIE-100](https://essd.copernicus.org/articles/17/855/2025/) | Sub-pixel irrigation proportion (0-1) | ~100 m | `projects/wu-rsdata/assets/gmie` |
| [World Bank NV.AGR.TOTL.CD](https://data.worldbank.org/indicator/NV.AGR.TOTL.CD) | GVAa (current US$, annual, country) | country | World Bank Open Data |
| [FAO AQUASTAT](https://www.fao.org/aquastat) | Cr (irrigated and cultivated area statistics) | country | FAO AQUASTAT portal |
| [Brouwer & Heibloem 1986](https://www.fao.org/3/s2022e/s2022e00.htm) | Effective precipitation formula | - | FAO Training Manual no. 3 |
| [USDOS LSIB Simple 2017](https://developers.google.com/earth-engine/datasets/catalog/USDOS_LSIB_SIMPLE_2017) | Country reduction polygons | vector | `USDOS/LSIB_SIMPLE/2017` |

> **Note on the dashboard UI:** other pages refer to these inputs by generic
> terms (*"AETI", "daily precipitation", "irrigation-weighted area",
> "agricultural GVA"*). This table is the authoritative attribution for
> citation, validation, and replication.
""")

    st.divider()

    # ── Known limitations ─────────────────────────────────────────────────────
    st.subheader('Known limitations')
    st.markdown("""
1. **GVA includes forestry and fishing**. Countries with large forestry or
   fishing sectors will have Awp overestimated.
   Flagged as `GVA_FORESTRY_FISHING` in the quality flag column.

2. **Cr uncertainty**: The crop ratio is derived from area proxies or literature,
   not direct economic surveys. Country-level uncertainty is approximately ±15–25%.

3. **Irrigation fraction (GMIE-100)**: ~100 m, observation period 2010–2019.
   May not reflect recent irrigation expansion or abandonment.

4. **WaPOR data coverage starts 2018**. The baseline year is 2018 by definition,
   so tAwp = 0 for all countries in 2018.

5. **Humid-country Awp**: In countries where annual rainfall covers most crop
   water needs, blue ET (VETb) is near zero and Awp is not computed
   (flagged `ZERO_VETB`). These countries show no irrigated blue-water demand,
   not a data error.
""")

# ══════════════════════════════════════════════════════════════════════════════
with tab_flags:
    st.header('Quality Flags')
    st.markdown(
        "Each row in the dataset carries a comma-separated `quality_flag` field. "
        "Multiple flags may apply to a single country-year."
    )

    rows = [
        {'Flag': flag, 'Description': desc}
        for flag, desc in QUALITY_FLAGS.items()
    ]
    flag_df = pd.DataFrame(rows)
    st.dataframe(flag_df, use_container_width=True, hide_index=True)

    st.markdown("""
**Recommended data use by flag:**

| Use case | Recommended filter |
|----------|--------------------|
| Peer-reviewed analysis | `OK` only |
| Country-level planning | `OK` + `CR_COUNTRY_FIXED` |
| Global overview map | `OK` + `CR_*` flags |
| All data (with caveats) | No filter |
""")

# ══════════════════════════════════════════════════════════════════════════════
with tab_manual:
    st.header('Dashboard Manual & Guidelines')

    _MANUAL_PATH = Path(__file__).parent.parent.parent / 'docs' / 'WaPOR4Awp_Monitor_Manual.md'
    try:
        _manual_md = _MANUAL_PATH.read_text(encoding='utf-8')
        st.download_button(
            label     = '⬇ Download Manual (Markdown)',
            data      = _manual_md.encode('utf-8'),
            file_name = 'WaPOR4Awp_Monitor_Manual.md',
            mime      = 'text/markdown',
        )
        st.divider()
        st.markdown(_manual_md)
    except FileNotFoundError:
        st.error(f'Manual file not found at {_MANUAL_PATH}.')

# ══════════════════════════════════════════════════════════════════════════════
with tab_data:
    st.header('Download Dataset')

    if not data_available:
        st.warning(
            "Dataset not yet generated. "
            "Complete the GEE and Python processing pipeline first."
        )
    else:
        # Dataset overview
        years   = sorted(df['year'].unique())
        n_ctry  = df['iso3'].nunique()
        n_ok    = df['quality_flag'].str.startswith('OK').sum()

        col1, col2, col3 = st.columns(3)
        col1.metric('Countries', n_ctry)
        col2.metric('Years', f"{years[0]}–{years[-1]}")
        col3.metric('OK quality rows', n_ok)

        st.markdown('#### Filter before download')

        dl_years = st.multiselect(
            'Years', options=years, default=years
        )
        dl_flags = st.multiselect(
            'Quality flags to include (leave empty to download all rows)',
            options=list(QUALITY_FLAGS.keys()),
            default=[],
        )
        dl_cols_awp = st.checkbox('Include Awp and derived indicators', value=True)
        dl_cols_components = st.checkbox('Include component columns (VETb, GVA, Cr, ETb)', value=True)

        # Build download DataFrame
        dl_df = df[df['year'].isin(dl_years)].copy()

        if dl_flags:
            mask = dl_df['quality_flag'].apply(
                lambda f: any(flag in f.split(',') for flag in dl_flags)
            )
            dl_df = dl_df[mask]

        keep_cols = ['iso3', 'country_name_standard', 'wb_region', 'wb_income', 'year', 'quality_flag']
        if dl_cols_awp:
            keep_cols += ['awp_usd_per_m3', 'cawp_pct', 'tawp_pct']
        if dl_cols_components:
            keep_cols += ['VETb_m3', 'vetb_Mm3', 'gva_agriculture_usd',
                          'cr_value', 'cr_source', 'irr_area_ha',
                          'ETb_annual_mm', 'AETI_annual_mm']
        keep_cols = [c for c in keep_cols if c in dl_df.columns]
        dl_df = dl_df[keep_cols]

        st.markdown(f"**{len(dl_df)} rows** ready for download")

        csv_bytes = dl_df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label     = 'Download CSV',
            data      = csv_bytes,
            file_name = 'wapor4awp_global.csv',
            mime      = 'text/csv',
        )

        with st.expander('Preview (first 50 rows)'):
            st.dataframe(dl_df.head(50), use_container_width=True)

    st.markdown("""
---
### Citation

If you use this data, please cite:

> Yalew, S. & Mul, M. (2026). *WaPOR4AWP Global: Annual Agricultural Water
> Productivity - Dashboard and Dataset.*
> IHE Delft / FAO.

### Licence

This dataset and dashboard are produced by IHE Delft and FAO and provided under
[CC BY-NC-SA 3.0 IGO](https://creativecommons.org/licenses/by-nc-sa/3.0/igo/).
""")

branding.footer()
