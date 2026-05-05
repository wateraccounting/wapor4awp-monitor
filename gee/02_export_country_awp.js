/**
 * 02_export_country_awp.js
 *
 * Single-file GEE pipeline for global Agricultural Water Productivity:
 *
 *   WaPOR v3 L1-AETI-M  ──┐
 *   WaPOR v3 L1-PCP-M   ──┼──► monthly ETb per pixel (inline, no intermediate asset)
 *   Land use weight      ──┘
 *       │
 *       ▼
 *   Annual country-level sums (reduceRegions)
 *       │
 *       ▼
 *   CSV → Google Drive  (one export task per year, runs in parallel)
 *
 * ── Land use layer is fully swappable ───────────────────────────────────────
 *   Two modes, configured in the LAND USE block below:
 *
 *   'fraction'  Pixel values are 0–1 (e.g. GMIE-100).
 *               Weight = pixel value. Bilinear resampling to WaPOR 300m.
 *
 *   'binary'    Pixel values are integer land use codes (e.g. ESA CCI, FAO GAEZ).
 *               Specify which code(s) = irrigated cropland.
 *               Weight = 1 for those pixels, 0 elsewhere.
 *               Nearest-neighbour resampling preserves hard 0/1 edges.
 *
 *   All downstream computation (VETb, area, depth means) uses the same
 *   `weight` image regardless of which mode is chosen.
 *
 * ── Scalability design ──────────────────────────────────────────────────────
 *   • Land use resampled to WaPOR 300m CRS before any computation
 *   • Non-irrigated pixels masked before reduceRegions — cuts global pixel
 *     count by ~70–80%, the biggest single performance gain
 *   • tileScale = TILE_SCALE: splits GEE memory tiles; raise to 8 or 16
 *     if "Computation timed out" or OOM errors occur
 *   • One export task per year — GEE runs them in parallel within quota
 *   • Raw sums exported (not ratios) — Python computes area-weighted means
 *     and aggregates multi-polygon countries
 *
 * ── Prerequisites ────────────────────────────────────────────────────────────
 *   1. Run 00_confirm_scale_factors.js → record SCALE_AETI and SCALE_PCP
 *   2. Prepare land use asset (run 01_prepare_gmie_asset.js for GMIE-100,
 *      or upload your own single-band GEE asset)
 *   3. Update the configuration blocks below
 *
 * ── Output columns ───────────────────────────────────────────────────────────
 *   iso3, country_name, year, n_months_aeti, n_months_pcp,
 *   VETb_m3, irr_area_m2, AETI_wsum, ETb_wsum, landuse_source
 *
 *   → Download CSVs from Google Drive: WaPOR4AWP_GEE_outputs/
 *   → Place in data/raw/gee_exports/ then run scripts/05_compute_annual_awp.py
 */


// ═══════════════════════════════════════════════════════════════════════════
// WAPOR CONFIGURATION
// ═══════════════════════════════════════════════════════════════════════════

var PROJECT_ID = 'wu-rsdata';

// AETI: WaPOR v3 dekadal (L1-AETI-D). Scale factor 0.1 → mm/dekad.
// 3 dekadal images per month are summed to get monthly AETI.
// PCP: CHIRPS daily. Values in mm/day; sum of daily = monthly total. No scale needed.
var SCALE_AETI = 0.1;
var SCALE_PCP  = 1.0;

var YEAR_START = 2018;   // WaPOR v3 baseline year
var YEAR_END   = 2025;

var AETI_COL_ID = 'FAO/WAPOR/3/L1_AETI_D';    // dekadal AETI
var PCP_COL_ID  = 'UCSB-CHG/CHIRPS/DAILY';     // daily precipitation

// tileScale for reduceRegions (1–16).
// 4 works for most global runs at 300m. Increase to 8 or 16 if tasks fail.
var TILE_SCALE = 4;


