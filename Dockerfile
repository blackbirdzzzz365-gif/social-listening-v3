ARG CAMOUFOX_CACHE_IMAGE=camoufox-downloader

FROM node:20-slim AS frontend-builder

WORKDIR /build
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --no-audit
COPY frontend/ ./
RUN npm run build

FROM python:3.12-slim AS camoufox-downloader

WORKDIR /tmp
COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
RUN python -m camoufox fetch

FROM ${CAMOUFOX_CACHE_IMAGE} AS camoufox-cache

FROM python:3.12-slim

LABEL maintainer="social-listening-v3"
LABEL description="AI Facebook Social Listening - Phase 1"

RUN apt-get update && apt-get install -y --no-install-recommends \
    xvfb \
    x11vnc \
    novnc \
    websockify \
    libnss3-tools \
    libgtk-3-0 \
    libdbus-glib-1-2 \
    libxt6 \
    libasound2 \
    libx11-xcb1 \
    libxcomposite1 \
    libxdamage1 \
    libxrandr2 \
    libxss1 \
    libxtst6 \
    libpango-1.0-0 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    curl \
    procps \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY --from=camoufox-cache /root/.cache/camoufox /root/.cache/camoufox

COPY backend/ /app/
COPY --from=frontend-builder /build/dist/ /app/static/
COPY browser_web/ /app/browser-web/
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

RUN mkdir -p /data /root/.social-listening/browser_profile

ENV DISPLAY=:99
ENV PYTHONUNBUFFERED=1
ENV SQLITE_DB_PATH=/data/app.db
ENV BROWSER_PROFILE_DIR=/root/.social-listening/browser_profile
ENV BROWSER_MOCK_MODE=false
ENV CAMOUFOX_HEADLESS=false

EXPOSE 8000 6080

ENTRYPOINT ["/entrypoint.sh"]
