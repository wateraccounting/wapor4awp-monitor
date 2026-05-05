"""
1_Global_Overview.py - choropleth world map with year controls and animation.
"""

import streamlit as st
import plotly.express as px
import pandas as pd
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from utils import load_data, INDICATORS, INDICATOR_OPTIONS, QUALITY_FLAGS, fmt_awp, fmt_Mm3, fmt_usd
import branding

branding.apply(subtitle='Global Overview', show_logo=False)

# ── Load data ─────────────────────────────────────────────────────────────────
@st.cache_data
def get_data():
    return load_data()

try:
    df, _ = get_data()
except FileNotFoundError as e:
    st.error(f"Data not found: {e}\nRun scripts 01-05 to generate the dataset.")
    st.stop()

years     = sorted(df['year'].unique())
name_col  = 'dashboard_name' if 'dashboard_name' in df.columns else 'country_name_standard'

# Fill NaN names with iso3 so widgets never receive NaN labels
df = df.copy()
df[name_col] = df[name_col].fillna(df['iso3'])

# ── Sidebar controls ──────────────────────────────────────────────────────────
with st.sidebar:
    st.header('Controls')

    selected_label = st.selectbox(
        'Indicator',
        options=list(INDICATOR_OPTIONS.keys()),
        index=0,
    )
    col_key = INDICATOR_OPTIONS[selected_label]
    meta    = INDICATORS[col_key]

    show_only_ok = st.checkbox('Show only "OK" quality flag', value=False)

    st.markdown('---')
    st.markdown(f"**{meta['label']}**")
    st.markdown(f"*{meta['description']}*")
    st.markdown(f"Unit: `{meta['unit']}`")

    # ── Featured Country (random per session) ──────────────────────────────
    st.markdown('---')
    st.markdown('#### Featured Country')

    if 'featured_iso3' not in st.session_state:
        _cands = (
            df[(df['year'] == years[-1]) & df['awp_usd_per_m3'].notna()]
        )
        if 'quality_flag' in _cands.columns:
            _cands = _cands[~_cands['quality_flag'].str.contains('OUTLIER_AWP', na=False)]
        if _cands.empty:
            _cands = df[df['awp_usd_per_m3'].notna()]
        if not _cands.empty:
            _pick = _cands.sample(1).iloc[0]
            st.session_state['featured_iso3'] = _pick['iso3']
            st.session_state['featured_year'] = int(_pick['year'])

    _fiso = st.session_state.get('featured_iso3')
    if _fiso:
        _fyr  = st.session_state.get('featured_year', years[-1])
        _frow = df[(df['iso3'] == _fiso) & (df['year'] == _fyr)]
        if not _frow.empty:
            _fr     = _frow.iloc[0]
            _fname  = _fr.get(name_col, _fiso)
            _fregion = _fr.get('wb_region', '')
            _fawp   = _fr.get('awp_usd_per_m3')
            _ftawp  = _fr.get('tawp_pct')
            _fflag  = _fr.get('quality_flag', '')

            st.markdown(f"**{_fname}**")
            if _fregion:
                st.caption(_fregion)
            if pd.notna(_fawp):
                st.metric('Awp', f"${_fawp:.3f}/m³", label_visibility='visible')
            if pd.notna(_ftawp):
                _delta_str = f"{_ftawp:+.1f}% vs 2018"
                st.metric('Trend (tAwp)', _delta_str)
            st.caption(f'Year: {_fyr} · *Changes each session*')

# ── Shared prep ───────────────────────────────────────────────────────────────
df_all = df.copy()
if show_only_ok:
    df_all = df_all[df_all['quality_flag'].str.startswith('OK')]

# Ensure vetb_Mm3 exists
if col_key == 'vetb_Mm3' and 'vetb_Mm3' not in df_all.columns and 'VETb_m3' in df_all.columns:
    df_all['vetb_Mm3'] = df_all['VETb_m3'] / 1_000_000

# Fixed color range across ALL years (keeps animation colours comparable)
all_vals = df_all[col_key].dropna()
if len(all_vals) > 4:
    vmin = all_vals.quantile(0.02)
    vmax = all_vals.quantile(0.98)
else:
    vmin = float(all_vals.min()) if len(all_vals) else 0.0
    vmax = float(all_vals.max()) if len(all_vals) else 1.0

if meta.get('higher_is') == 'better' and col_key in ('cawp_pct', 'tawp_pct'):
    abs_max = max(abs(vmin), abs(vmax), 1)
    vmin, vmax = -abs_max, abs_max

