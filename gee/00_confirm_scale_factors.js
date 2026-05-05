/**
 * ==============================================================================
 * 00_confirm_scale_factors.js (PUBLIC DATA VERSION)
 * ==============================================================================
 * MANDATORY FIRST STEP — Run this before executing any computation.
 *
 * Overview:
 * Since private Monthly access is restricted, this script directly inspects
 * the PUBLIC WaPOR Dekadal and CHIRPS Daily datasets to extract metadata
 * and scale factors.
 * ==============================================================================
 */

// Known irrigated test point (Nile Delta, Egypt) for sampling values
var TEST_POINT = ee.Geometry.Point([31.2, 30.5]);

// ==============================================================================
// 1. PUBLIC ASSET PATHS (Use these in your export scripts)
// ==============================================================================

// Public WaPOR v3 AETI (Dekadal / 10-day data)
var AETI_COL_ID = 'FAO/WAPOR/3/L1_AETI_D';

// Public Precipitation (CHIRPS Daily data — standard for WaPOR)
var PCP_COL_ID  = 'UCSB-CHG/CHIRPS/DAILY';

// ==============================================================================
// 2. INSPECT COLLECTIONS
// ==============================================================================

inspectCollection(AETI_COL_ID, 'Public WaPOR v3 AETI (Dekadal)');
inspectCollection(PCP_COL_ID,  'Public CHIRPS Precipitation (Daily)');

// ==============================================================================
// HELPER FUNCTION: EXTRACT & PRINT METADATA
// ==============================================================================

function inspectCollection(colId, label) {
  var col = ee.ImageCollection(colId);

  print('════════════════════════════════════════════════════════════');
  print('✓ INSPECTING PUBLIC COLLECTION: ' + label);
  print('  ↳ Asset Path:', colId);
  print('  ↳ Total Images (Public Catalog):', col.size());

  // Extract metadata from the chronologically first image
  var img = col.sort('system:time_start').first();
  var firstDate = ee.Date(img.get('system:time_start')).format('YYYY-MM-dd');

  print('  ↳ First Image Date:', firstDate);
  print('  ↳ Band Names:', img.bandNames());
  print('  ↳ Nominal Pixel Scale (m):', img.projection().nominalScale());

  // Define a 50km bounding box around the test point for spatial sampling
  var testBox = TEST_POINT.buffer(50000).bounds();

  // Calculate spatial statistics (Min, Max, Mean) within the test box
  var stats = img.reduceRegion({
    reducer: ee.Reducer.minMax().combine(ee.Reducer.mean(), null, true),
    geometry: testBox,
    scale: 300,
    maxPixels: 1e6
  });

  print('════════════════════════════════════════════════════════════');
  print('STATISTICS OVER 50KM NILE DELTA TEST BOX (' + label + '):', stats);
  print('Scale Factor Guide:');
  print('  → AETI Dekadal Scale Factor = 0.1 (Multiply by 0.1 for mm/dekad)');
  print('  → CHIRPS Daily Scale Factor = 1.0 (Already in mm/day)');
}
