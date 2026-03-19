#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

CONFIG_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/telegram-daily-html-summary"
ENV_FILE=""

if [[ -f ".env" ]]; then
  ENV_FILE=".env"
elif [[ -f "$CONFIG_DIR/.env" ]]; then
  ENV_FILE="$CONFIG_DIR/.env"
fi

if [[ -n "$ENV_FILE" ]]; then
  set -a
  # shellcheck disable=SC1091
  source "$ENV_FILE"
  set +a
fi

if [[ -n "${TG_SESSION_NAME:-}" && "${TG_SESSION_NAME}" != /* ]]; then
  if [[ -n "$ENV_FILE" ]]; then
    ENV_DIR="$(cd "$(dirname "$ENV_FILE")" && pwd)"
    TG_SESSION_NAME="$ENV_DIR/$TG_SESSION_NAME"
  else
    TG_SESSION_NAME="$ROOT_DIR/$TG_SESSION_NAME"
  fi
fi

python3 scripts/telegram_daily_html_summary.py \
  --window "${TG_SUMMARY_WINDOW:-yesterday}" \
  --timezone "${TG_SUMMARY_TIMEZONE:-Europe/Moscow}" \
  --output-dir "${TG_SUMMARY_OUTPUT_DIR:-output/telegram_daily_html}" \
  --session-name "${TG_SESSION_NAME:-telegram_user}" \
  --send-to-chat \
  "$@"