// ═══════════════════════════════════════════════════════════════════════════
// LAND USE CONFIGURATION  ←  swap your layer here
// ═══════════════════════════════════════════════════════════════════════════
//
// To replace the land use layer, change the five parameters below.
// Nothing else in the script needs to change.
//
// ── Mode: 'fraction' ────────────────────────────────────────────────────
//   Pixel values are a continuous proportion of irrigated area, 0–1.
//   Weight = pixel value (partially irrigated pixels contribute proportionally).
//   Background/nodata replaced with 0.
//   Resampled bilinearly to WaPOR 300m (smooth gradients).
//
//   Example — GMIE-100 (current default):
//     LANDUSE_ASSET   = 'projects/YOUR_PROJECT/assets/gmie100_global'
//     LANDUSE_TYPE    = 'fraction'
//     IRRIGATED_CODES = []          (not used)
//     LANDUSE_BAND    = 'GMIE'
//     LANDUSE_NODATA  = -99
//     WEIGHT_THRESHOLD = 0.01
//
// ── Mode: 'binary' ──────────────────────────────────────────────────────
//   Pixel values are integer land use class codes.
//   Weight = 1 for pixels whose code is in IRRIGATED_CODES, 0 elsewhere.
//   Resampled with nearest-neighbour (default for reproject) — preserves 0/1.
//   WEIGHT_THRESHOLD should be 0.5 (any non-zero weight = irrigated).
//
//   Example — FAO GAEZ irrigated cropland (code 40):
//     LANDUSE_ASSET   = 'projects/YOUR_PROJECT/assets/gaez_landuse'
//     LANDUSE_TYPE    = 'binary'
//     IRRIGATED_CODES = [40]
//     LANDUSE_BAND    = 0            (first band)
//     LANDUSE_NODATA  = 0            (or -9999 — check your asset)
//     WEIGHT_THRESHOLD = 0.5
//
//   Example — ESA CCI Land Cover (irrigated cropland = class 20):
//     LANDUSE_ASSET   = 'ESA/CCI/LC/v207'   (or your uploaded asset)
//     LANDUSE_TYPE    = 'binary'
//     IRRIGATED_CODES = [20]
//     LANDUSE_BAND    = 'lccs_class'
//     LANDUSE_NODATA  = 0
//     WEIGHT_THRESHOLD = 0.5
//
//   Example — custom binary irrigated mask (1 = irrigated):
//     LANDUSE_ASSET   = 'projects/YOUR_PROJECT/assets/irrigated_mask_2020'
//     LANDUSE_TYPE    = 'binary'
//     IRRIGATED_CODES = [1]
//     LANDUSE_BAND    = 0
//     LANDUSE_NODATA  = -9999
//     WEIGHT_THRESHOLD = 0.5

var LANDUSE_ASSET    = 'projects/wu-rsdata/assets/gmie';   // single Image, already mosaicked
var LANDUSE_TYPE     = 'fraction';   // 'fraction' or 'binary'
var IRRIGATED_CODES  = [];           // [40] for GAEZ, [20] for ESA CCI, [1] for binary mask
var LANDUSE_BAND     = 'b1';         // actual band name in projects/wu-rsdata/assets/gmie
var LANDUSE_NODATA   = -99;          // background/nodata value → set to 0
var WEIGHT_THRESHOLD = 0.01;         // exclude pixels below this weight
                                     // use 0.01 for 'fraction', 0.5 for 'binary'

// Label written to the 'landuse_source' column in the export CSV.
// Update this when you swap datasets — helps track which layer produced each export.
var LANDUSE_LABEL = 'GMIE-100';      // e.g. 'FAO-GAEZ-v4', 'ESA-CCI-v207', 'custom-2020'


// ═══════════════════════════════════════════════════════════════════════════
// COUNTRY BOUNDARIES
// ═══════════════════════════════════════════════════════════════════════════
// LSIB_SIMPLE provides iso_alpha3. Multi-polygon countries produce multiple
// rows in the export CSV — Python aggregates by iso3 before computing Awp.

// LSIB_SIMPLE properties: country_co (ISO-2), country_na (name).
// There is no iso_alpha3 property — Python derives iso3 from country_name
// using scripts/05_compute_annual_awp.py (_LSIB_NAME_TO_ISO3 mapping).
var countries = ee.FeatureCollection('USDOS/LSIB_SIMPLE/2017')
  .map(function(f) {
    return f.set({
      'iso3':         null,           // derived in Python from country_name
      'country_name': f.get('country_na'),
    });
  });


