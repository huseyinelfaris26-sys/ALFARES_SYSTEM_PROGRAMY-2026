FROM python:3.12-slim
WORKDIR /app
COPY pyproject.toml README.md ./
COPY src ./src
COPY data ./data
COPY templates ./templates
RUN python -m pip install --no-cache-dir '.[api,postgres]'
EXPOSE 8000
CMD ["uvicorn", "jazira_agri.api.server:app", "--host", "0.0.0.0", "--port", "8000"]
