"""
streamlit_app.py - navigation router for the WaPOR4AWP Global Dashboard.

Usage:
    cd global-wapor-awp
    streamlit run dashboard/streamlit_app.py
"""

import sys
from pathlib import Path
import streamlit as st

sys.path.insert(0, str(Path(__file__).parent))
import branding

st.set_page_config(
    page_title            = 'WaPOR4Awp Monitor',
    page_icon             = branding.get_favicon(),
    layout                = 'wide',
    initial_sidebar_state = 'expanded',
)

# Sidebar logo sits above the nav links
with st.sidebar:
    branding.sidebar_logo()

pg = st.navigation([
    st.Page('pages/1_Global_Overview.py',          title='Global Overview'),
    st.Page('pages/2_Country_Explorer.py',          title='Country Explorer'),
    st.Page('pages/3_Rankings_and_Comparison.py',   title='Rankings & Comparison'),
    st.Page('pages/4_Methodology_and_Download.py',  title='Methodology & Download'),
    st.Page('pages/5_About.py',                     title='About'),
])
pg.run()
