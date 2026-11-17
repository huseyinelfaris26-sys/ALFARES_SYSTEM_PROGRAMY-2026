# Advanced agronomy tools

These offline helpers use the local crop and disease knowledge base. Their outputs are preliminary decision-support information, not definitive diagnoses or treatment prescriptions.

## Soil assessment

```bash
jazira soil --ph 7.8 --ec 3.2 --organic-matter 1.1 --texture loam
```

Or in Python:

```python
from jazira_agri.soil import SoilAnalyzer

print(SoilAnalyzer(ph=7.8, salinity_ec=3.2, organic_matter=1.1, texture="loam").evaluate())
```

## Seed data

```bash
jazira seeds --crop wheat
```

`SeedAdvisor.recommend()` exposes seed varieties and rates from the repository knowledge base. Confirm locally whether the data is verified and suitable for the field.

## Symptom candidates

```bash
jazira pests --crop wheat --symptoms yellow_stripes,yellowing
```

This ranks known disease candidates from symptoms and is not a confirmed diagnosis. Seek local agronomic advice before treatment.

## Vegetation index

Install NumPy and use arrays in Python:

```bash
python -m pip install -e '.[analysis]'
```

```python
import numpy as np
from jazira_agri.geo_spatial import IndexAnalyzer

ndvi = IndexAnalyzer.ndvi(np.array([[10, 20]]), np.array([[20, 30]]))
print(ndvi, IndexAnalyzer.summarize(ndvi))
```

The `jazira indices --red VALUE --nir VALUE` CLI command is intended for simple scalar calculations; raster workflows should use the existing geospatial pipeline. No satellite imagery is downloaded by these helpers.
