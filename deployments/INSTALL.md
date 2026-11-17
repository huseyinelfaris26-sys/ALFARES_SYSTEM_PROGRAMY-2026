# Local laptop/deployment setup
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip setuptools wheel
python -m pip install -e '.[api,postgres,test]'
cp .env.example .env
# Edit .env and replace every CHANGE_THIS value with long, unique random values.
python -m pytest -q

# Start the API directly (requires configured environment)
python -m uvicorn jazira_agri.api.server:app --reload

# Or run PostgreSQL/PostGIS and the API with Docker Compose
# docker compose --env-file .env -f deployments/docker-compose.yml up --build

# Optional ML and GIS stacks (best installed on the laptop, not Android/Termux)
python -m pip install -e '.[ml]'
python -m pip install -e '.[geo]'
