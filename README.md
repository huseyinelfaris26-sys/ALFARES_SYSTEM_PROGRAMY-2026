# JaziraAgri-OS

## Quick start

```bash
cd /data/data/com.termux/files/home/JaziraAgri-OS
python -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[geo,test,api]'
cp .env.example .env
python -m pytest -q
```

## Secure configuration

Create a local `.env` file for application settings without keeping secrets in GitHub. The default values are placeholders and should be updated before deployment.

```bash
cp .env.example .env
```

Available variables:

- `APP_NAME`
- `USERNAME`
- `PASSWORD`
- `API_KEY`
- `DEFAULT_KNOWLEDGE`
- `DB_HOST`
- `DB_PORT`
- `DB_NAME`
- `DB_USER`
- `DB_PASSWORD`
- `LOG_DIR`

## Knowledge bases

JaziraAgri-OS now includes two independent knowledge layers:

- `data/knowledge/crops.json`: general agricultural knowledge.
- `data/knowledge/syrian_crops.json`: region-specific Syrian crop knowledge, with first priority for wheat, barley, and cotton in Tal Abyad and Raqqa.

These layers remain separate. The Syrian knowledge base is intentionally kept as a draft local reference until validated by a local agronomic source.

## Local recommendation log

Every recommendation can be saved under `data/logs/recommendations/` through the `RecommendationLog` helper in `src/jazira_agri/core/engine.py`. This keeps a trace of the recommendation inputs, confidence, and the eventual outcome.

## FastAPI API

The API application is available in `src/jazira_agri/api/server.py` and is activated with the `api` extra:

```bash
python -m uvicorn jazira_agri.api.server:app --reload
```

The service exposes:

- `/health`
- `/settings`
- `/`

## PostgreSQL/PostGIS

The project includes optional PostgreSQL/PostGIS dependency groups in `pyproject.toml` for later spatial database use. Keep the database credentials in `.env` and do not commit them to GitHub.
