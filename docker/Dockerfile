FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml ./
COPY apps ./apps
COPY scripts ./scripts
COPY docker/start.sh ./start.sh

RUN pip install --no-cache-dir . && chmod +x ./start.sh

# Default: create tables (idempotent) then run the web app. Render sets
# $PORT; falls back to 8000 locally.
CMD ["./start.sh"]
