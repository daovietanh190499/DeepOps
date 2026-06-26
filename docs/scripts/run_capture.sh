#!/usr/bin/env bash
# Capture Dohub docs screenshots (Playwright + Chromium).
# OTP được hỏi SAU khi script đăng nhập GitHub và email OTP tới — không hỏi từ đầu.
set -euo pipefail
cd "$(dirname "$0")/.."

if [[ -f .env.capture ]]; then
  # shellcheck disable=SC1091
  set -a && source .env.capture && set +a
fi

if [[ ! -f /tmp/pw-libs/env.sh ]]; then
  bash scripts/setup_chromium_libs.sh
fi
# shellcheck disable=SC1091
source /tmp/pw-libs/env.sh
export PLAYWRIGHT_BROWSERS_PATH="${PLAYWRIGHT_BROWSERS_PATH:-$HOME/.cache/ms-playwright}"

export DOHUB_URL="${DOHUB_URL:-https://hub.example.com}"
export DOCS_HEADLESS="${DOCS_HEADLESS:-1}"

# Không đọc OTP từ .env — chỉ nhập khi GitHub hiện trang xác minh
unset DOCS_GITHUB_OTP DOCS_ADMIN_OTP

if [[ -t 0 ]]; then
  echo "Chụp screenshot Dohub docs."
  if [[ -f .auth/user.json ]]; then
    echo "  • User: session đã lưu (.auth/user.json)"
  elif [[ -n "${DOCS_USER_COOKIE:-}" ]]; then
    echo "  • User: cookie Dohub (user_access_key)"
  else
    echo "  • User: đăng nhập mật khẩu — OTP hỏi sau khi GitHub gửi email"
  fi
  if [[ -f .auth/admin.json ]]; then
    echo "  • Admin: session đã lưu (.auth/admin.json)"
  elif [[ -n "${DOCS_ADMIN_COOKIE:-}" ]]; then
    echo "  • Admin: cookie Dohub (user_access_key)"
  else
    echo "  • Admin: đăng nhập mật khẩu — OTP hỏi sau khi GitHub gửi email"
  fi
  echo
fi

python3 scripts/capture_screenshots.py "$@"
python3 build.py
echo "Xong — ảnh trong assets/screenshots/, wiki đã rebuild."
