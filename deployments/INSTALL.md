# JaziraAgri-OS laptop setup

## Supported deployment scope

The lightweight Python package and tests work on Python 3.11+. Run PostgreSQL/PostGIS, FastAPI, and optional ML/GIS services on a laptop or server. Android/Termux remains suitable for CLI/basic tests; heavy GIS libraries and Docker are not assumed to work there.

## First-time setup (Linux/macOS)

```bash
git clone https://github.com/huseyinelfaris26-sys/JaziraAgri-OS.git
cd JaziraAgri-OS
git switch feat/syrian-crop-knowledge
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip setuptools wheel
python -m pip install -e '.[api,postgres,test]'
python scripts/create_local_env.py
python -m pytest -q
```

The setup script asks for the administrator password and creates a local `.env` with a salted password hash and randomly generated API, session-signing, and database secrets. `.env` is ignored by Git. Keep it private and do not paste it into chat or commit it.

For Windows PowerShell, activate with `.venv\\Scripts\\Activate.ps1`; otherwise follow the same commands using `py -m venv .venv`.

## Start PostgreSQL/PostGIS and API with Docker

Install Docker Desktop/Engine, then run from the repository root:

```bash
python -m pip install -e '.[api,postgres,test]'
python scripts/create_local_env.py
# Set DB_HOST=db in .env for the compose deployment.
docker compose --env-file .env -f deployments/docker-compose.yml up --build
```

Open `http://127.0.0.1:8000/`. The service binds to localhost only by default. The PostGIS container initializes `data/sql/postgres_init.sql` on first creation and stores durable data in a named volume. Initialization SQL is not re-run automatically for an existing volume; use a migration for later schema changes. The example database table includes geometry indexes and records for recommendations/field observations.

If running FastAPI directly instead of Docker, set `DB_HOST=localhost` in `.env`, ensure the PostgreSQL role/database exist, apply the schema with `psql -d jazira_agri -f data/sql/postgres_init.sql`, and run:

```bash
python -m uvicorn jazira_agri.api.server:app --host 127.0.0.1 --port 8000
```

## Optional stacks

Install only on the laptop, as required:

```bash
python -m pip install -e '.[ml]'   # XGBoost and MLflow Python client
python -m pip install -e '.[geo]'  # rasterio/GDAL, NumPy, Shapely, etc.
```

Run the optional MLflow tracking service using `docker compose --profile ml --env-file .env -f deployments/docker-compose.yml up`. The service is local-only on port 5000. XGBoost/MLflow dependencies are not needed for core app startup. SoilGrids geometry/data are not downloaded by these steps; the project stores the source/provenance reference and requires an explicit future import workflow.

## Verification

```bash
python -m pip check
python -m pytest -q
curl http://127.0.0.1:8000/health
```

Use the dashboard login form; `/api/knowledge`, `/api/dashboard`, and recommendation writes require the session cookie or configured `X-API-Key`. Do not expose the development service publicly. For deployment, use HTTPS, a reverse proxy, production cookie settings, secrets management, database backups, and schema migrations.
