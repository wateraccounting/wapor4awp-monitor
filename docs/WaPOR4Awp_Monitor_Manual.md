# WaPOR4Awp Monitor - Technical Methodology and User Manual

**Global Agricultural Water Productivity Dashboard**
IHE Delft Institute for Water Education · Food and Agriculture Organization of the United Nations (FAO)

---

## 1. Introduction

### 1.1 Purpose

WaPOR4Awp Monitor is a global dashboard for tracking **Agricultural Water Productivity (Awp)** at the country level using satellite remote-sensing data and national economic statistics. It is designed to support evidence-based monitoring of **SDG indicator 6.4.1** (*Change in water-use efficiency over time*) and to help policy makers, water managers, and researchers understand where irrigated agriculture generates the most economic value per unit of consumed water.

### 1.2 Audience

- National water and agriculture ministries
- River-basin organisations
- Researchers in irrigation, water economics, and climate adaptation
- International partners working on SDG 6 monitoring
- Educators and students in water-resources programmes

### 1.3 Partners

The Awp methodology was developed by **IHE Delft Institute for Water Education** in collaboration with **FAO**. WaPOR satellite data is published by FAO; the dashboard, derivations, and documentation are produced at IHE Delft.

---

## 2. Concept - Agricultural Water Productivity

### 2.1 Definition

Agricultural Water Productivity (Awp) is the **economic value of irrigated crop production per unit of blue water consumed**:

```
Awp = (GVAa × (1 − Cr)) / VETb            [USD/m³]
```

| Term | Meaning |
|------|---------|
| **GVAa** | Agriculture, forestry & fishing value added (current USD) |
| **Cr**   | Crop ratio - non-irrigated fraction of GVAa |
| **VETb** | Annual blue ET volume over irrigated land (m³/year) |

### 2.2 Why blue water?

*Blue water* refers to water from rivers, lakes, and aquifers - the water that irrigation actually withdraws and consumes. *Green water* (rainfall stored in soil) is shared by rainfed and irrigated systems and is excluded from the productivity ratio so the indicator isolates the value generated specifically by irrigation.

### 2.3 SDG 6.4.1 alignment

SDG 6.4.1 measures water-use efficiency as USD value added per m³ of water withdrawn. WaPOR4Awp Monitor adapts this concept for the agricultural sector, using satellite-derived consumption (blue ET) instead of withdrawals - a more accurate indicator of net water use in regions where return flows are significant.

---

## 3. Methodology

### 3.1 Core formula

```
Awp = (GVAa × (1 − Cr)) / VETb
```

### 3.2 Component derivation

#### GVAa - Agricultural Value Added

Source: World Bank indicator `NV.AGR.TOTL.CD` (Agriculture, forestry and fishing value added, current US$). Annual, country-level. Note: this includes forestry and fishing alongside agriculture, which inflates Awp in countries with large forestry or fishing sectors. Such cases are flagged with `GVA_FORESTRY_FISHING`.

#### Cr - Crop ratio

Cr is the fraction of agricultural value added that comes from **non-irrigated** activities (rainfed crops, forestry, fishing, livestock). It is derived from area proxies and literature, with a fallback hierarchy:

1. **Country-year** value (preferred)
2. **Country fixed** value (most recent reliable estimate)
3. **Regional average** (when no country-level data exists)
4. **Global default** (last resort)

Each fallback is recorded in the `cr_source` column and reflected in a `CR_*` quality flag.

#### VETb - Blue ET volume

Computed in five steps from WaPOR v3 dekadal AETI and CHIRPS daily precipitation:

**Step 1 - Effective precipitation** (Brouwer & Heibloem 1986, per pixel per month):

| Monthly rainfall *P* (mm) | Effective precipitation *Pe* |
|---------------------------|------------------------------|
| *P* ≤ 16.67               | *Pe* = 0                     |
| 16.67 < *P* ≤ 75          | *Pe* = 0.6 × *P* − 10        |
| *P* > 75                  | *Pe* = 0.8 × *P* − 25        |

The two segments are continuous at *P* = 75 mm/month (*Pe* = 35 mm). The zero-threshold at *P* = 16.67 mm ensures *Pe* ≥ 0.

**Step 2 - Monthly blue ET** (per pixel):
```
ETb_month = max(AETI_month − Pe_month, 0)
```

**Step 3 - Annual sum** (per pixel):
```
ETb_annual = Σ ETb_month  (m = 1..12)        [mm/year]
```

**Step 4 - Irrigation-weighted volume** (per pixel):
```
VETb_pixel = (ETb_annual / 1000) × A_pixel × f_irr     [m³]
```
where *A_pixel* is the pixel area in m² and *f_irr* ∈ [0, 1] is the irrigation fraction from the GMIE-100 layer.