// ═══════════════════════════════════════════════════════════════════════════
// SETUP — runs once, shared across all years
// ═══════════════════════════════════════════════════════════════════════════

// WaPOR native projection — used to align the land use layer
var wapor_proj = ee.ImageCollection(AETI_COL_ID)
  .sort('system:time_start')
  .first()
  .projection();

print('WaPOR L1 projection:', wapor_proj);
print('WaPOR L1 nominal scale (m):', wapor_proj.nominalScale());


// ─────────────────────────────────────────────────────────────────────────
// prepareLanduseWeight()
//
// Loads any land use asset and returns a single-band weight image aligned
// to the WaPOR 300m grid. Downstream code uses `weight` regardless of
// which mode was chosen.
//
// Returns: ee.Image with band 'weight', values in [0, 1], reprojected to
//          wapor_proj at 300m. Nodata pixels have weight = 0.
// ─────────────────────────────────────────────────────────────────────────
function prepareLanduseWeight(assetPath, type, codes, band, nodata) {

  // Load the asset and select the target band
  var raw = ee.Image(assetPath).select([band]);

  // Replace nodata with 0 so background pixels contribute weight = 0
  // (not masked, so weighted sums over country boundaries stay stable)
  raw = raw.where(raw.eq(nodata), 0);

  var weight;

  if (type === 'fraction') {
    // ── Continuous fraction mode ─────────────────────────────────────────
    // Values are already 0–1. Clamp for safety, then bilinearly resample
    // to WaPOR 300m. Bilinear is correct for smooth continuous fractions.
    weight = raw
      .clamp(0, 1)
      .resample('bilinear')
      .reproject({ crs: wapor_proj, scale: 300 })
      .rename('weight');

  } else {
    // ── Binary classification mode ───────────────────────────────────────
    // Build a 0/1 mask: 1 for any pixel whose code is in IRRIGATED_CODES.
    // OR-combine so multiple codes (e.g. irrigated annual + irrigated perennial)
    // are all captured in one pass.
    var irr_mask = ee.Image(0).byte();
    for (var i = 0; i < codes.length; i++) {
      irr_mask = irr_mask.or(raw.eq(ee.Number(codes[i])));
    }
    // Nearest-neighbour resampling (GEE default for reproject) preserves
    // hard 0/1 boundaries. Do not use bilinear here — it would create
    // fractional edge pixels at class boundaries, which is not meaningful
    // for a discrete classification.
    weight = irr_mask
      .reproject({ crs: wapor_proj, scale: 300 })
      .rename('weight');
  }

  return weight;
}

// Build the weight image using the configuration above
var luw = prepareLanduseWeight(
  LANDUSE_ASSET, LANDUSE_TYPE, IRRIGATED_CODES, LANDUSE_BAND, LANDUSE_NODATA
);

// Mask: pixels below threshold excluded from computation.
// This is the primary scalability optimisation — skips non-irrigated pixels.
var luw_mask   = luw.gte(WEIGHT_THRESHOLD);
var luw_masked = luw.updateMask(luw_mask);

// Pixel area in m² — accounts for latitude-dependent pixel size in geographic CRS
var pixel_area_m2 = ee.Image.pixelArea();

// Land-use-weighted pixel area image (m²) — used for VETb volume and depth means
var irr_area_m2_img = pixel_area_m2.multiply(luw_masked).rename('irr_area_m2');


// ═══════════════════════════════════════════════════════════════════════════
// EFFECTIVE PRECIPITATION (Brouwer & Heibloem 1986)
// ═══════════════════════════════════════════════════════════════════════════
// Piecewise linear formula; continuous at both breakpoints:
//   P = 16.67 mm → Pe = 0 from both segments
//   P = 75    mm → Pe = 35 mm from both segments
//
// @param {ee.Image} pcp_mm  Monthly PCP in mm/month (after scale factor applied)
// @returns {ee.Image}        Pe in mm/month, ≥ 0
function computePe(pcp_mm) {
  var pe_mid  = pcp_mm.multiply(0.6).subtract(10);  // 16.67 < P ≤ 75
  var pe_high = pcp_mm.multiply(0.8).subtract(25);  // P > 75

  return ee.Image(0)
    .where(pcp_mm.gt(16.67), pe_mid)
    .where(pcp_mm.gt(75),    pe_high)
    .max(0)
    .rename('PE');
}


