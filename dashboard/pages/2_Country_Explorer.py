"""
2_Country_Explorer.py - time-series and comparison for selected countries.
"""

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from utils import load_data, INDICATORS, INDICATOR_OPTIONS, fmt_awp, fmt_Mm3, fmt_usd
import branding

branding.apply(subtitle='Country Explorer', show_logo=False)

# ── Load data ─────────────────────────────────────────────────────────────────
@st.cache_data
def get_data():
    return load_data()

try:
    df, _ = get_data()
except FileNotFoundError as e:
    st.error(f"Data not found: {e}")
    st.stop()

# Build country list (use dashboard_name where available, fall back to iso3)
name_col = 'dashboard_name' if 'dashboard_name' in df.columns else 'country_name_standard'
_names = df[['iso3', name_col]].drop_duplicates().copy()
_names[name_col] = _names[name_col].fillna(_names['iso3'])  # replace NaN with iso3
country_options = (
    _names.sort_values(name_col)
    .set_index('iso3')[name_col]
    .to_dict()
)

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.header('Controls')

    selected_iso3 = st.multiselect(
        'Countries',
        options    = list(country_options.keys()),
        default    = ['EGY', 'IND', 'ETH', 'NLD'],
        format_func = lambda x: country_options.get(x, x),
    )

    selected_label = st.selectbox(
        'Primary indicator',
        options = list(INDICATOR_OPTIONS.keys()),
        index   = 0,
    )
    col  = INDICATOR_OPTIONS[selected_label]
    meta = INDICATORS[col]

    show_components = st.checkbox(
        'Show VETb and GVA components',
        value=False,
        help='Adds secondary charts for the VETb and GVA components.'
    )

    st.markdown('---')
    st.markdown(f"**{meta['label']}**")
    st.markdown(f"*{meta['description']}*")

if not selected_iso3:
    st.info('Select at least one country from the sidebar.')
    st.stop()

# ── Filter ────────────────────────────────────────────────────────────────────
df_sel = df[df['iso3'].isin(selected_iso3)].copy()
df_sel[name_col] = df_sel['iso3'].map(country_options)

years = sorted(df_sel['year'].unique())

# ── Primary time-series chart ─────────────────────────────────────────────────
st.subheader(f'{meta["label"]} over time')

display_col = col
if col == 'vetb_Mm3' and 'vetb_Mm3' not in df_sel.columns and 'VETb_m3' in df_sel.columns:
    df_sel['vetb_Mm3'] = df_sel['VETb_m3'] / 1_000_000

fig_ts = px.line(
    df_sel.dropna(subset=[display_col]),
    x          = 'year',
    y          = display_col,
    color      = name_col,
    markers    = True,
    labels     = {display_col: meta['unit'], 'year': 'Year', name_col: 'Country'},
    color_discrete_sequence = px.colors.qualitative.Set2,
)
fig_ts.update_layout(
    height    = 400,
    legend    = dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1),
    hovermode = 'x unified',
)
fig_ts.update_traces(line_width=2.5, marker_size=8)
st.plotly_chart(fig_ts, use_container_width=True, config={'displayModeBar': False})

# ── Component charts ──────────────────────────────────────────────────────────
if show_components:
    c1, c2 = st.columns(2)

    with c1:
        st.subheader('VETb (Mm³/year)')
        if 'vetb_Mm3' in df_sel.columns or 'VETb_m3' in df_sel.columns:
            if 'vetb_Mm3' not in df_sel.columns:
                df_sel['vetb_Mm3'] = df_sel['VETb_m3'] / 1_000_000
            fig_vetb = px.bar(
                df_sel.dropna(subset=['vetb_Mm3']),
                x='year', y='vetb_Mm3', color=name_col, barmode='group',
                labels={'vetb_Mm3': 'Mm³/year', 'year': 'Year'},
                color_discrete_sequence=px.colors.qualitative.Set2,
            )
            fig_vetb.update_layout(height=320, showlegend=False)
            st.plotly_chart(fig_vetb, use_container_width=True, config={'displayModeBar': False})

    with c2:
        st.subheader('Agricultural GVA (USD)')
        if 'gva_agriculture_usd' in df_sel.columns:
            fig_gva = px.bar(
                df_sel.dropna(subset=['gva_agriculture_usd']),
                x='year', y='gva_agriculture_usd', color=name_col, barmode='group',
                labels={'gva_agriculture_usd': 'USD/year', 'year': 'Year'},
                color_discrete_sequence=px.colors.qualitative.Set2,
            )
            fig_gva.update_layout(height=320, showlegend=False)
            st.plotly_chart(fig_gva, use_container_width=True, config={'displayModeBar': False})

# ── cAwp and tAwp ─────────────────────────────────────────────────────────────
st.subheader('Year-to-year change (cAwp) and trend since 2018 (tAwp)')

c1, c2 = st.columns(2)

with c1:
    if 'cawp_pct' in df_sel.columns:
        fig_cawp = px.line(
            df_sel.dropna(subset=['cawp_pct']),
            x='year', y='cawp_pct',
            color=name_col, markers=True,
            labels={'cawp_pct': '% change', 'year': 'Year'},
            color_discrete_sequence=px.colors.qualitative.Set2,
            title='cAwp (%)',
        )
        fig_cawp.add_hline(y=0, line_dash='dash', line_color='grey')
        fig_cawp.update_layout(height=320, showlegend=True)
        st.plotly_chart(fig_cawp, use_container_width=True, config={'displayModeBar': False})

with c2:
    if 'tawp_pct' in df_sel.columns:
        fig_tawp = px.line(
            df_sel.dropna(subset=['tawp_pct']),
            x='year', y='tawp_pct',
            color=name_col, markers=True,
            labels={'tawp_pct': '% vs 2018', 'year': 'Year'},
            color_discrete_sequence=px.colors.qualitative.Set2,
            title='tAwp (% vs 2018 baseline)',
        )
        fig_tawp.add_hline(y=0, line_dash='dash', line_color='grey')
        fig_tawp.update_layout(height=320, showlegend=False)
        st.plotly_chart(fig_tawp, use_container_width=True, config={'displayModeBar': False})

# ── Data table ────────────────────────────────────────────────────────────────
with st.expander('Full data table for selected countries'):
    show_cols = [
        name_col, 'year', 'awp_usd_per_m3', 'cawp_pct', 'tawp_pct',
        'vetb_Mm3' if 'vetb_Mm3' in df_sel.columns else 'VETb_m3',
        'gva_agriculture_usd', 'cr_value', 'cr_source',
        'irr_area_ha', 'ETb_annual_mm', 'AETI_annual_mm', 'quality_flag',
    ]
    show_cols = [c for c in show_cols if c in df_sel.columns]
    st.dataframe(
        df_sel[show_cols].sort_values([name_col, 'year']).reset_index(drop=True),
        use_container_width=True
    )

branding.footer()
