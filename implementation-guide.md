# WaPOR4AWP Global — Implementation Guide

Goal: get GEE computation running within 1 hour so data processes overnight.
Everything that requires your attention is marked with ←

---

## Project structure

```
global-wapor-awp/
├── gee/
│   ├── 00_confirm_scale_factors.js     GEE: verify WaPOR v3 scale factors
│   ├── 01_prepare_gmie_asset.js        GEE: mosaic and export GMIE-100
│   └── 02_export_country_awp.js        GEE: compute ETb, reduce to countries, export CSV
├── scripts/
│   ├── 02_download_worldbank_gva.py    Python: download World Bank GVA via API
│   ├── 03_prepare_aquastat_cr.py       Python: build Cr lookup table
│   ├── 04_build_country_crosswalk.py   Python: align ISO-3 codes across datasets
│   ├── 05_compute_annual_awp.py        Python: merge all inputs, compute Awp
│   └── 06_validate_outputs.py          Python: automated QA report
├── dashboard/
│   ├── streamlit_app.py                Entry point
│   ├── utils.py                        Shared constants and helpers
│   └── pages/
│       ├── 1_Global_Overview.py
│       ├── 2_Country_Explorer.py
│       ├── 3_Rankings_and_Comparison.py
│       └── 4_Methodology_and_Download.py
├── data/
│   ├── raw/
│   │   ├── gmie/                       67 GMIE-100 GeoTIFF tiles (already downloaded)
│   │   ├── gee_exports/                GEE CSV outputs land here after download
│   │   ├── worldbank/                  Auto-created by script 02
│   │   └── aquastat/                   Place AQUASTAT CSVs here manually
│   ├── interim/
│   │   ├── crosswalks/                 Auto-created by script 04
│   │   └── aquastat_cr.csv             Auto-created by script 03
│   └── final/
│       └── global_awp_country_year.csv Final output
├── docs/
│   └── WaPOR4AWP_Global_Technical_Guide.docx
├── requirements.txt
└── implementation-guide.md            ← this file
```

---

## Prerequisites — check before starting (~5 min)

```
□  GEE account with access to projects/UNFAO/wapor/v3/ collections
   → test at code.earthengine.google.com — search the collection ID in the search bar

□  earthengine CLI installed and authenticated (for GMIE tile upload only)
   pip install earthengine-api
   earthengine authenticate

□  Python 3.10+ installed
   python --version

□  GMIE tiles present
   ls data/raw/gmie/*.tif   →  should list your tiles (65–67 is normal)

□  GEE cloud project ID known
   e.g.  ee-seleshi-wapor
   find it at console.cloud.google.com or code.earthengine.google.com top-left
```

---

## Python environment — do once

```bash
cd D:/WaPOR4AWP_global/global-wapor-awp

python -m venv .venv

.venv\Scripts\activate            # Windows
# source .venv/bin/activate       # Mac / Linux

pip install -r requirements.txt
```

Your prompt will show `(.venv)` when active.
Always activate the venv before running any Python script or the dashboard.

If using VS Code: Ctrl+Shift+P → Python: Select Interpreter → choose .venv

---

## TRACK A — GEE (sequential, do in order)

All GEE scripts run at code.earthengine.google.com — paste each script and click Run.

```
┌──────┬──────────────────────────────────────┬──────────┬────────────────────────────────────────┐
│ Step │ Action                               │ Runtime  │ What you do                            │
├──────┼──────────────────────────────────────┼──────────┼────────────────────────────────────────┤
│  A1  │ Verify WaPOR v3 scale factors        │ ~1 min   │ Paste gee/00_confirm_scale_factors.js  │
│      │                                      │          │ into GEE Code Editor → Run             │
│      │                                      │          │ Read Console → find scale factor for   │
│      │                                      │          │ L1-AETI-M and L1-PCP-M                 │
│      │                                      │          │ Expected: Jan AETI at Nile Delta       │
│      │                                      │          │ ≈ 60–100 mm/month after scaling        │
├──────┼──────────────────────────────────────┼──────────┼────────────────────────────────────────┤
│  A2  │ SKIP — tiles already in GEE          │  —       │ Tiles are at:                          │
│      │ (was: upload GMIE tiles)             │          │ projects/wu-rsdata/assets/gmie         │
│      │                                      │          │ No upload needed                       │
│      │                                      │          │ → Switch to Track B immediately        │
├──────┼──────────────────────────────────────┼──────────┼────────────────────────────────────────┤
│  A3  │ Inspect GMIE asset (sanity check)     │ ~1 min   │ Paste gee/01_prepare_gmie_asset.js     │
│      │                                      │          │ into GEE Code Editor → Run             │
│      │                                      │          │ Check Console: GMIE @ Nile Delta       │
│      │                                      │          │ should be 0.7–1.0                      │
│      │                                      │          │ Asset is already a single Image —      │
│      │                                      │          │ no mosaic step needed                  │
├──────┼──────────────────────────────────────┼──────────┼────────────────────────────────────────┤
│  A4  │ Submit annual country export tasks   │ ~3 min   │ Paste gee/02_export_country_awp.js     │
│      │                                      │          │ into GEE → verify SCALE_AETI/PCP       │
│      │                                      │          │ from step A1, then Run                 │
│      │                                      │          │ Tasks panel → click Run on all 6 tasks │
│      │                                      │          │ Verify all 6 show Running status       │
├──────┼──────────────────────────────────────┼──────────┼────────────────────────────────────────┤
│  A5  │ GEE computes overnight               │ 1–6 hrs  │ Nothing — leave it running             │
│      │                                      │          │ Check Tasks panel before sleeping      │
└──────┴──────────────────────────────────────┴──────────┴────────────────────────────────────────┘
```

