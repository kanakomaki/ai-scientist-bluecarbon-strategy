// Collection 2対応版 GEEスクリプト（Olango Island中心、Landsat 8のみに統一）
// var rectangle = ee.Geometry.Rectangle([123.98, 10.23, 124.03, 10.29]);
// var dict = {"Name": "Cebu_1"};


var rectangle = ee.Geometry.Rectangle([123.75, 9.25, 124.25, 9.75]);
var dict = {"Name": "FL_1"};

// var rectangle = ee.Geometry.Rectangle([123.96, 10.22, 124.06, 10.32]);
// var dict = {"Name": "Olango_2"};
// GEEスクリプト（Landsat 8対応・Landsat 7モデル推論用のバンド順＋スケーリング対応）



// Cloud masking 用関数（Landsat 8）
function maskClouds(image) {
  var qa = image.select("QA_PIXEL");
  var cloudBitMask = 1 << 3;
  var mask = qa.bitwiseAnd(cloudBitMask).eq(0);
  return image.updateMask(mask);
}

// NDVI追加関数
function getNDVI(image) {
  return image.addBands(image.normalizedDifference(["SR_B5", "SR_B4"]).rename("NDVI"));
}

// === Landsat 8: 2020年 ===
var images_2020 = ee.ImageCollection("LANDSAT/LC08/C02/T1_L2")
  .filterBounds(rectangle)
  .filterDate("2020-01-01", "2020-12-31")
  .map(maskClouds)
  .map(getNDVI);

var ndvi_2020_composite = images_2020.median().clip(rectangle);

// マングローブラベル（2000年のグローバルマングローブ）
var mangroves_coll = ee.ImageCollection("LANDSAT/MANGROVE_FORESTS");
var mangroves = mangroves_coll.first().select(["1"], ["Mangroves"]).clip(rectangle);

// Landsat 8 → Landsat 7順にバンド名再構成
var reordered = ndvi_2020_composite.select([
  "SR_B2", // B1 (Blue)
  "SR_B3", // B2 (Green)
  "SR_B4", // B3 (Red)
  "SR_B5", // B4 (NIR)
  "SR_B6", // B5 (SWIR1)
  "ST_B10", // B6 (TIR1)
  "SR_B7"  // B7 (SWIR2)
]).rename(["B1", "B2", "B3", "B4", "B5", "B6", "B7"]);


// スケーリングするとき
// Reflectanceスケーリング（SR_Bx）: x0.0000275 - 0.2
var scaled_reflectance = reordered.select(['B1','B2','B3','B4','B5','B7'])
  .multiply(0.0000275)
  .subtract(0.2)
  .rename(['B1','B2','B3','B4','B5','B7']);

// Temperatureスケーリング（ST_B10）: x0.00341802 + 149.0
var scaled_tir = reordered.select('B6')
  .multiply(0.00341802)
  .add(149.0)
  .rename('B6');

// バンド統合＋NDVI＋ラベル＋unmask(0)
var image_2020_final = scaled_reflectance
  .addBands(scaled_tir)
  .addBands(ndvi_2020_composite.select("NDVI"))
  .addBands(mangroves.rename("Mangroves"))
  .unmask(0);

// 表示設定
var ndviPalette = [
  'FFFFFF', 'CE7E45', 'DF923D', 'F1B555', 'FCD163', '99B718',
  '74A901', '66A000', '529400', '3E8601', '207401', '056201',
  '004C00', '023B01', '012E01', '011D01', '011301'];

Map.centerObject(rectangle, 13);
Map.addLayer(image_2020_final.select("NDVI"), {min: 0, max: 1, palette: ndviPalette}, "NDVI 2020", false);
Map.addLayer(image_2020_final.select(["B3", "B2", "B1"]), {min: 0, max: 0.2}, "RGB 2020", false);
Map.addLayer(image_2020_final.select("Mangroves"), {min: 0, max: 1, palette: ["d40115"]}, "Mangroves in Rectangle", false);


// エクスポート
Export.image.toDrive({
  image: image_2020_final.select('B1', 'B2', 'B3', 'B4', 'B5', 'B6', 'B7', 'Mangroves', 'NDVI').toFloat(),
  //image: image_2020_final.toFloat(),
  description: dict.Name.concat("_2020_L8_L7ordered_scaled"),
  scale: 30,
  region: image_2020_final.geometry().bounds(),
  folder: "MangroveClassification",
  maxPixels: 2e9
});




