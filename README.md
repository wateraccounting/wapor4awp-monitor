# WaPOR4Awp Monitor

**Global Agricultural Water Productivity Dashboard**
IHE Delft Institute for Water Education · Food and Agriculture Organization of the United Nations (FAO)

A country-level monitoring tool for **Agricultural Water Productivity (Awp)** — the economic value of irrigated crop production per unit of blue water consumed. Designed to support evidence-based monitoring of **SDG indicator 6.4.1** and to help policy makers, water managers, and researchers identify where irrigated agriculture generates the most value per unit of consumed water.

## Live dashboard

> Streamlit Cloud URL — to be added

## What it does

- Computes annual Awp (USD/m³) at country level for 2018-present
- Combines satellite-derived blue ET (from WaPOR v3 + CHIRPS) with World Bank value-added statistics and an irrigation-extent layer (GMIE-100)
- Provides global maps, country time series, regional rankings, and a filterable CSV download
- Includes a built-in technical methodology and user manual

## Core formula

```
Awp = (GVAa × (1 - Cr)) / VETb            [USD/m³]
```

| Term | Meaning |
|------|---------|
| GVAa | Agriculture, forestry & fishing value added (current USD) |
| Cr   | Crop ratio: non-irrigated fraction of GVAa |
| VETb | Annual blue ET volume over irrigated land (m³/year) |

See the **Methodology & Download → Methodology** tab in the dashboard, or `docs/WaPOR4Awp_Monitor_Manual.md`, for full derivation.

## Repository structure

```
global-wapor-awp/
├── gee/                      Google Earth Engine scripts (raster processing)
├── scripts/                  Python aggregation pipeline (CSV-level)
├── dashboard/                Streamlit application
│   ├── streamlit_app.py      Entry point (run this)
│   ├── branding.py           Theming and brand helpers
│   ├── utils.py              Shared constants and data loader
│   └── pages/                Five dashboard pages
├── data/
│   ├── final/                Country-year CSV consumed by dashboard
│   ├── interim/              Crosswalks and intermediate products
│   └── raw/                  Source inputs (GMIE rasters excluded - regenerable)
├── docs/                     Technical methodology and user manual
├── assets/                   Logo, favicon, custom CSS
├── MOOC/                     Educational notebook (WaPOR access via GEE)
└── requirements.txt          Python dependencies
```

## Quickstart

```bash
# 1. Clone
git clone https://github.com/<owner>/wapor4awp-monitor.git
cd wapor4awp-monitor

# 2. Set up environment
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # macOS / Linux
pip install -r requirements.txt

# 3. Run the dashboard
streamlit run dashboard/streamlit_app.py
```

The dashboard opens at `http://localhost:8501`.

## Data sources

| Dataset | Used for | Source |
|---------|----------|--------|
| [WaPOR v3 L1-AETI-D](https://data.apps.fao.org/wapor) | Crop water consumption (AETI) | FAO |
| [CHIRPS Daily](https://www.chc.ucsb.edu/data/chirps) | Effective precipitation | UCSB / Climate Hazards Center |
| [GMIE-100](https://essd.copernicus.org/articles/17/855/2025/) | Irrigation proportion (0-1) | ESSD 17:855 (2025) |
| [World Bank NV.AGR.TOTL.CD](https://data.worldbank.org/indicator/NV.AGR.TOTL.CD) | Agricultural value added | World Bank Open Data |
| [FAO AQUASTAT](https://www.fao.org/aquastat) | Crop ratio Cr inputs | FAO |
| [Brouwer & Heibloem 1986](https://www.fao.org/3/s2022e/s2022e00.htm) | Effective precipitation formula | FAO Training Manual no. 3 |
| [USDOS LSIB Simple 2017](https://developers.google.com/earth-engine/datasets/catalog/USDOS_LSIB_SIMPLE_2017) | Country boundaries | US Department of State |

## Citation

If you use data, results, or screenshots from WaPOR4Awp Monitor, please cite:

> Yalew, S. & Mul, M. (2026). *WaPOR4Awp Monitor: Annual Agricultural Water Productivity - Dashboard and Dataset.* IHE Delft / FAO.

## Licence

The dataset and dashboard are produced by IHE Delft and FAO and provided under
[CC BY-NC-SA 3.0 IGO](https://creativecommons.org/licenses/by-nc-sa/3.0/igo/).

## Contact

For questions about the dashboard, the underlying data, or collaboration opportunities, contact the WaPOR4Awp Monitor team at IHE Delft:

**Email:** WaterAccounting_Project@un-ihe.org