// ═══════════════════════════════════════════════════════════════════════════
// PER-YEAR PROCESSING
// ═══════════════════════════════════════════════════════════════════════════
// Computes annual country-level sums for one calendar year.
// ETb is computed inline per month — no intermediate asset storage.
//
// @param  {number} year  Calendar year (e.g. 2020)
// @returns {ee.FeatureCollection}  One row per country polygon
function processYear(year) {

  // Iterate over calendar months explicitly.
  // AETI: sum all dekadal images within the month (typically 3) → monthly mm.
  // PCP:  sum all daily CHIRPS images within the month → monthly mm.
  var monthly = ee.ImageCollection(
    ee.List.sequence(1, 12).map(function(m) {
      var t0 = ee.Date.fromYMD(year, m, 1);
      var t1 = t0.advance(1, 'month');

      var aeti_mm = ee.ImageCollection(AETI_COL_ID)
        .filterDate(t0, t1)
        .sum()
        .multiply(SCALE_AETI)
        .max(0)
        .rename('AETI');

      var pcp_mm = ee.ImageCollection(PCP_COL_ID)
        .select('precipitation')
        .filterDate(t0, t1)
        .sum()
        .multiply(SCALE_PCP)
        .max(0);

      var etb_mm = aeti_mm.subtract(computePe(pcp_mm)).max(0).rename('ETb');

      return etb_mm.addBands(aeti_mm).set('system:time_start', t0.millis());
    })
  );

  var n_months_aeti = ee.Number(12);
  var n_months_pcp  = ee.Number(12);

  // ── Annual sums (mm/year) — only over land-use-weighted pixels ───────────
  var etb_annual  = monthly.select('ETb').sum().rename('ETb_annual_mm').updateMask(luw_mask);
  var aeti_annual = monthly.select('AETI').sum().rename('AETI_annual_mm').updateMask(luw_mask);

  // ── Per-pixel VETb (m³) ───────────────────────────────────────────────────
  //   ETb_mm / 1000  → depth in m
  //   × pixel_area_m²  → volume in m³
  //   × weight         → fraction that is actually irrigated
  var vetb_px = etb_annual
    .divide(1000)
    .multiply(pixel_area_m2)
    .multiply(luw_masked)
    .rename('VETb_m3');

  // ── Weighted numerators for area-weighted mean depths (ratio in Python) ───
  var aeti_wsum = aeti_annual.multiply(pixel_area_m2).multiply(luw_masked).rename('AETI_wsum');
  var etb_wsum  = etb_annual.multiply(pixel_area_m2).multiply(luw_masked).rename('ETb_wsum');

  // ── Single-pass country reduction ─────────────────────────────────────────
  var stack = ee.Image([
    vetb_px,         // sum → VETb_m3 per country
    irr_area_m2_img, // sum → irr_area_m2 per country (÷ 10000 = ha in Python)
    aeti_wsum,       // sum → numerator for area-weighted AETI depth
    etb_wsum,        // sum → numerator for area-weighted ETb depth
  ]);

  var stats = stack.reduceRegions({
    collection: countries,
    reducer:    ee.Reducer.sum(),
    scale:      300,
    crs:        wapor_proj,
    tileScale:  TILE_SCALE,
  });

  // Attach metadata fields used downstream
  stats = stats.map(function(feat) {
    return feat.set({
      'year':           year,
      'n_months_aeti':  n_months_aeti,
      'n_months_pcp':   n_months_pcp,
      'landuse_source': LANDUSE_LABEL,
    });
  });

  return stats;
}


// ═══════════════════════════════════════════════════════════════════════════
// SANITY CHECKS — run before submitting full batch
// ═══════════════════════════════════════════════════════════════════════════

var NILE_DELTA  = ee.Geometry.Point([31.2, 30.5]);
var INDUS_PLAIN = ee.Geometry.Point([72.8, 26.9]);
var SAHARA      = ee.Geometry.Point([20.0, 22.0]);