hover_data = {col_key: True, 'quality_flag': True}

geo_style = dict(
    showframe=False,
    showcoastlines=True,
    coastlinecolor='#cccccc',
    showcountries=True,
    countrycolor='#eeeeee',
    bgcolor='#f8f8f8',
)
cbar = dict(title=meta['unit'], thickness=15, len=0.7)

# cAwp boundary years shown with a notice in Map View.
# 2018 = first WaPOR year (no prior year). 2025 = incomplete/not yet published.
# Animation only excludes 2018 (starts at 2019); 2025 stays in animation.
_CAWP_NA = frozenset({years[0], years[-1]})

# ── Tabs ──────────────────────────────────────────────────────────────────────
tab_map, tab_anim = st.tabs(['Map View', 'Animated Time Series'])


# ════════════════════════════════════════════════════════════════════════════
# TAB 1 - static map for a single selected year + click-to-popout
# ════════════════════════════════════════════════════════════════════════════
with tab_map:
    selected_year = st.select_slider(
        'Year', options=years, value=years[0], key='year_slider_map'
    )

    df_year = df_all[df_all['year'] == selected_year].copy()

    # cAwp notice for boundary years
    _cawp_na = col_key == 'cawp_pct' and selected_year in _CAWP_NA
    if _cawp_na:
        if selected_year == years[0]:
            _msg = (
                f"**cAwp - Not available for {selected_year}.**  \n"
                f"{selected_year} is the first year of WaPOR data - no prior year exists "
                f"for comparison. Select **{years[1]}** or later to view cAwp."
            )
        else:
            _msg = (
                f"**cAwp - Not available for {selected_year}.**  \n"
                f"Awp data for {selected_year} is incomplete or not yet published, "
                f"so a reliable year-to-year comparison cannot be shown. "
                f"Select **{years[-2]}** or earlier to view cAwp."
            )
        st.warning(_msg)

    if not _cawp_na:
        valid   = df_year[col_key].notna()
        n_valid = valid.sum()
        n_total = len(df_year)

        # Per-country rank for the selected indicator (rank 1 = highest value)
        _rank_df = df_year[['iso3', col_key]].dropna(subset=[col_key]).copy()
        _rank_df['rank'] = _rank_df[col_key].rank(ascending=False, method='min').astype(int)

        # ── Top metrics ─────────────────────────────────────────────────────
        m1, m2, m3, m4 = st.columns(4)
        m1.metric('Year', selected_year)
        m2.metric('Countries ranked', f"{n_valid} / {n_total}")

        if col_key == 'awp_usd_per_m3' and n_valid > 0:
            m3.metric('Median Awp', fmt_awp(df_year.loc[valid, col_key].median()))
        elif col_key == 'vetb_Mm3' and n_valid > 0:
            m3.metric('Total VETb', fmt_Mm3(df_year.loc[valid, col_key].sum()))
        elif col_key == 'gva_agriculture_usd' and n_valid > 0:
            m3.metric('Total GVA', fmt_usd(df_year.loc[valid, col_key].sum()))

        if n_valid > 0:
            candidates = df_year.loc[valid].copy()
            if 'quality_flag' in candidates.columns:
                candidates = candidates[
                    ~candidates['quality_flag'].str.contains('OUTLIER_AWP', na=False)
                ]
            if not candidates.empty:
                top = candidates.nlargest(1, col_key).iloc[0]
                m4.metric('Highest', top.get(name_col, top['iso3']))

        # ── Static choropleth ────────────────────────────────────────────────
        fig_static = px.choropleth(
            df_year,
            locations               = 'iso3',
            color                   = col_key,
            hover_name              = name_col,
            hover_data              = hover_data,
            color_continuous_scale  = meta['colorscale'],
            range_color             = (vmin, vmax),
            labels                  = {col_key: meta['unit']},
            projection              = 'natural earth',
        )
        fig_static.update_layout(
            margin             = {'r': 0, 't': 10, 'l': 0, 'b': 0},
            height             = 510,
            coloraxis_colorbar = cbar,
            geo                = geo_style,
        )

        map_event = st.plotly_chart(
            fig_static,
            use_container_width=True,
            on_select='rerun',
            key='world_map_static',
            config={'displayModeBar': False},
        )

        # ── Country popout on click ──────────────────────────────────────────
        clicked_iso3 = None
        if map_event and map_event.selection and map_event.selection.points:
            clicked_iso3 = map_event.selection.points[0].get('location')

        if clicked_iso3:
            country_yr  = df_year[df_year['iso3'] == clicked_iso3]
            country_all = df[df['iso3'] == clicked_iso3].sort_values('year')
            cname = (
                country_yr[name_col].values[0]
                if not country_yr.empty and pd.notna(country_yr[name_col].values[0])
                else clicked_iso3
            )

            _crank = _rank_df.loc[_rank_df['iso3'] == clicked_iso3, 'rank']
            _rank_str = f"#{int(_crank.values[0])} of {n_valid}" if not _crank.empty else '-'

            st.markdown(
                f'### {cname} ({clicked_iso3}) - {selected_year}'
                f'&ensp;<span style="font-size:0.85rem;color:#3d7575;font-weight:600;">'
                f'Rank {_rank_str} · {meta["label"]}</span>',
                unsafe_allow_html=True,
            )

            if country_yr.empty:
                st.info('No data for this country in the selected year.')
            else:
                row = country_yr.iloc[0]
                awp_val  = row.get('awp_usd_per_m3')
                vetb_val = row.get('VETb_m3')
                gva_val  = row.get('gva_agriculture_usd')
                area_val = row.get('irr_area_ha')
                etb_val  = row.get('ETb_annual_mm')
                tawp     = row.get('tawp_pct')
                cawp     = row.get('cawp_pct')
                flag     = row.get('quality_flag', '')
                region   = row.get('wb_region', '')

                c1, c2, c3, c4, c5 = st.columns(5)
                c1.metric('Awp (USD/m³)',   f"{awp_val:.3f}"      if pd.notna(awp_val)  else 'N/A')
                c2.metric('VETb (Mm³)',     f"{vetb_val/1e6:.1f}" if pd.notna(vetb_val) else 'N/A')
                c3.metric('Agric. GVA',     fmt_usd(gva_val)      if pd.notna(gva_val)  else 'N/A')
                c4.metric('Irr. area (ha)', f"{area_val:,.0f}"    if pd.notna(area_val) else 'N/A')
                c5.metric('ETb (mm/yr)',    f"{etb_val:.0f}"      if pd.notna(etb_val)  else 'N/A')

                d1, d2, d3 = st.columns(3)
                d1.metric('tAwp vs 2018',   f"{tawp:+.1f}%"  if pd.notna(tawp)  else 'N/A')
                d2.metric('cAwp prev year', f"{cawp:+.1f}%"  if pd.notna(cawp)  else 'N/A')
                d3.metric('Region', region or 'N/A')
                st.caption(f"Quality flag: `{flag}`")

                ts = country_all[['year', 'awp_usd_per_m3']].dropna(subset=['awp_usd_per_m3'])
                if not ts.empty:
                    fig_bar = px.bar(
                        ts, x='year', y='awp_usd_per_m3',
                        labels={'awp_usd_per_m3': 'Awp (USD/m³)', 'year': 'Year'},
                        title=f'Awp {years[0]}–{years[-1]} - {cname}',
                        color='awp_usd_per_m3',
                        color_continuous_scale='YlGn',
                    )
                    fig_bar.update_layout(
                        height=270, showlegend=False,
                        coloraxis_showscale=False,
                        margin={'t': 40, 'b': 10, 'l': 0, 'r': 0},
                    )
                    st.plotly_chart(fig_bar, use_container_width=True,
                                    config={'displayModeBar': False})

            st.divider()

        # ── Country table ────────────────────────────────────────────────────
        with st.expander('Country data table - ranked by selected indicator'):
            tbl_cols = ['iso3', name_col, 'wb_region', col_key, 'quality_flag']
            tbl_cols = [c for c in tbl_cols if c in df_year.columns]
            st.dataframe(
                df_year[tbl_cols].sort_values(col_key, ascending=False).reset_index(drop=True),
                use_container_width=True,
            )

    with st.expander('Quality flag descriptions'):
        for flag, desc in QUALITY_FLAGS.items():
            st.markdown(f"**`{flag}`** - {desc}")


