# Advanced advisory tools

These first-stage modules are deliberately data-driven and conservative. They
add reusable soil interpretation, seed-data lookup, insect-pest symptom triage,
and satellite index calculations while keeping the core usable offline.

## Optional installation profiles

- `pip install -e '.[satellite]'` installs STAC and raster analysis tools.
- `pip install -e '.[soil]'` installs optional scientific-analysis libraries.
- `pip install -e '.[ai-local]'` installs ONNX Runtime for a separately supplied model.
- `pip install -e '.[ai]'` enables the optional hosted AI adapter.
- `pip install -e '.[all]'` installs the general integration set; it does not download model weights.

The index analyzer operates on already downloaded, co-registered arrays. It does
not fetch satellite imagery by itself. Soil interpretation requires real lab
measurements and does not infer a fertilizer dose. Seed rates and varieties come
from the repository knowledge base and remain explicitly unverified until local
agronomic authorities validate them. Pest triage is symptom-based, not a vision
model or verified diagnosis; it intentionally does not recommend pesticides.

Example APIs:

```python
from jazira_agri.soil.analyzer import SoilAnalyzer
from jazira_agri.crops.seed_advisor import SeedAdvisor
from jazira_agri.geo_spatial.index_analyzer import SatelliteIndexAnalyzer
from jazira_agri.advisor.pest_advisor import PestAdvisor

soil = SoilAnalyzer.analyze(ph=7.8, ec_ds_m=2.5, organic_matter_pct=1.4)
seed = SeedAdvisor.advise("wheat", "rainfed")
ndvi = SatelliteIndexAnalyzer.ndvi(red_band, nir_band)
pests = PestAdvisor.scout("wheat", ["insect_seen", "sticky_leaves"])
```

All recommendations should be checked against local sampling protocols, crop
varieties, field scouting, and agricultural extension guidance before action.