**Step 5 - Country total**:
```
VETb = Σ VETb_pixel   over all pixels in country       [m³/year]
```

### 3.3 Derived indicators

| Indicator | Formula | Unit |
|-----------|---------|------|
| **cAwp** - year-to-year change | (Awp_t − Awp_{t−1}) / Awp_{t−1} × 100 | % |
| **tAwp** - trend since 2018    | (Awp_t − Awp_2018) / Awp_2018 × 100 | % |

Baseline year: **2018** (first year of WaPOR v3 coverage).

---

## 4. Data Sources

| Dataset | Used for | Resolution | Period | GEE asset / Source |
|---------|----------|-----------|--------|---------------------|
| [WaPOR v3 L1-AETI-D](https://data.apps.fao.org/wapor) | Crop water consumption (AETI) | 300 m | 2018+ | `FAO/WAPOR/3/L1_AETI_D` |
| [CHIRPS Daily](https://www.chc.ucsb.edu/data/chirps) | Effective precipitation Pe | ~5 km (0.05°) | 2018+ | `UCSB-CHG/CHIRPS/DAILY` |
| [GMIE-100](https://essd.copernicus.org/articles/17/855/2025/) | Sub-pixel irrigation proportion (0-1) | ~100 m | 2010-2019 | `projects/wu-rsdata/assets/gmie` |
| [World Bank NV.AGR.TOTL.CD](https://data.worldbank.org/indicator/NV.AGR.TOTL.CD) | GVAa (agriculture, forestry & fishing value added, current US$) | country | annual | World Bank Open Data |
| [FAO AQUASTAT](https://www.fao.org/aquastat) | Crop ratio Cr (irrigated and cultivated area statistics) | country | annual + fallbacks | FAO AQUASTAT portal |
| [Brouwer & Heibloem 1986](https://www.fao.org/3/s2022e/s2022e00.htm) | Effective precipitation formula (Pe) | - | reference | FAO Training Manual no. 3 |
| [USDOS LSIB Simple 2017](https://developers.google.com/earth-engine/datasets/catalog/USDOS_LSIB_SIMPLE_2017) | Country reduction polygons | vector | static | `USDOS/LSIB_SIMPLE/2017` |

All raster computation runs on Google Earth Engine (`02_export_country_awp.js`). Country-level CSVs are produced by Python scripts (`02_*` through `06_validate_outputs.py`) and consumed by the Streamlit dashboard.

> **Note on the dashboard UI:** for clarity in the public interface, the dashboard pages refer to these inputs by generic terms (*"AETI", "daily precipitation", "irrigation-weighted area", "agricultural GVA"*) rather than by source name. The full attribution table above is the authoritative reference for citation, validation, and replication.

---

## 5. Quality Flags

Each row in the dataset carries a comma-separated `quality_flag` field. Multiple flags may apply to a single country-year.

| Flag | Meaning |
|------|---------|
| `OK` | All key inputs available; indicator calculated normally. |
| `MISSING_GVA` | GVA data missing - Awp not calculated. |
| `MISSING_CR` | Cr unavailable and no fallback applied - Awp not calculated. |
| `CR_COUNTRY_FIXED` | Country fixed Cr used (no annual value available). |
| `CR_REGIONAL_DEFAULT` | Regional average Cr used - moderate confidence. |
| `CR_GLOBAL_DEFAULT` | Global default Cr used - low confidence. |
| `ZERO_VETB` | VETb ≤ 0 - Awp not calculated (typical of humid countries with no blue-water demand). |
| `LOW_GMIE_AREA` | Irrigated area below minimum threshold. |
| `NO_GMIE_IRRIGATION` | No irrigated area detected in this country. |
| `GVA_FORESTRY_FISHING` | Country has a large forestry/fishing sector; GVA numerator likely overestimates irrigated agricultural value. |
| `BOUNDARY_MISMATCH` | Country boundary or ISO-3 code mismatch suspected. |
| `PARTIAL_YEAR` | WaPOR or PCP data incomplete for this year. |
| `OUTLIER_AWP` | Awp is unusually high or low - review recommended. |

### Recommended filters by use case

| Use case | Recommended filter |
|----------|---------------------|
| Peer-reviewed analysis | `OK` only |
| Country-level planning | `OK` + `CR_COUNTRY_FIXED` |
| Global overview map | `OK` + all `CR_*` flags |
| Exploratory / educational | No filter |

---

## 6. Dashboard - Page-by-Page Walkthrough

The dashboard has five pages, accessible from the sidebar.

### 6.1 Global Overview

**Purpose:** show how the selected indicator varies across countries in a given year.

**Controls:**
- *Indicator selector* (sidebar) - Awp, cAwp, tAwp, VETb, GVA, irrigated area, ETb depth, AETI depth.
- *Year slider* (sidebar) - single-year snapshot.
- *Animation* (button) - plays the choropleth across all years (cAwp animation starts at 2019; other indicators at 2018).
- *Click a country* - opens an inline pop-out showing that country's value, its rank (e.g. "#12 of 146"), and key components.

**Caveats:**
- For **cAwp**, 2018 shows a warning ("first year of WaPOR data - no prior year"). The last year (e.g. 2025) shows a warning if data is incomplete.
- Countries flagged `OUTLIER_AWP` are excluded from the "featured country" panel.

### 6.2 Country Explorer

**Purpose:** time-series view for one or more selected countries.

**Controls:**
- *Country multi-select* (sidebar) - pick one or many.
- *Indicator selector* - same options as Global Overview.
- *Time-series chart* - line chart by year, one line per country.
- *Year-to-year change panel* - shows cAwp and tAwp.

**Tip:** select 3–5 countries for a clean comparison; more than ~10 lines becomes hard to read.

### 6.3 Rankings & Comparison

**Purpose:** identify top and bottom performers and compare across regions / income groups.

**Controls:**
- *Year selector*.
- *Top-N rankings* - bar charts of highest- and lowest-ranked countries on the selected indicator.
- *Region / income filters* - restrict the ranking pool.
- *Box plots by region and income group* - distribution comparison.

**Metric "Countries ranked"** indicates how many countries had data for the selected indicator-year combination (this is the ranking pool, not a rank itself).

### 6.4 Methodology & Download

Four tabs:

- **About** - what the dashboard is and which pages do what.
- **Methodology** - full Awp derivation (formula, Pe table, step-by-step VETb).
- **Quality Flags** - flag-by-flag reference table and recommended filters.
- **Download** - filter by year and quality flag, then export the resulting subset as CSV.

### 6.5 About

Project background, partners, resource links (WaPOR portal, methodology DOI, this manual), citation, and contact email.

---

## 7. Recommended Use Cases

| Purpose | Suggested workflow |
|---------|---------------------|
| **Compare countries in a single year** | Global Overview → select indicator → set year → click countries to see ranks |
| **Track one country over time** | Country Explorer → select country → choose indicator → read trend |
| **Identify regional leaders** | Rankings & Comparison → set year → filter by region → review top-N |
| **Export data for analysis** | Methodology & Download → Download tab → filter quality flags → export CSV |
| **Cite in research** | Use citation in section 9 below; restrict to `OK` rows for peer-review |

---

## 8. Caveats and Limitations

1. **GVA includes forestry and fishing.** Countries with large forestry or fishing sectors will have Awp overestimated. Flagged `GVA_FORESTRY_FISHING`.

2. **Cr uncertainty (±15–25%).** The crop ratio is derived from area proxies and literature, not direct economic surveys.

3. **Static irrigation fraction (GMIE-100, ~100 m, observation period 2010–2019).** Recent irrigation expansion or abandonment is not captured.

4. **2018 baseline.** WaPOR v3 starts in 2018; tAwp = 0 for all countries in 2018 by definition.

5. **Humid-country Awp.** Where annual rainfall meets crop water demand, blue ET (VETb) is near zero and Awp is not computed (`ZERO_VETB`). This is a *correct* result, not a data error.

6. **Boundary geometry.** Country reductions use LSIB simplified boundaries. Disputed or recently changed borders may not match other authoritative sources exactly.

7. **Most recent year may be incomplete.** WaPOR data is published with a lag; the latest year often carries `PARTIAL_YEAR` until the full year is processed.

---

## 9. Citation

If you use data, results, or screenshots from WaPOR4Awp Monitor, please cite:

> Yalew, S. & Mul, M. (2026). *WaPOR4Awp Monitor: Annual Agricultural Water Productivity - Dashboard and Dataset.* IHE Delft / FAO.

## 10. Licence

The dataset and dashboard are produced by IHE Delft and FAO and provided under
[Creative Commons Attribution-NonCommercial-ShareAlike 3.0 IGO (CC BY-NC-SA 3.0 IGO)](https://creativecommons.org/licenses/by-nc-sa/3.0/igo/).

## 11. Contact

For questions about the dashboard, the underlying data, or collaboration opportunities, contact the WaPOR4Awp Monitor team at IHE Delft:

**Email:** WaterAccounting_Project@un-ihe.org

---

*Manual version: 1.0 - 2026-05-05*
