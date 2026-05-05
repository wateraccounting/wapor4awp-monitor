"""
5_About.py - project background, partners, and contact.
"""

import streamlit as st
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
import branding

branding.apply(subtitle='About', show_logo=False)

# ── Project identity ──────────────────────────────────────────────────────────
st.markdown("""
**WaPOR4Awp Monitor** is developed by **IHE Delft Institute for Water
Education** in collaboration with the **Food and Agriculture Organization
of the United Nations (FAO)**.

It presents country-level **Agricultural Water Productivity (Awp)** derived
from WaPOR satellite remote-sensing data, covering irrigated agriculture
globally for the period 2018–present.
""")

st.divider()

# ── Partner logos / cards ─────────────────────────────────────────────────────
col_ihe, col_fao = st.columns(2, gap='large')

with col_ihe:
    st.markdown("""
#### IHE Delft Institute for Water Education
IHE Delft is the largest international graduate water education institute in the
world, based in Delft, the Netherlands. The institute operates under the auspices
of UNESCO as a Category 2 institute and carries out research and capacity
development in water, environment, and related fields.

[un-ihe.org](https://www.un-ihe.org)
""")

with col_fao:
    st.markdown("""
#### Food and Agriculture Organization of the United Nations (FAO)
FAO is a specialised agency of the United Nations that leads international efforts
to defeat hunger and improve nutrition. WaPOR is FAO's open-access portal to
monitor water productivity in agriculture through remote sensing, supporting
evidence-based food and water policy.

[fao.org](https://www.fao.org)
""")

st.divider()

# ── Resources ─────────────────────────────────────────────────────────────────
st.subheader('Resources')

r1, r2, r3 = st.columns(3, gap='large')

with r1:
    st.markdown("""
**WaPOR Data Portal**

Access the full WaPOR remote-sensing dataset - evapotranspiration, land cover,
precipitation, and more - at continental and national scales.

[data.apps.fao.org/wapor](https://data.apps.fao.org/wapor)
""")

with r2:
    st.markdown("""
**Methodology Reference**

Full technical documentation of the WaPOR data products and the Awp derivation
methodology, published by FAO.

[FAO Open Knowledge Repository](https://openknowledge.fao.org/server/api/core/bitstreams/52282ed9-f901-49c0-b879-252fb58fd96c/content)
""")

with r3:
    st.markdown("""
**Dashboard Manual & Guidelines**

Step-by-step guidance for interpreting and using this dashboard, including
indicator definitions, data quality flags, and recommended use cases.
""")
    st.page_link('pages/4_Methodology_and_Download.py',
                 label='Open Manual (in Methodology & Download)', icon='📘')

st.divider()

# ── Citation ──────────────────────────────────────────────────────────────────
st.subheader('Citation')
st.markdown("""
If you use data or results from this dashboard, please cite:

> Yalew, S. & Mul, M. (2026). *WaPOR4AWP Global: Annual Agricultural Water
> Productivity - Dashboard and Dataset.*
> IHE Delft / FAO.
""")

st.divider()

# ── Contact ───────────────────────────────────────────────────────────────────
st.subheader('Contact')
st.markdown("""
For questions about this dashboard, the underlying data, or collaboration
opportunities, please reach out to the WaPOR4Awp Monitor team at IHE Delft:

**Email:** [WaterAccounting_Project@un-ihe.org](mailto:WaterAccounting_Project@un-ihe.org)
""")

branding.footer()
