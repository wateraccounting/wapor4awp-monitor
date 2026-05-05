"""
3_Rankings_and_Comparison.py - country rankings and regional comparisons.
"""

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import numpy as np
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from utils import load_data, INDICATORS, INDICATOR_OPTIONS, REGIONS, INCOME_GROUPS
import branding

branding.apply(subtitle='Rankings & Regional Comparison', show_logo=False)

# ── Load data ─────────────────────────────────────────────────────────────────
@st.cache_data
def get_data():
    return load_data()

try:
    df, _ = get_data()
except FileNotFoundError as e:
    st.error(f"Data not found: {e}")
    st.stop()

name_col = 'dashboard_name' if 'dashboard_name' in df.columns else 'country_name_standard'
years    = sorted(df['year'].unique())

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.header('Controls')

    selected_year = st.select_slider('Year', options=years, value=years[0])

    selected_label = st.selectbox(
        'Indicator',
        options=list(INDICATOR_OPTIONS.keys()),
        index=0,
    )
    col  = INDICATOR_OPTIONS[selected_label]
    meta = INDICATORS[col]

    top_n = st.slider('Number of countries', min_value=5, max_value=50, value=20)

    selected_regions = st.multiselect(
        'Filter by region',
        options=REGIONS,
        default=[],
        placeholder='All regions',
    )

    selected_income = st.multiselect(
        'Filter by income group',
        options=INCOME_GROUPS,
        default=[],
        placeholder='All income groups',
    )

    only_ok = st.checkbox('OK quality only', value=False,
                          help='Restrict to rows where all primary data sources were used. '
                               'Currently no rows qualify (fallback Cr is used for all countries).')

# ── Filter ────────────────────────────────────────────────────────────────────
df_yr = df[df['year'] == selected_year].copy()

if 'vetb_Mm3' not in df_yr.columns and 'VETb_m3' in df_yr.columns:
    df_yr['vetb_Mm3'] = df_yr['VETb_m3'] / 1_000_000

if only_ok:
    df_yr = df_yr[df_yr['quality_flag'].str.startswith('OK')]

if selected_regions:
    df_yr = df_yr[df_yr['wb_region'].isin(selected_regions)]

if selected_income:
    df_yr = df_yr[df_yr['wb_income'].isin(selected_income)]

display_col = col
df_plot = df_yr.dropna(subset=[display_col]).copy()
df_plot[name_col] = df_plot[name_col].fillna(df_plot['iso3'])

# ── Country ranking chart ─────────────────────────────────────────────────────
st.subheader(f'Top / Bottom {top_n} countries - {meta["label"]} ({selected_year})')

higher_better = meta.get('higher_is') == 'better'

top = df_plot.nlargest(top_n, display_col)
bot = df_plot.nsmallest(top_n, display_col)

tab_top, tab_bot = st.tabs([
    f'Top {top_n} ({"highest" if higher_better else "largest"})',
    f'Bottom {top_n} ({"lowest" if higher_better else "smallest"})',
])

with tab_top:
    fig_top = px.bar(
        top.sort_values(display_col, ascending=True),
        x             = display_col,
        y             = name_col,
        orientation   = 'h',
        color         = 'wb_region' if 'wb_region' in top.columns else None,
        labels        = {display_col: meta['unit'], name_col: ''},
        color_discrete_sequence = px.colors.qualitative.Pastel,
        text          = display_col,
    )
    fig_top.update_traces(texttemplate='%{x:.3g}', textposition='outside')
    fig_top.update_layout(height=max(400, top_n * 22), showlegend=True,
                          legend_title='Region')
    st.plotly_chart(fig_top, use_container_width=True, config={'displayModeBar': False})

