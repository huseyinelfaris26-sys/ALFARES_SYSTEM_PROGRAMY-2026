# JaziraAgri-OS modular architecture

This feature branch adds modular entry points for the requested core, satellite, soil, crops, vision, weather, prediction, and API areas while retaining the existing package layout and CLI modules. No main-branch change is made.

Satellite clients define provider contracts and report `not_configured` until a STAC provider is explicitly set. Vegetation-index helpers compute values only from supplied calibrated reflectance. No credentials or imagery are bundled.

Crop profiles read the independent Syrian-priority knowledge database. That database is still a draft, and local varieties, thresholds, doses, and yields remain unknown until sourced and reviewed. Advice therefore reports missing data rather than issuing prescriptions. Yield/risk modules are model interfaces only and intentionally return no numeric prediction until a locally trained and validated model is supplied.

Weather utilities summarize supplied observations; forecast retrieval is optional and requires network access. Soil utilities retain provenance and do not infer lab results from SoilGrids. Vision utilities validate local image files but do not claim disease classification without a validated model.

Start the API with the optional API dependencies:

```bash
python -m pip install -e '.[api,test]'
python -m uvicorn jazira_agri.api.server:app --host 127.0.0.1 --port 8000
```

Run tests with `python -m pytest -q`.
