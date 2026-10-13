# syntax=docker/dockerfile:1
FROM python:3.12-slim-bookworm AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH" \
    OMP_NUM_THREADS=4 \
    MKL_NUM_THREADS=4

# QReader needs zbar; transitive dependencies also install non-headless OpenCV.
RUN apt-get update && apt-get install -y --no-install-recommends \
    libzbar0 libgl1 libglib2.0-0 libgomp1 \
    && rm -rf /var/lib/apt/lists/*

FROM runtime AS builder
COPY --from=ghcr.io/astral-sh/uv:0.13.0 /uv /usr/local/bin/uv
ENV UV_PROJECT_ENVIRONMENT=/opt/venv UV_LINK_MODE=copy \
    UV_HTTP_TIMEOUT=300 UV_CONCURRENT_DOWNLOADS=4
WORKDIR /build
COPY pyproject.toml uv.lock README.md ./
COPY vn_id ./vn_id
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev --no-editable --reinstall-package vn-id \
    && uv pip check --python /opt/venv/bin/python

FROM runtime
COPY --from=builder /opt/venv /opt/venv
RUN useradd --create-home --uid 10001 app \
    && mkdir -p /home/app/.cache/vn_id/.models/qrdet \
        /home/app/.cache/vn_id/.easyocr_models/model \
        /home/app/.cache/vn_id/.easyocr_models/user_network \
    && mkdir -p /home/app/.cache/tmp \
    && chown -R app:app /home/app/.cache
ENV TMPDIR=/home/app/.cache/tmp
USER app
WORKDIR /app
EXPOSE 8000
# Liveness only: the API loads OCR/QR models lazily.
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=4)"
CMD ["uvicorn", "vn_id.api.app:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