with tab_bot:
    fig_bot = px.bar(
        bot.sort_values(display_col, ascending=False),
        x             = display_col,
        y             = name_col,
        orientation   = 'h',
        color         = 'wb_region' if 'wb_region' in bot.columns else None,
        labels        = {display_col: meta['unit'], name_col: ''},
        color_discrete_sequence = px.colors.qualitative.Pastel,
        text          = display_col,
    )
    fig_bot.update_traces(texttemplate='%{x:.3g}', textposition='outside')
    fig_bot.update_layout(height=max(400, top_n * 22), showlegend=False)
    st.plotly_chart(fig_bot, use_container_width=True, config={'displayModeBar': False})

# ── Regional box plot ─────────────────────────────────────────────────────────
if 'wb_region' in df_plot.columns:
    st.subheader(f'Regional distribution - {meta["label"]} ({selected_year})')

    region_order = (
        df_plot.groupby('wb_region')[display_col]
        .median()
        .sort_values(ascending=False)
        .index.tolist()
    )

    fig_box = px.box(
        df_plot,
        x             = 'wb_region',
        y             = display_col,
        color         = 'wb_region',
        points         = 'all',
        category_orders = {'wb_region': region_order},
        labels         = {display_col: meta['unit'], 'wb_region': 'Region'},
        color_discrete_sequence = px.colors.qualitative.Pastel,
        hover_name     = name_col,
    )
    fig_box.update_layout(height=450, showlegend=False,
                          xaxis_tickangle=-20)
    st.plotly_chart(fig_box, use_container_width=True, config={'displayModeBar': False})

# ── Income group comparison ───────────────────────────────────────────────────
if 'wb_income' in df_plot.columns:
    st.subheader(f'Income group comparison - {meta["label"]} ({selected_year})')

    income_order = [g for g in INCOME_GROUPS if g in df_plot['wb_income'].unique()]

    fig_inc = px.box(
        df_plot,
        x              = 'wb_income',
        y              = display_col,
        color          = 'wb_income',
        points          = 'all',
        category_orders = {'wb_income': income_order},
        labels          = {display_col: meta['unit'], 'wb_income': 'Income group'},
        color_discrete_sequence = px.colors.qualitative.Set3,
        hover_name      = name_col,
    )
    fig_inc.update_layout(height=400, showlegend=False)
    st.plotly_chart(fig_inc, use_container_width=True, config={'displayModeBar': False})

# ── Scatter: Awp vs GVA or VETb ──────────────────────────────────────────────
if col == 'awp_usd_per_m3':
    st.subheader('Awp vs VETb (bubble = irrigated area)')

    scatter_df = df_plot.dropna(subset=['awp_usd_per_m3', 'vetb_Mm3' if 'vetb_Mm3' in df_plot.columns else 'VETb_m3']).copy()
    y_col = 'vetb_Mm3' if 'vetb_Mm3' in scatter_df.columns else 'VETb_m3'
    y_label = 'VETb (Mm³/year)'

    fig_sc = px.scatter(
        scatter_df,
        x             = 'awp_usd_per_m3',
        y             = y_col,
        size          = 'irr_area_ha' if 'irr_area_ha' in scatter_df.columns else None,
        color         = 'wb_region' if 'wb_region' in scatter_df.columns else None,
        hover_name    = name_col,
        labels        = {'awp_usd_per_m3': 'Awp (USD/m³)', y_col: y_label},
        log_y         = True,
        color_discrete_sequence = px.colors.qualitative.Pastel,
        size_max      = 40,
    )
    fig_sc.update_layout(height=450)
    st.plotly_chart(fig_sc, use_container_width=True, config={'displayModeBar': False})

# ── Full ranking table ────────────────────────────────────────────────────────
with st.expander('Full ranking table'):
    rank_df = (
        df_plot[[name_col, 'iso3', 'wb_region', 'wb_income', display_col, 'quality_flag']]
        .sort_values(display_col, ascending=not higher_better)
        .reset_index(drop=True)
    )
    rank_df.index = rank_df.index + 1
    st.dataframe(rank_df, use_container_width=True)

branding.footer()
