/**
 * 01_prepare_gmie_asset.js
 *
 * Inspects the GMIE-100 image already uploaded at projects/wu-rsdata/assets/gmie,
 * zeroes out background pixels (-99), and exports a clean copy as gmie100_global.
 *
 * The source asset is a single Image (not a collection), so no mosaic is needed.
 *
 * Run this ONCE. When the export task shows COMPLETED in the Tasks panel,
 * the LANDUSE_ASSET in 02_export_country_awp.js is already set correctly.
 */

var GMIE_IMAGE = 'projects/wu-rsdata/assets/gmie';
var OUT_ASSET  = 'projects/wu-rsdata/assets/gmie100_global';

// ── Load as single Image ──────────────────────────────────────────────────────
var gmie_raw = ee.Image(GMIE_IMAGE);

print('Band names:',             gmie_raw.bandNames());
print('Projection:',             gmie_raw.projection());
print('Nominal scale (m):',      gmie_raw.projection().nominalScale());
print('All properties:',         gmie_raw.toDictionary());

// ── Zero out background (-99) and clamp to [0, 1] ────────────────────────────
var gmie = gmie_raw.where(gmie_raw.lt(0), 0).clamp(0, 1).rename('GMIE');

// ── Sanity checks ─────────────────────────────────────────────────────────────
var NILE_DELTA = ee.Geometry.Point([31.2, 30.5]);
var SAHARA     = ee.Geometry.Point([20.0, 22.0]);
var INDIA_IRR  = ee.Geometry.Point([75.5, 26.0]);

print('GMIE @ Nile Delta 50km box (expect 0.7-1.0):',
  gmie.reduceRegion({ reducer: ee.Reducer.mean(), geometry: NILE_DELTA.buffer(50000), scale: 1000, maxPixels: 1e6 }));
print('GMIE @ Sahara 50km box (expect ~0):',
  gmie.reduceRegion({ reducer: ee.Reducer.mean(), geometry: SAHARA.buffer(50000), scale: 1000, maxPixels: 1e6 }));
print('GMIE @ Rajasthan 50km box (expect moderate-high):',
  gmie.reduceRegion({ reducer: ee.Reducer.mean(), geometry: INDIA_IRR.buffer(50000), scale: 1000, maxPixels: 1e6 }));

// ── Visualise ─────────────────────────────────────────────────────────────────
Map.setCenter(31.2, 30.5, 5);
Map.addLayer(gmie,
  {min: 0, max: 1, palette: ['white', '#abd9e9', '#2166ac']},
  'GMIE-100 irrigation fraction');
Map.addLayer(gmie.updateMask(gmie.gt(0.1)),
  {min: 0.1, max: 1, palette: ['#fee090', '#fdae61', '#d73027']},
  'GMIE-100 > 0.1 (significant irrigation)', false);

// ── Export clean copy ─────────────────────────────────────────────────────────
// Only needed if you want a pre-cleaned asset. The main script (02) also applies
// background zeroing internally via prepareLanduseWeight(), so this is optional.
Export.image.toAsset({
  image:            gmie.float(),
  description:      'gmie100_global_clean',
  assetId:          OUT_ASSET,
  scale:            1000,
  crs:              'EPSG:4326',
  maxPixels:        1e13,
  pyramidingPolicy: {'.default': 'mean'},
});

print('Sanity checks printed above.');
print('Export task submitted for cleaned copy -> ' + OUT_ASSET);
print('You can also skip this export and use projects/wu-rsdata/assets/gmie directly.');
