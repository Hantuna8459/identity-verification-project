# syntax=docker/dockerfile:1.7
FROM python:3.12-slim AS model-fetcher
WORKDIR /app
COPY models/manifest.json /app/models/manifest.json
COPY scripts/models.py /app/scripts/models.py
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
      --include syncnet-v2 \
      --include s3fd-face

FROM python:3.12-slim
ENV PIP_DEFAULT_TIMEOUT=180 \
    PIP_RETRIES=10 \
    HF_HUB_OFFLINE=1 \
    TRANSFORMERS_OFFLINE=1 \
    DEVICE=cpu \
    WEIGHTS_DIR=/app/weights \
    S3FD_WEIGHTS=/app/weights/sfd_face.pth \
    SYNCNET_WEIGHTS=/app/weights/syncnet_v2.model
WORKDIR /app
RUN --mount=type=secret,id=host_ca_bundle \
    if [ -f /run/secrets/host_ca_bundle ]; then \
      export SSL_CERT_FILE=/run/secrets/host_ca_bundle; \
      export REQUESTS_CA_BUNDLE=/run/secrets/host_ca_bundle; \
      export PIP_CERT=/run/secrets/host_ca_bundle; \
    fi; \
    apt-get update \
    && apt-get install -y --no-install-recommends curl ffmpeg libgl1 libglib2.0-0 libgomp1 \
    && rm -rf /var/lib/apt/lists/*
COPY backend/ai_modules/lipsync/requirements.txt ./requirements.txt
RUN --mount=type=cache,target=/root/.cache/pip \
    --mount=type=secret,id=host_ca_bundle \
    if [ -f /run/secrets/host_ca_bundle ]; then \
      export SSL_CERT_FILE=/run/secrets/host_ca_bundle; \
      export REQUESTS_CA_BUNDLE=/run/secrets/host_ca_bundle; \
      export PIP_CERT=/run/secrets/host_ca_bundle; \
    fi; \
    pip install --upgrade pip \
    && pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu \
    && pip install -r requirements.txt
COPY backend/ai_modules/lipsync/app ./app
COPY --from=model-fetcher /app/models/lipsync /app/weights
RUN useradd --system --uid 10001 --create-home vid && chown -R vid:vid /app
USER vid
EXPOSE 8002
HEALTHCHECK --interval=30s --timeout=15s --start-period=120s --retries=3 \
  CMD curl --fail http://localhost:8002/health || exit 1
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8002"]
