#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
LOG_DIR="${HOME}/Library/Logs/telegram-daily-html-summary"
mkdir -p "$LOG_DIR"

OUT_LOG="$LOG_DIR/codex-automation-stdout.log"
ERR_LOG="$LOG_DIR/codex-automation-stderr.log"
SHELL_CMD="cd \"$ROOT_DIR\" && ./scripts/run_daily_summary.sh >> \"$OUT_LOG\" 2>> \"$ERR_LOG\""

/usr/bin/osascript "$ROOT_DIR/scripts/run_daily_summary.applescript" "$SHELL_CMD"
