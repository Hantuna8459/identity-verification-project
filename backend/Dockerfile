# syntax=docker/dockerfile:1.7
FROM ghcr.io/astral-sh/uv:0.8.15 AS uv

FROM python:3.12-slim AS model-fetcher
ENV SSL_CERT_FILE=/etc/ssl/certs/ca-certificates.crt
WORKDIR /app
COPY models/manifest.json /app/models/manifest.json
COPY scripts/models.py /app/scripts/models.py
COPY models/cccd_layout_yolov11.pt /tmp/cccd_layout_yolov11.pt
RUN --mount=type=cache,target=/var/cache/vid-models \
    --mount=type=secret,id=host_ca_bundle \
    if [ -f /run/secrets/host_ca_bundle ]; then \
      export SSL_CERT_FILE=/run/secrets/host_ca_bundle; \
      export REQUESTS_CA_BUNDLE=/run/secrets/host_ca_bundle; \
    fi; \
    python /app/scripts/models.py \
         --models-dir /app/models \
         --manifest /app/models/manifest.json \
         --profile technical_demo \
         --cache-dir /var/cache/vid-models \
         --artifact cccd-layout-yolov11=/tmp/cccd_layout_yolov11.pt

FROM python:3.12-slim AS builder
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_HTTP_TIMEOUT=300 \
    UV_HTTP_RETRIES=10 \
    PIP_DEFAULT_TIMEOUT=180 \
    PIP_RETRIES=10
WORKDIR /app/backend
COPY --from=uv /uv /uvx /bin/
COPY backend/pyproject.toml backend/uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=secret,id=host_ca_bundle \
    if [ -f /run/secrets/host_ca_bundle ]; then \
      export SSL_CERT_FILE=/run/secrets/host_ca_bundle; \
      export REQUESTS_CA_BUNDLE=/run/secrets/host_ca_bundle; \
      export PIP_CERT=/run/secrets/host_ca_bundle; \
    fi; \
    uv sync --frozen --no-dev --no-install-project
COPY backend/app ./app
COPY backend/ai_modules ./ai_modules
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=secret,id=host_ca_bundle \
    if [ -f /run/secrets/host_ca_bundle ]; then \
      export SSL_CERT_FILE=/run/secrets/host_ca_bundle; \
      export REQUESTS_CA_BUNDLE=/run/secrets/host_ca_bundle; \
      export PIP_CERT=/run/secrets/host_ca_bundle; \
    fi; \
    uv sync --frozen --no-dev

FROM python:3.12-slim AS runtime
ENV PATH=/app/backend/.venv/bin:$PATH \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HF_HUB_OFFLINE=1 \
    TRANSFORMERS_OFFLINE=1 \
    HF_HOME=/app/models/.cache/huggingface \
    TORCH_HOME=/app/models/.cache/torch \
    MODEL_DIR=/app/models \
    YOLO_CONFIG_DIR=/app/models/.cache/ultralytics \
    EVIDENCE_DIR=/app/data/evidence
WORKDIR /app/backend
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl ffmpeg libgl1 libglib2.0-0 libgomp1 \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --system --uid 10001 --create-home vid
COPY --from=builder /app/backend/.venv ./.venv
COPY --from=builder /app/backend/app ./app
COPY --from=builder /app/backend/ai_modules ./ai_modules
COPY --from=model-fetcher /app/models /app/models
COPY scripts/models.py /app/scripts/models.py
RUN python /app/scripts/models.py --models-dir /app/models --manifest /app/models/manifest.json --profile technical_demo --verify-only \
    && mkdir -p /app/data/evidence /app/models/.cache/ultralytics \
    && chown -R vid:vid /app/data /app/models/.cache
USER vid
EXPOSE 8000
HEALTHCHECK --interval=20s --timeout=5s --start-period=20s --retries=5 \
  CMD curl --fail http://localhost:8000/api/v2/utils/health-check || exit 1
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
