#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
LOG_DIR="${HOME}/Library/Logs/telegram-daily-html-summary"
mkdir -p "$LOG_DIR"

OUT_LOG="$LOG_DIR/codex-automation-stdout.log"
ERR_LOG="$LOG_DIR/codex-automation-stderr.log"
SHELL_CMD="cd \"$ROOT_DIR\" && ./scripts/run_daily_summary.sh >> \"$OUT_LOG\" 2>> \"$ERR_LOG\""

/usr/bin/osascript \
  -e 'on run argv' \
  -e 'set cmd to item 1 of argv' \
  -e 'do shell script "/bin/zsh -lc " & quoted form of cmd' \
  -e 'end run' \
  -- "$SHELL_CMD"
