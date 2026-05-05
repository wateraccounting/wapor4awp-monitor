import json
from pathlib import Path

nb_path = Path(r"D:\WaPOR4AWP_global\global-wapor-awp\MOOC\MOOC_WaPOR_for_Global_Challenges_Data_access_python_with_GEE_Notebook2 (1).ipynb")

with nb_path.open("r", encoding="utf-8") as f:
    nb = json.load(f)

cell_a_src = """# === Extract LC=40 (irrigated/cropland) area within Erbil AOI ===
# Uses ESA WorldCover v200 (2021), the same dataset as ESA_LC_2021_Erbil.tif,
# clipped to the Erbil shapefile loaded earlier as `area_of_interest`.

esa_lc = ee.ImageCollection("ESA/WorldCover/v200").first().clip(area_of_interest)
cropland_mask = esa_lc.eq(40).selfMask()  # 1 where LC=40, masked elsewhere

# Total irrigated (cropland) area in hectares
irrigated_area_ha = (
    ee.Image.pixelArea().divide(1e4)            # m2 -> ha
    .updateMask(cropland_mask)
    .reduceRegion(
        reducer=ee.Reducer.sum(),
        geometry=area_of_interest.geometry(),
        scale=10,
        maxPixels=1e13,
    )
    .get('area').getInfo()
)
print(f"Irrigated (LC=40) area in Erbil: {irrigated_area_ha:,.1f} ha")

# Quick visual check
Map_lc = geemap.Map(height="500px", width="800px")
Map_lc.centerObject(area_of_interest, 8)
Map_lc.addLayer(cropland_mask, {"palette": ["#1a9641"]}, "Cropland (LC=40)")
Map_lc.addLayerControl()
Map_lc"""

cell_b_src = """# === Seasonal & annual AETI per year over the irrigated (LC=40) area ===
season_periods = {
    'season2018': {'SOS': '2018-06-01', 'EOS': '2018-10-31'},
    'season2019': {'SOS': '2019-06-01', 'EOS': '2019-10-31'},
    'season2020': {'SOS': '2020-06-01', 'EOS': '2020-10-31'},
    'season2021': {'SOS': '2021-06-01', 'EOS': '2021-10-31'},
    'season2022': {'SOS': '2022-06-01', 'EOS': '2022-10-31'},
    'season2023': {'SOS': '2023-06-01', 'EOS': '2023-10-31'},
    'season2024': {'SOS': '2024-06-01', 'EOS': '2024-10-31'},
    'season2025': {'SOS': '2025-06-01', 'EOS': '2025-10-31'},
}

aeti_full = ee.ImageCollection("projects/UNFAO/wapor/v3/L2-AETI-D")

def aeti_mean_mm(start, end):
    \"\"\"Mean of summed AETI (mm over the period) across cropland pixels in the AOI.\"\"\"
    period_sum = (
        aeti_full
        .filterDate(start, end)
        .filterBounds(area_of_interest)
        .map(lambda im: im.clip(area_of_interest))
        .sum()
        .updateMask(cropland_mask)
    )
    stats = period_sum.reduceRegion(
        reducer=ee.Reducer.mean(),
        geometry=area_of_interest.geometry(),
        scale=100,
        maxPixels=1e13,
    ).getInfo()
    return stats.get('L2-AETI-D')  # None if the period has no images

records = []
for season, dates in season_periods.items():
    year = season.replace('season', '')
    sos, eos = dates['SOS'], dates['EOS']

    seasonal_aeti = aeti_mean_mm(sos, eos)
    annual_aeti   = aeti_mean_mm(f"{year}-01-01", f"{year}-12-31")

    records.append({
        'year': int(year),
        'season': f"{sos} - {eos}",
        'seasonal_AETI_mean_mm': seasonal_aeti,
        'annual_AETI_mean_mm':   annual_aeti,
        'irrigated_area_ha':     irrigated_area_ha,
    })

summary_df = pd.DataFrame(records)

# Volume = mean depth (mm) x irrigated area; convert to Mm3
# (mm/1000 -> m) * (ha*1e4 -> m2) / 1e6 -> Mm3
summary_df['seasonal_AETI_volume_Mm3'] = (
    summary_df['seasonal_AETI_mean_mm'] / 1000
    * summary_df['irrigated_area_ha'] * 1e4
    / 1e6
)
summary_df['annual_AETI_volume_Mm3'] = (
    summary_df['annual_AETI_mean_mm'] / 1000
    * summary_df['irrigated_area_ha'] * 1e4
    / 1e6
)

print(summary_df.to_string(index=False))
summary_df"""


def to_lines(src: str):
    lines = src.split("\n")
    return [ln + ("\n" if i < len(lines) - 1 else "") for i, ln in enumerate(lines)]


def make_code_cell(src: str, cell_id: str):
    return {
        "cell_type": "code",
        "source": to_lines(src),
        "metadata": {"id": cell_id},
        "execution_count": None,
        "outputs": [],
    }


cells = nb["cells"]

# Find the trailing empty code cell (id sIu5-I22aK7i) and insert before it.
insert_at = len(cells)
for i in range(len(cells) - 1, -1, -1):
    md_id = cells[i].get("metadata", {}).get("id")
    if md_id == "sIu5-I22aK7i":
        insert_at = i
        break

new_cells = [
    make_code_cell(cell_a_src, "ErbilCroplandMask01"),
    make_code_cell(cell_b_src, "ErbilSeasonalAETI02"),
]

cells[insert_at:insert_at] = new_cells

with nb_path.open("w", encoding="utf-8") as f:
    json.dump(nb, f, indent=2, ensure_ascii=False)

print(f"Inserted {len(new_cells)} cells before index {insert_at}.")
print(f"Total cells now: {len(cells)}")
