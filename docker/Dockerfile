FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml ./
COPY apps ./apps
COPY scripts ./scripts

RUN pip install --no-cache-dir .

# Default: run the web app (Render sets $PORT; falls back to 8000 locally).
# Override the command on the Render Cron Job to:
#   python -m apps.pipeline.run_daily
CMD ["sh", "-c", "uvicorn apps.web.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
