"""Regression tests for NDVI geometry, grid alignment, and NoData handling."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

try:
    import numpy as np
    import rasterio
    from rasterio.transform import from_origin
    from jazira_agri.geo_spatial.sentinel_ndvi import NDVI_NODATA, SentinelNDVI, _aoi_bbox
except ImportError:  # geo dependencies are an optional installation extra
    np = None
    rasterio = None
    from_origin = None
    NDVI_NODATA = -9999.0
    SentinelNDVI = None
    _aoi_bbox = None


@unittest.skipIf(rasterio is None, "install the geo extra to run raster tests")
class SentinelNDVITests(unittest.TestCase):
    def _write_raster(self, path: Path, data, *, transform=None, nodata=-9999):
        with rasterio.open(
            path,
            "w",
            driver="GTiff",
            height=data.shape[0],
            width=data.shape[1],
            count=1,
            dtype="float32",
            crs="EPSG:4326",
            transform=transform or from_origin(39, 37, 0.01, 0.01),
            nodata=nodata,
        ) as dataset:
            dataset.write(data.astype("float32"), 1)

    def test_computes_ndvi_and_preserves_nodata(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            red = root / "red.tif"
            nir = root / "nir.tif"
            self._write_raster(red, np.array([[1, -9999], [0, 2]], dtype="float32"))
            self._write_raster(nir, np.array([[3, 5], [0, 6]], dtype="float32"))
            result_path = SentinelNDVI("unused", "2026-01-01", "2026-01-02", root / "cache").compute_ndvi(red, nir)
            with rasterio.open(result_path) as result:
                values = result.read(1)
            self.assertAlmostEqual(float(values[0, 0]), 0.5)
            self.assertEqual(float(values[0, 1]), NDVI_NODATA)
            self.assertEqual(float(values[1, 0]), NDVI_NODATA)
            self.assertAlmostEqual(float(values[1, 1]), 0.5)

    def test_rejects_misaligned_inputs(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            red = root / "red.tif"
            nir = root / "nir.tif"
            data = np.ones((2, 2), dtype="float32")
            self._write_raster(red, data)
            self._write_raster(nir, data, transform=from_origin(40, 37, 0.01, 0.01))
            assistant = SentinelNDVI("unused", "2026-01-01", "2026-01-02", root / "cache")
            with self.assertRaisesRegex(ValueError, "matching dimensions"):
                assistant.compute_ndvi(red, nir)

    def test_polygon_bbox_uses_all_vertices(self):
        aoi = {
            "features": [{
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[[39, 36], [40, 36], [40, 37], [39, 37], [39, 36]]],
                }
            }]
        }
        self.assertEqual(_aoi_bbox(aoi), [39.0, 36.0, 40.0, 37.0])

    def test_multipolygon_bbox_combines_polygons(self):
        aoi = {
            "features": [{
                "geometry": {
                    "type": "MultiPolygon",
                    "coordinates": [
                        [[[39, 36], [40, 36], [40, 37], [39, 36]]],
                        [[[41, 35], [42, 35], [42, 36], [41, 35]]],
                    ],
                }
            }]
        }
        self.assertEqual(_aoi_bbox(aoi), [39.0, 35.0, 42.0, 37.0])

    def test_rejects_invalid_aoi_coordinates(self):
        with self.assertRaisesRegex(ValueError, "coordinates"):
            _aoi_bbox({"features": [{"geometry": {"type": "Polygon", "coordinates": [[[200, 0]]]}}]})


if __name__ == "__main__":
    unittest.main()
