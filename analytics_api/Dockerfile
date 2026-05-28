# Analytics API reads dbt marts from Postgres for the React dashboard.
# Local dev: DATABASE_URL should use host port 5433 when Postgres runs in Docker.

FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends libpq5 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements-analytics-api.txt /app/requirements-analytics-api.txt
RUN pip install --no-cache-dir -r requirements-analytics-api.txt

COPY shared /app/shared
COPY analytics_api /app/analytics_api
COPY pyproject.toml /app/pyproject.toml

ENV PYTHONPATH=/app
ENV ANALYTICS_API_HOST=0.0.0.0
ENV ANALYTICS_API_PORT=8001

EXPOSE 8001

CMD ["uvicorn", "analytics_api.main:app", "--host", "0.0.0.0", "--port", "8001"]
