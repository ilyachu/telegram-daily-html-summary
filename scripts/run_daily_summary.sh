#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

if [[ -f ".env" ]]; then
  set -a
  # shellcheck disable=SC1091
  source ".env"
  set +a
fi

python3 scripts/telegram_daily_html_summary.py \
  --window "${TG_SUMMARY_WINDOW:-yesterday}" \
  --timezone "${TG_SUMMARY_TIMEZONE:-Europe/Moscow}" \
  --output-dir "${TG_SUMMARY_OUTPUT_DIR:-output/telegram_daily_html}" \
  --session-name "${TG_SESSION_NAME:-telegram_user}" \
  --send-to-chat \
  "$@"