### Step A4 — only values to verify in 02_export_country_awp.js

Project ID and asset paths are already set. The only values to update after step A1:

```javascript
var SCALE_AETI   = 0.1;   // ← confirm from step A1 Console output
var SCALE_PCP    = 0.1;   // ← confirm from step A1 Console output
```

Everything else is pre-configured:

```javascript
var PROJECT_ID    = 'wu-rsdata';
var YEAR_START    = 2018;
var YEAR_END      = 2025;
var LANDUSE_ASSET = 'projects/wu-rsdata/assets/gmie100_global';
var LANDUSE_TYPE  = 'fraction';
var LANDUSE_LABEL = 'GMIE-100';
```

---

## TRACK B — Python + AQUASTAT (run while waiting for GMIE upload in Track A)

Open a second terminal. Activate venv first.

```
┌──────┬──────────────────────────────────────┬──────────┬────────────────────────────────────────┐
│ Step │ Action                               │ Runtime  │ Command                                │
├──────┼──────────────────────────────────────┼──────────┼────────────────────────────────────────┤
│  B1  │ Download World Bank GVA              │ ~2 min   │ python scripts/                        │
│      │ (auto — just needs internet)         │          │ 02_download_worldbank_gva.py           │
│      │                                      │          │                                        │
│      │                                      │          │ Check: Ethiopia GVA series printed     │
│      │                                      │          │ Should show values in billions USD     │
├──────┼──────────────────────────────────────┼──────────┼────────────────────────────────────────┤
│  B2  │ Build country crosswalk              │ ~1 min   │ python scripts/                        │
│      │ (auto — just needs internet)         │          │ 04_build_country_crosswalk.py          │
│      │                                      │          │                                        │
│      │                                      │          │ Check: ~250 countries, 12 flagged      │
│      │                                      │          │ for review (Kosovo, Taiwan, etc.)      │
├──────┼──────────────────────────────────────┼──────────┼────────────────────────────────────────┤
│  B3  │ Download AQUASTAT data               │ ~20 min  │ Browser:                               │
│      │ (manual, optional but recommended)   │ manual   │ fao.org/aquastat/statistics/query      │
│      │                                      │          │ (details below)                        │
│      │                                      │          │                                        │
│      │                                      │          │ Skip if short on time — script uses    │
│      │                                      │          │ built-in country defaults as fallback  │
├──────┼──────────────────────────────────────┼──────────┼────────────────────────────────────────┤
│  B4  │ Prepare crop ratio (Cr) table        │ ~1 min   │ python scripts/                        │
│      │                                      │          │ 03_prepare_aquastat_cr.py              │
│      │                                      │          │                                        │
│      │                                      │          │ Check: source breakdown printed        │
│      │                                      │          │ Egypt Cr should be ~0.30              │
│      │                                      │          │ Ethiopia Cr should be ~0.88           │
└──────┴──────────────────────────────────────┴──────────┴────────────────────────────────────────┘
```

### Step B3 — AQUASTAT manual download

```
URL:       fao.org/aquastat/statistics/query

Select:
  Countries  → All countries
  Variables  → "Area equipped for irrigation: total"  (ha)
               "Cultivated area"                       (ha)
  Years      → 2010–2025
  Format     → CSV

Save as:
  data/raw/aquastat/aquastat_irrigated_area.csv
  data/raw/aquastat/aquastat_cultivated_area.csv

Required columns (rename if AQUASTAT uses different headers):
  iso3, year, irrigated_area_ha
  iso3, year, cultivated_area_ha
```

---

## Tonight — before you go to bed

Check the GEE Tasks panel. You should see 6 tasks running:

```
awp_gee_country_2018   ●  Running
awp_gee_country_2019   ●  Running
awp_gee_country_2020   ●  Running
awp_gee_country_2021   ●  Running
awp_gee_country_2022   ●  Running
awp_gee_country_2023   ●  Running
awp_gee_country_2024   ●  Running
awp_gee_country_2025   ●  Running
```

If any show FAILED:

