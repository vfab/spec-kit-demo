# ── Stage 1: dependency builder ───────────────────────────────────────────────
FROM python:3.12-slim AS builder

WORKDIR /build

# Install build dependencies (needed for psycopg2-binary, Pillow)
RUN apt-get update && apt-get install -y --no-install-recommends \
        gcc \
        libpq-dev \
        libjpeg-dev \
        zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python deps into an isolated prefix so we can copy them cleanly
COPY requirements.txt .
RUN pip install --upgrade pip \
    && pip install --prefix=/install --no-cache-dir -r requirements.txt \
    && pip install --prefix=/install --no-cache-dir gunicorn==21.2.0


# ── Stage 2: runtime image ────────────────────────────────────────────────────
FROM python:3.12-slim AS runtime

# Runtime system deps only (no build tools)
RUN apt-get update && apt-get install -y --no-install-recommends \
        libpq5 \
        libjpeg62-turbo \
        zlib1g \
    && rm -rf /var/lib/apt/lists/*

# Copy installed packages from builder
COPY --from=builder /install /usr/local

# Create a non-root user for security
RUN useradd --create-home --shell /bin/bash appuser

WORKDIR /app

# Copy application source
COPY . .

# SECRET_KEY here is a build-time-only throw-away value used solely so
# collectstatic can import Django settings without failing. The real
# SECRET_KEY is never baked into the image — it is injected at runtime
# via the .env file or container environment variables.
# hadolint ignore=DL3044
ENV SECRET_KEY=placeholder-for-collectstatic \
    DJANGO_SETTINGS_MODULE=ecommerce_site.settings \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN python manage.py collectstatic --noinput

# Ensure media directory exists and is owned by appuser
RUN mkdir -p /app/media && chown -R appuser:appuser /app

USER appuser

EXPOSE 8000

# Gunicorn: 2 workers per CPU core (adjust via GUNICORN_WORKERS env var)
CMD ["sh", "-c", "gunicorn ecommerce_site.wsgi:application \
    --bind 0.0.0.0:8000 \
    --workers ${GUNICORN_WORKERS:-3} \
    --timeout 120 \
    --access-logfile - \
    --error-logfile -"]