# ════════════════════════════════════════════════════════════════════════════
# TAB 2 - animated choropleth stepping through all years
# ════════════════════════════════════════════════════════════════════════════
with tab_anim:

    # ── Pre-compute aggregates (used for KPI strip below the map) ─────────────
    df_anim = df_all.sort_values(['year', 'iso3']).copy()

    # cAwp animation starts at 2019 (2018 has no prior year).
    # 2025 stays in the animation - grey countries simply mean no data yet.
    if col_key == 'cawp_pct':
        df_anim = df_anim[df_anim['year'] != years[0]]

    _anim_years = sorted(df_anim['year'].unique())
    _anim_first = _anim_years[0]  if _anim_years else years[0]
    _anim_last  = _anim_years[-1] if _anim_years else years[-1]

    _agg = (
        df_anim.dropna(subset=[col_key])
        .groupby('year')[col_key]
        .agg(['median', 'mean', 'count'])
        .reset_index()
    )
    _first_df = _agg[_agg['year'] == _anim_first]
    _last_df  = _agg[_agg['year'] == _anim_last]
    _first = _first_df.iloc[0] if len(_first_df) else None
    _last  = _last_df.iloc[0]  if len(_last_df)  else None

    frame_ms = 5000   # 5 s per year (first frame overridden to 500 ms below)

    # ── Animated choropleth ───────────────────────────────────────────────────
    fig_anim = px.choropleth(
        df_anim,
        locations               = 'iso3',
        color                   = col_key,
        animation_frame         = 'year',
        hover_name              = name_col,
        hover_data              = hover_data,
        color_continuous_scale  = meta['colorscale'],
        range_color             = (vmin, vmax),
        labels                  = {col_key: meta['unit'], 'year': 'Year'},
        projection              = 'natural earth',
    )

    # ── Play / Pause buttons - top-LEFT, above the year bar ──────────────────
    if fig_anim.layout.updatemenus:
        um = fig_anim.layout.updatemenus[0]

        # Loop 5× through all animation years, return to first frame at end
        frame_names = [str(f.name) for f in fig_anim.frames]
        _loop_frames = frame_names * 5 + [frame_names[0]]

        # Replace full args in one call (args is an immutable tuple - cannot assign by index)
        um.buttons[0].update(args=[
            _loop_frames,
            {
                'frame':       {'duration': frame_ms, 'redraw': True},
                'fromcurrent': True,
                'transition':  {'duration': 200, 'easing': 'linear'},
                'mode':        'immediate',
            },
        ])

        um.buttons[0].label = '▶  Play'
        um.buttons[1].label = '⏸  Pause'
        fig_anim.layout.updatemenus[0].update(
            showactive  = True,
            active      = 1,
            type        = 'buttons',
            direction   = 'right',   # buttons extend rightward from left anchor
            font        = {'size': 15, 'color': '#1a1a1a'},
            bgcolor     = '#ffffff',
            bordercolor = '#3d7575',
            borderwidth = 2,
            pad         = {'t': 8, 'b': 8, 'l': 18, 'r': 18},
            x           = 0.0,
            xanchor     = 'left',
            y           = 1.18,
            yanchor     = 'bottom',
        )

    # ── Year watermark - tracks each animation frame ──────────────────────────
    def _yr_annotation(yr):
        return dict(
            text      = str(yr),
            x=0.01, y=0.18,
            xref='paper', yref='paper',
            showarrow = False,
            font      = dict(size=60, color='rgba(61,117,117,0.22)',
                             family='Arial Black, Arial, sans-serif'),
            xanchor='left', yanchor='bottom',
        )

    fig_anim.update_layout(annotations=[_yr_annotation(years[0])])
    for frame in fig_anim.frames:
        frame.layout = {'annotations': [_yr_annotation(frame.name)]}

    # ── Figure layout - maximised, top margin holds year bar + buttons ────────
    fig_anim.update_layout(
        margin             = {'r': 0, 't': 100, 'l': 0, 'b': 10},
        height             = 680,
        coloraxis_colorbar = dict(
            title     = {'text': meta['unit'], 'side': 'right'},
            thickness = 14,
            len       = 0.65,
            x         = 1.01,
            tickfont  = {'size': 11},
        ),
        geo                = geo_style,
    )

    # ── Year bar - top of figure, starts after the Play/Pause buttons ─────────
    if fig_anim.layout.sliders:
        fig_anim.layout.sliders[0].update(
            currentvalue = {
                'prefix'  : 'Year: ',
                'font'    : {'size': 17, 'color': '#3d7575'},
                'visible' : True,
                'xanchor' : 'left',
            },
            bgcolor       = '#f0f5f5',
            bordercolor   = '#3d7575',
            borderwidth   = 1,
            tickcolor     = '#3d7575',
            font          = {'size': 12, 'color': '#555'},
            x             = 0.28,    # offset right to clear the Play/Pause buttons
            len           = 0.72,
            y             = 1.18,
            pad           = {'t': 0, 'b': 0, 'l': 0, 'r': 0},
            transition    = {'duration': 200},
        )

    st.plotly_chart(fig_anim, use_container_width=True,
                    config={'displayModeBar': False})

    # ── Caption + KPI strip (below the map) ───────────────────────────────────
    _no_data_note = (
        f"Showing {_anim_first}–{_anim_last} (2018 excluded - no prior year for comparison)"
        if col_key == 'cawp_pct'
        else "Grey = no detectable irrigated blue water demand"
    )
    st.caption(
        f"**{meta['label']}** - {meta['description']} | Unit: **{meta['unit']}** | "
        f"{_anim_first}–{_anim_last} | "
        + _no_data_note
    )

    if _first is not None and _last is not None:
        k1, k2, k3, k4 = st.columns(4)
        k1.metric(f'Global median {_anim_first}',
                  f"{_first['median']:.3g} {meta['unit']}")
        k2.metric(f'Global median {_anim_last}',
                  f"{_last['median']:.3g} {meta['unit']}",
                  delta=f"{(_last['median']-_first['median'])/max(abs(_first['median']),1e-9)*100:+.1f}% vs {_anim_first}")
        k3.metric('Countries reporting', int(_last['count']))
        k4.metric('Years covered', f"{_anim_first} – {_anim_last}")

    # ── What to look for (policy interpretation guide) ────────────────────────
    with st.expander('What to look for - interpretation guide'):
        st.markdown(f"""
**{meta['label']}** captures how efficiently irrigated agriculture converts
blue water into economic output.

| Pattern | Policy signal |
|---------|--------------|
| Steadily rising Awp | Efficiency gains: technology adoption, crop switching, or irrigation modernisation |
| Sudden drop | Drought, market shock, or crop failure inflating water use relative to output |
| Consistently grey countries | Insufficient irrigated area detected, or humid climates where blue ET ≈ 0 |
| High Awp in arid regions | Intensive high-value horticulture compensating for scarce water resources |
| Low Awp despite large irrigation | Structural inefficiency or subsistence-dominated irrigated agriculture |

*Baseline year: {_anim_first}. All trend indicators (tAwp) are measured from {years[0]}.*
""")

    st.divider()

    # ── Global trend lines ────────────────────────────────────────────────────
    st.subheader(f'Global trend - {meta["label"]} ({_anim_first}–{_anim_last})')

    agg = (
        df_anim.dropna(subset=[col_key])
        .groupby('year')[col_key]
        .agg(['median', 'mean', 'count'])
        .reset_index()
        .rename(columns={'median': 'Median', 'mean': 'Mean', 'count': 'N countries'})
    )

    trend_tab_global, trend_tab_region = st.tabs(['Global', 'By region'])

    with trend_tab_global:
        fig_trend = px.line(
            agg.melt(id_vars='year', value_vars=['Median', 'Mean'],
                     var_name='Statistic', value_name=meta['unit']),
            x='year', y=meta['unit'], color='Statistic',
            markers=True,
            labels={'year': 'Year'},
            color_discrete_map={'Median': '#3d7575', 'Mean': '#F5A623'},
        )
        fig_trend.update_layout(
            height=300, margin={'t': 10, 'b': 10},
            hovermode='x unified',
            legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1),
        )
        fig_trend.update_traces(line_width=2.5, marker_size=8)
        st.plotly_chart(fig_trend, use_container_width=True,
                        config={'displayModeBar': False})
        _n_df = agg[agg['year'] == _anim_last]
        st.caption(
            f"N countries reporting in {_anim_last}: "
            f"{int(_n_df['N countries'].iloc[0]) if len(_n_df) else 'N/A'}"
        )

    with trend_tab_region:
        if 'wb_region' in df_anim.columns:
            reg_agg = (
                df_anim.dropna(subset=[col_key, 'wb_region'])
                .groupby(['year', 'wb_region'])[col_key]
                .median()
                .reset_index()
                .rename(columns={col_key: f'Median {meta["unit"]}'})
            )
            fig_reg = px.line(
                reg_agg,
                x='year', y=f'Median {meta["unit"]}', color='wb_region',
                markers=True,
                labels={'year': 'Year', 'wb_region': 'Region'},
                color_discrete_sequence=px.colors.qualitative.Safe,
            )
            fig_reg.update_layout(
                height=340, margin={'t': 10, 'b': 10},
                hovermode='x unified',
                legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1),
            )
            fig_reg.update_traces(line_width=2, marker_size=7)
            st.plotly_chart(fig_reg, use_container_width=True,
                            config={'displayModeBar': False})
        else:
            st.info('Regional breakdown not available - wb_region column missing.')

branding.footer()