```
"Computation timed out"        →  open 02_export_country_awp.js
"User memory limit exceeded"      set TILE_SCALE = 8, resubmit that year only

"Band pattern did not match"   →  LANDUSE_BAND wrong; set to 'b1' for wu-rsdata GMIE

"Asset not found" (GMIE)       →  LANDUSE_ASSET path wrong
                                  must be projects/wu-rsdata/assets/gmie

"ImageCollection not found"    →  WaPOR or CHIRPS collection ID wrong
                                  AETI: FAO/WAPOR/3/L1_AETI_D
                                  PCP:  UCSB-CHG/CHIRPS/DAILY
```

---

## Tomorrow morning — all 8 tasks show COMPLETED

```
┌──────┬──────────────────────────────────────┬──────────┬────────────────────────────────────────┐
│ Step │ Action                               │ Runtime  │ Command                                │
├──────┼──────────────────────────────────────┼──────────┼────────────────────────────────────────┤
│  C1  │ Download 8 CSVs from Google Drive    │ ~5 min   │ drive.google.com                       │
│      │                                      │ manual   │ → WaPOR4AWP_GEE_outputs/               │
│      │                                      │          │ Download all awp_gee_country_YYYY.csv  │
│      │                                      │          │ → save to data/raw/gee_exports/        │
├──────┼──────────────────────────────────────┼──────────┼────────────────────────────────────────┤
│  C2  │ Compute annual Awp                   │ ~1 min   │ python scripts/                        │
│      │                                      │          │ 05_compute_annual_awp.py               │
│      │                                      │          │                                        │
│      │                                      │          │ Check: Awp statistics table printed    │
│      │                                      │          │ Netherlands should rank high           │
│      │                                      │          │ Ethiopia should rank low               │
├──────┼──────────────────────────────────────┼──────────┼────────────────────────────────────────┤
│  C3  │ Validate outputs                     │ ~1 min   │ python scripts/                        │
│      │                                      │          │ 06_validate_outputs.py                 │
│      │                                      │          │                                        │
│      │                                      │          │ All checks should show PASS            │
│      │                                      │          │ Report: data/final/                    │
│      │                                      │          │ validation_report.txt                  │
├──────┼──────────────────────────────────────┼──────────┼────────────────────────────────────────┤
│  C4  │ Launch dashboard                     │ instant  │ streamlit run dashboard/               │
│      │                                      │          │ streamlit_app.py                       │
│      │                                      │          │                                        │
│      │                                      │          │ Opens at http://localhost:8501         │
└──────┴──────────────────────────────────────┴──────────┴────────────────────────────────────────┘
```

---

## Full timeline

```
0:00  A1  Scale factor check (GEE, 1 min)
0:02  A2  SKIP — tiles already at projects/wu-rsdata/assets/gmie
0:02  B1  World Bank GVA download (Python, 2 min)
0:04  B2  Country crosswalk (Python, 1 min)
0:05  B3  AQUASTAT download (browser, 20 min — skip if short on time)
0:05  A3  Inspect GMIE asset sanity check (GEE, 1 min)
0:06  B4  Prepare Cr table (Python, 1 min)
0:20  A4  Submit 8 year tasks (GEE, 3 min)
0:23  ✓   All 8 GEE tasks running overnight

      [GEE runs 1–6 hours on Google's servers — you do nothing]

next  C1  Download CSVs from Drive (5 min)
day   C2  Compute Awp (1 min)
      C3  Validate (1 min)
      C4  Launch dashboard (instant)
```

---

## Quick reference — key paths

```
GEE scripts      gee/
Python scripts   scripts/
Dashboard        dashboard/streamlit_app.py
GMIE tiles       data/raw/gmie/                     (input)
GEE exports      data/raw/gee_exports/              (download here from Drive)
AQUASTAT         data/raw/aquastat/                 (place CSVs here manually)
Final output     data/final/global_awp_country_year.csv
Technical guide  docs/WaPOR4AWP_Global_Technical_Guide.docx
Validation log   data/final/validation_report.txt
```

## Quick reference — quality flags

```
OK                   All inputs present, Awp computed normally
MISSING_GVA          World Bank GVA not available for this country-year
ZERO_VETB            No computable blue ET — Awp not calculated
NO_GMIE_IRRIGATION   No irrigation detected in this country
LOW_GMIE_AREA        Irrigated area below 1,000 ha threshold
CR_COUNTRY_FIXED     Country fixed Cr used (no AQUASTAT data)
CR_REGIONAL_DEFAULT  Regional average Cr used
CR_GLOBAL_DEFAULT    Global default Cr = 0.80 used
GVA_FORESTRY_FISHING Large forestry/fishing sector — GVA likely overestimated
PARTIAL_YEAR         Fewer than 12 months of WaPOR data — ETb underestimated
OUTLIER_AWP          Awp outside plausible range — review recommended
```
