# Optional integration guide / دليل التكامل الاختياري

JaziraAgri-OS already contains deterministic modules for seed and crop advice, photo-based disease hints, FAO-56 irrigation decisions, and Sentinel-2 NDVI. This guide adds a single facade and optional provider integrations without making the offline core depend on AI or network services.

## Install

```bash
# Core/offline use
python -m pip install -e .

# Weather API client
python -m pip install -e '.[weather]'

# Optional OpenAI summary adapter
python -m pip install -e '.[ai]'

# Raster/satellite and all optional integrations
python -m pip install -e '.[geo]'
python -m pip install -e '.[all]'
```

Optional geospatial libraries include native components; use the installation guidance for your operating system if Rasterio cannot be installed from a wheel. Do not install every large ML framework by default: select a model/runtime that matches the target device and deploy it behind the `ImageClassifier` interface in `advisor.diagnose`.

## Unified field assessment

```python
from jazira_agri.intelligence import FieldAssistant

assistant = FieldAssistant()  # offline deterministic mode
result = assistant.assess(
    crop="wheat",
    farming="rainfed",
    region="tal_abyad",
    seasonal_rain_mm=280,
    symptoms=["yellow_stripes"],
)
print(result["crop_advice"])
print(result["diagnosis"])
```

The facade can also accept `DailyWeather` and `FieldConditions` from `jazira_agri.intelligence.deficit_irrigation` together to add the irrigation engine result. `weather_observation` can hold a forecast returned by `WeatherForecast`; network fetching remains an explicit caller choice.

## OpenAI summary (optional)

Set `OPENAI_API_KEY` in the runtime environment (never commit it), optionally set `JAZIRA_AI_MODEL`, then instantiate `FieldAssistant(ai_provider=OpenAIAgricultureAI())`. The AI receives calculated advice and not the original photo or local stored-photo path. If the AI call fails, the field assessment still returns deterministic results and sets `ai_error`.

AI output is an explanatory summary only. It must not be treated as a verified diagnosis, pesticide prescription, seed guarantee, or substitute for local agronomic expertise. Review the external provider's data-retention and privacy terms before sending farm data.

## Weather

```python
from jazira_agri.weather.forecast import WeatherForecast

forecast = WeatherForecast(36.5, 39.0).get_7day()
if forecast is None:
    print("Forecast unavailable; use local observations or cached data")
```

The client has a request timeout, validates coordinates, and returns `None` on transport/API errors. Forecast availability and accuracy depend on the upstream service and location.

## Supported engines and extension points

- Crop/seed/fertilizer/yield: `jazira_agri.advisor.recommend`
- Photo symptom/color diagnosis, optional model adapter: `jazira_agri.advisor.diagnose`
- Irrigation and water/salinity calculations: `jazira_agri.intelligence.deficit_irrigation`
- Satellite bands and NDVI: `jazira_agri.geo_spatial.sentinel_ndvi`
- Weather: `jazira_agri.weather.forecast`
- Unified result composition: `jazira_agri.intelligence.FieldAssistant`

Use calibrated local data and validate recommendations with agronomists before operational decisions. External APIs and satellite products require connectivity; the existing local engines can operate without them.
