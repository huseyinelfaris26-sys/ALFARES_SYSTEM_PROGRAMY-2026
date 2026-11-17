## Application and database setup

The API dashboard is served at `/` and is Arabic/RTL and mobile-responsive. Login uses `JAZIRA_USERNAME`, `JAZIRA_PASSWORD`, and `SECRET_KEY` from a private `.env` file. Passwords and keys are never returned by the settings endpoint. Sessions use signed, HTTP-only cookies; in production the cookie is marked Secure. Set a random `SECRET_KEY` with at least 32 characters and use HTTPS in production.

For local installation on the laptop, see `deployments/INSTALL.md`. PostgreSQL/PostGIS is optional for Termux development. The Docker Compose setup initializes the schema in `data/sql/postgres_init.sql`, persists database files in a named volume, and starts the API only after PostgreSQL is healthy.

Install packages as needed: `.[api,postgres,test]` for the API/database/tests, `.[ml]` for XGBoost/MLflow, and `.[geo]` for geospatial dependencies. The machine-learning and geospatial integrations are optional; their dependencies have not been installed or validated on Android by this repository change.
