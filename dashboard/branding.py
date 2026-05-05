"""
branding.py - IHE Delft / WaPOR4AWP brand helpers.

Call ``branding.apply(subtitle='...')`` right after st.set_page_config().
Call ``branding.footer()`` at the very end of each page.
"""

import base64
from pathlib import Path
import streamlit as st

_ASSETS = Path(__file__).parent.parent / 'assets'
_TEAL   = '#3d7575'
_AMBER  = '#F5A623'


# ── Internal helpers ──────────────────────────────────────────────────────────

def _b64(name: str) -> str:
    return base64.b64encode((_ASSETS / name).read_bytes()).decode()


def get_favicon():
    """Return a PIL Image for page_icon, or a fallback emoji."""
    try:
        from PIL import Image
        return Image.open(str(_ASSETS / 'favicon.png'))
    except Exception:
        return '💧'


# ── CSS injection ─────────────────────────────────────────────────────────────

def inject_css() -> None:
    """Inject brand CSS. Called once per page render."""
    extra_css = ''
    custom = _ASSETS / 'custom.css'
    if custom.exists():
        extra_css = custom.read_text(encoding='utf-8')

    st.markdown(f"""
<style>
{extra_css}

/* ── Sidebar ─────────────────────────────────────── */
[data-testid="stSidebar"] {{
    background-color: #f0f5f5;
    border-right: 3px solid {_TEAL};
}}
[data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3 {{
    color: {_TEAL};
}}

/* ── Metrics ─────────────────────────────────────── */
[data-testid="stMetricLabel"] {{
    color: {_TEAL};
    font-weight: 600;
}}

/* ── Active tab underline ────────────────────────── */
button[data-baseweb="tab"][aria-selected="true"] {{
    border-bottom: 3px solid {_TEAL} !important;
    color: {_TEAL} !important;
}}

/* ── Download button ─────────────────────────────── */
.stDownloadButton > button {{
    background-color: {_AMBER} !important;
    color: white !important;
    border: none !important;
    font-weight: 700 !important;
}}
.stDownloadButton > button:hover {{
    background-color: #d9861e !important;
    color: white !important;
}}

/* ── Header / footer bands ───────────────────────── */
.wapor-header {{
    background-color: {_TEAL};
    padding: 10px 24px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    border-radius: 6px;
    margin-bottom: 18px;
    box-shadow: 0 2px 6px rgba(0,0,0,0.18);
}}
.wapor-header-title {{
    color: white;
    font-size: 1.08rem;
    font-weight: 700;
    letter-spacing: 0.04em;
    margin: 0;
    line-height: 1.3;
}}
.wapor-header-sub {{
    color: rgba(255,255,255,0.82);
    font-size: 0.88rem;
    font-weight: 400;
}}
.wapor-footer {{
    background-color: {_AMBER};
    padding: 8px 24px;
    margin-top: 36px;
    border-radius: 6px;
    text-align: center;
    color: white;
    font-size: 0.82rem;
    font-weight: 600;
    letter-spacing: 0.03em;
}}
</style>
""", unsafe_allow_html=True)


# ── Branded header band ───────────────────────────────────────────────────────

def header(subtitle: str = '') -> None:
    """Render the teal header band with IHE Delft logo."""
    logo_b64 = _b64('logo.png')
    sub_html = (
        f'<br><span class="wapor-header-sub">{subtitle}</span>'
        if subtitle else ''
    )
    st.markdown(f"""
<div class="wapor-header">
  <span class="wapor-header-title">
    WaPOR4Awp Monitor: Global Agricultural Water Productivity{sub_html}
  </span>
  <div style="background:white; padding:5px 10px; border-radius:5px; flex-shrink:0; margin-left:16px;">
    <img src="data:image/png;base64,{logo_b64}"
         style="height:40px; display:block;"
         alt="IHE Delft - Institute for Water Education">
  </div>
</div>
""", unsafe_allow_html=True)


# ── Sidebar logo ──────────────────────────────────────────────────────────────

def sidebar_logo() -> None:
    """Show IHE Delft logo at the top of the sidebar."""
    logo_b64 = _b64('logo.png')
    st.sidebar.markdown(
        f'<div style="padding:8px 0 4px 0;">'
        f'<img src="data:image/png;base64,{logo_b64}" '
        f'style="width:100%;max-width:170px;" alt="IHE Delft"></div>'
        f'<hr style="border:none;border-top:2px solid {_TEAL};margin:6px 0 14px 0;">',
        unsafe_allow_html=True,
    )


# ── Footer band ───────────────────────────────────────────────────────────────

def footer() -> None:
    """Render the amber footer band."""
    st.markdown(
        '<div class="wapor-footer">'
        'WaPOR4Awp Monitor &nbsp;&bull;&nbsp; IHE Delft &nbsp;&bull;&nbsp; FAO'
        '</div>',
        unsafe_allow_html=True,
    )


# ── One-call convenience ──────────────────────────────────────────────────────

def apply(subtitle: str = '', show_logo: bool = True) -> None:
    """Inject CSS, render header band and (optionally) sidebar logo."""
    inject_css()
    header(subtitle)
    if show_logo:
        sidebar_logo()
