# syntax=docker/dockerfile:1.7
FROM python:3.12-slim AS builder

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /build
COPY pyproject.toml README.md ./
COPY src ./src

# Use INSTALL_TARGET=".[prod]" for an image containing optional production clients.
ARG INSTALL_TARGET=.
RUN python -m pip wheel --wheel-dir /wheels "${INSTALL_TARGET}"

FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    APP_MODE=offline \
    DATABASE_URL=sqlite:///./data/contractguard.db \
    CONTRACT_GUARD_AUTH_REQUIRED=true \
    CONTRACT_GUARD_REGISTRATION_ENABLED=true \
    CONTRACT_GUARD_AUTH_COOKIE_SECURE=false \
    CONTRACT_GUARD_MAX_UPLOAD_BYTES=20971520 \
    CONTRACT_GUARD_MAX_DOCUMENT_PAGES=200 \
    CONTRACT_GUARD_MAX_DOCUMENT_CHARACTERS=1000000 \
    CONTRACT_GUARD_MAX_DOCX_UNCOMPRESSED_BYTES=104857600 \
    CONTRACT_GUARD_MAX_OCR_PIXELS=20000000 \
    APP_MODULE=contract_guard.main:app \
    HOST=0.0.0.0 \
    PORT=8000 \
    LOG_LEVEL=info

RUN groupadd --gid 10001 contractguard \
    && useradd --uid 10001 --gid contractguard --no-create-home \
        --home-dir /app --shell /usr/sbin/nologin contractguard

WORKDIR /app
COPY --from=builder /wheels /wheels
RUN python -m pip install --no-cache-dir /wheels/*.whl \
    && rm -rf /wheels
COPY --chown=contractguard:contractguard resources ./resources
COPY --chown=contractguard:contractguard scripts ./scripts

RUN mkdir -p /app/data \
    && chown -R contractguard:contractguard /app

USER contractguard
EXPOSE 8000
VOLUME ["/app/data"]

HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/live', timeout=2)" || exit 1

CMD ["sh", "-c", "exec python -m uvicorn \"$APP_MODULE\" --host \"$HOST\" --port \"$PORT\" --log-level \"$LOG_LEVEL\""]
