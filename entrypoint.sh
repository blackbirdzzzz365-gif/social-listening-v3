#!/bin/bash
set -euo pipefail

echo "========================================"
echo " Social Listening v3 - Starting..."
echo "========================================"

export DISPLAY="${DISPLAY:-:99}"
SCREEN_WIDTH="${BROWSER_SCREEN_WIDTH:-1600}"
SCREEN_HEIGHT="${BROWSER_SCREEN_HEIGHT:-900}"
DISPLAY_NUMBER="${DISPLAY#:}"
LOCK_FILE="/tmp/.X${DISPLAY_NUMBER}-lock"
SOCKET_DIR="/tmp/.X11-unix/X${DISPLAY_NUMBER}"

rm -f "$LOCK_FILE"
rm -f "$SOCKET_DIR"

echo "[1/5] Starting virtual display (Xvfb)..."
Xvfb "$DISPLAY" -screen 0 "${SCREEN_WIDTH}x${SCREEN_HEIGHT}x24" -ac +extension GLX +render -noreset &
XVFB_PID=$!
sleep 1
if ! kill -0 "$XVFB_PID" 2>/dev/null; then
  echo "ERROR: Xvfb failed to start"
  exit 1
fi
echo "  Xvfb running on $DISPLAY (${SCREEN_WIDTH}x${SCREEN_HEIGHT})"

echo "[2/5] Starting VNC server..."
VNC_ARGS="-display $DISPLAY -forever -shared -rfbport 5900"
if [ -n "${VNC_PASSWORD:-}" ]; then
  mkdir -p /root/.vnc
  x11vnc -storepasswd "$VNC_PASSWORD" /root/.vnc/passwd
  VNC_ARGS="$VNC_ARGS -rfbauth /root/.vnc/passwd"
else
  VNC_ARGS="$VNC_ARGS -nopw"
fi
x11vnc $VNC_ARGS >/tmp/x11vnc.log 2>&1 &
sleep 1
echo "  VNC server running on :5900"

echo "[3/5] Starting noVNC web client..."
NOVNC_PATH=$(find /usr/share -name "vnc.html" -path "*/novnc/*" 2>/dev/null | head -1 | xargs dirname || true)
if [ -z "${NOVNC_PATH:-}" ]; then
  NOVNC_PATH="/usr/share/novnc"
fi

CUSTOM_BROWSER_WEB="/tmp/social-listening-browser-web"
rm -rf "$CUSTOM_BROWSER_WEB"
mkdir -p "$CUSTOM_BROWSER_WEB"
cp -R "$NOVNC_PATH"/. "$CUSTOM_BROWSER_WEB"/
cp -R /app/browser-web/. "$CUSTOM_BROWSER_WEB"/

if [ -f "$CUSTOM_BROWSER_WEB/vnc.html" ]; then
  cp "$CUSTOM_BROWSER_WEB/vnc.html" "$CUSTOM_BROWSER_WEB/mobile.html"
  CUSTOM_BROWSER_WEB="$CUSTOM_BROWSER_WEB" python3 - <<'PY'
from pathlib import Path
import os

root = Path(os.environ["CUSTOM_BROWSER_WEB"])
mobile = root / "mobile.html"
content = mobile.read_text(encoding="utf-8")
content = content.replace("<title>noVNC</title>", "<title>Social Listening Browser</title>", 1)
injection = (
    '    <link rel="stylesheet" href="mobile-vnc.css">\n'
    '    <script type="module" src="mobile-vnc.js"></script>\n'
)
content = content.replace("</head>", f"{injection}</head>", 1)
mobile.write_text(content, encoding="utf-8")
PY
fi

websockify --web "$CUSTOM_BROWSER_WEB" 6080 localhost:5900 >/tmp/websockify.log 2>&1 &
sleep 1
echo "  browser web available at http://localhost:6080/"

echo "[4/5] Running database migrations..."
cd /app
alembic upgrade head
echo "  Database ready"

echo "[5/5] Starting application server..."
echo ""
echo "========================================"
echo " READY!"
echo ""
echo " App UI:     http://localhost:8000"
echo " Browser:    http://localhost:6080/vnc.html"
echo "========================================"
echo ""

exec uvicorn app.main:app \
  --host 0.0.0.0 \
  --port 8000 \
  --workers 1 \
  --log-level info