print('─── Land use weight sanity checks ──────────────────────────────');
print('Weight @ Nile Delta  (irrigated — expect > ' + WEIGHT_THRESHOLD + '):',
  luw.reduceRegion({ reducer: ee.Reducer.mean(), geometry: NILE_DELTA.buffer(20000),
    scale: 300, maxPixels: 1e6 }));
print('Weight @ Indus Plain (irrigated — expect > ' + WEIGHT_THRESHOLD + '):',
  luw.reduceRegion({ reducer: ee.Reducer.mean(), geometry: INDUS_PLAIN.buffer(20000),
    scale: 300, maxPixels: 1e6 }));
print('Weight @ Sahara      (not irrigated — expect ~0):',
  luw.reduceRegion({ reducer: ee.Reducer.mean(), geometry: SAHARA.buffer(20000),
    scale: 300, maxPixels: 1e6 }));

print('─── ETb sanity check (July 2020, Nile Delta) ────────────────────');
var aeti_mm_chk = ee.ImageCollection(AETI_COL_ID)
  .filterDate('2020-07-01', '2020-08-01').sum().multiply(SCALE_AETI).max(0);
var pcp_mm_chk = ee.ImageCollection(PCP_COL_ID).select('precipitation')
  .filterDate('2020-07-01', '2020-08-01').sum().multiply(SCALE_PCP).max(0);
var etb_jul_chk = aeti_mm_chk.subtract(computePe(pcp_mm_chk)).max(0);
print('  AETI  (expect 80–150 mm/month):',
  aeti_mm_chk.reduceRegion({ reducer: ee.Reducer.mean(), geometry: NILE_DELTA.buffer(20000), scale: 300, maxPixels: 1e6 }));
print('  ETb   (expect 70–140 mm/month):',
  etb_jul_chk.reduceRegion({ reducer: ee.Reducer.mean(), geometry: NILE_DELTA.buffer(20000), scale: 300, maxPixels: 1e6 }));

// Visualise
Map.setCenter(20, 20, 3);
Map.addLayer(luw_masked,
  {min: WEIGHT_THRESHOLD, max: 1, palette: ['#c7e9b4', '#41b6c4', '#225ea8']},
  'Land use weight (> threshold)');
Map.addLayer(etb_jul_chk.updateMask(luw_mask),
  {min: 0, max: 200, palette: ['white', '#fd8d3c', '#800026']},
  'ETb July 2020 (mm/month)');


// ═══════════════════════════════════════════════════════════════════════════
// EXPORT — one task per year (GEE runs them in parallel)
// ═══════════════════════════════════════════════════════════════════════════
// Typical runtime per task: 10–60 min at global 300m with tileScale=4.
//
// Task failure guide:
//   "Computation timed out"       → set TILE_SCALE = 8
//   "User memory limit exceeded"  → set TILE_SCALE = 16
//   "Asset not found" (land use)  → verify LANDUSE_ASSET path
//   "Asset not found" (WaPOR)     → collection ID wrong or no data for that period
//                                    verify: FAO/WAPOR/3/L1_AETI_M exists in your GEE search

for (var y = YEAR_START; y <= YEAR_END; y++) {
  var stats = processYear(y);

  Export.table.toDrive({
    collection:  stats,
    description: 'awp_gee_country_' + y,
    folder:      'WaPOR4AWP_GEE_outputs',
    fileFormat:  'CSV',
    selectors:   [
      'iso3', 'country_name', 'year',
      'n_months_aeti', 'n_months_pcp',
      'VETb_m3', 'irr_area_m2',
      'AETI_wsum', 'ETb_wsum',
      'landuse_source',
    ],
  });
}

print('Submitted ' + (YEAR_END - YEAR_START + 1) + ' export tasks ('
  + YEAR_START + '–' + YEAR_END + ') using land use: ' + LANDUSE_LABEL);
print('Download from Google Drive: WaPOR4AWP_GEE_outputs/');
print('Place CSVs in data/raw/gee_exports/ then run scripts/05_compute_annual_awp.py');
