#!/usr/bin/env bash
# Fetch Chromium runtime libraries without sudo (for Playwright on minimal servers).
set -euo pipefail
ROOT=/tmp/pw-libs
mkdir -p "$ROOT"
cd "$ROOT"
PKGS=(
  libatk1.0-0t64 libatk-bridge2.0-0t64 libatspi2.0-0t64
  libcups2t64 libavahi-common3 libavahi-client3
  libdrm2 libgbm1 libxkbcommon0 libxcomposite1 libxdamage1 libxfixes3 libxrandr2
  libasound2t64 libpango-1.0-0 libcairo2 libnss3 libnspr4 libdbus-1-3
  libx11-6 libxcb1 libxext6 libxi6 libx11-xcb1 libxcb-dri3-0 libxshmfence1 libxss1 libxtst6
  libgtk-3-0t64 libgdk-pixbuf-2.0-0 libglib2.0-0t64
  libxrender1 libfontconfig1 libfreetype6 libharfbuzz0b libpng16-16 libpixman-1-0
  libwayland-client0 libwayland-cursor0 libwayland-egl1 libepoxy0 libegl1 libgl1 libvulkan1
  libudev1 libexpat1 libxml2 libsqlite3-0 liblcms2-2 libjpeg-turbo8 libwebp7 libtiff6
  libdatrie1 libthai0 libfribidi0 libgraphite2-3 libxcb-render0 libxcb-shm0 libxcursor1
  libxinerama1 libgtk-3-common libpangocairo-1.0-0 libpangoft2-1.0-0 libgdk-pixbuf2.0-common
  libcolord2 libdeflate0 libjbig0 libsharpyuv0 liblerc4 libbrotli1 libzstd1
)
for pkg in "${PKGS[@]}"; do
  apt-get download "$pkg" 2>/dev/null || true
done
for deb in "$ROOT"/*.deb; do
  [ -f "$deb" ] && dpkg -x "$deb" "$ROOT/root"
done
CHROME="$HOME/.cache/ms-playwright/chromium-1223/chrome-linux64/chrome"
export LD_LIBRARY_PATH="$ROOT/root/usr/lib/x86_64-linux-gnu:$ROOT/root/lib/x86_64-linux-gnu:${LD_LIBRARY_PATH:-}"
if "$CHROME" --version; then
  echo "OK: Chromium ready with LD_LIBRARY_PATH=$LD_LIBRARY_PATH"
  echo 'export LD_LIBRARY_PATH="'"$LD_LIBRARY_PATH"'"' > "$ROOT/env.sh"
else
  echo "Still missing libraries — run: sudo python3 -m playwright install-deps chromium" >&2
  exit 1
fi
