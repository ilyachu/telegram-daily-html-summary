# Telegram Daily HTML Summary

Daily digest for Telegram chats.

The tool reads messages from a source chat, builds one Telegram-safe HTML summary for the previous calendar day, and posts it into another chat or channel.

It focuses on:
- main topics of the day;
- repositories and services mentioned in chat;
- other useful links;
- source links back to the original Telegram messages (`Источник` / `Обсуждение`).

## What this repository contains

- `scripts/telegram_daily_html_summary.py` — main Python script
- `scripts/run_daily_summary.sh` — wrapper entrypoint for manual runs and automation
- `.env.example` — required configuration template
- `scripts/requirements-telegram-summary.txt` — Python dependencies

## Requirements

- Python 3.11+
- Telegram `API_ID` and `API_HASH`
- Telethon session for your Telegram account

## 1. Get Telegram credentials

Open [my.telegram.org](https://my.telegram.org/), log in with your phone number, create an app, and copy:

- `API_ID`
- `API_HASH`

These are user-account credentials, not bot credentials.

## 2. Install

```bash
git clone <your-repo-url>
cd telegram-daily-html-summary
python3 -m pip install -r scripts/requirements-telegram-summary.txt
cp .env.example .env
```

## 3. Configure `.env`

Edit `.env` and set:

```dotenv
TG_API_ID=123456
TG_API_HASH=your_hash_here
TG_SESSION_NAME=/absolute/path/to/telegram_user

TG_SUMMARY_CHAT=vibecod3rs
TG_SUMMARY_CHAT_LABEL=vibecod3rs
TG_SUMMARY_WINDOW=yesterday
TG_SUMMARY_TIMEZONE=Europe/Moscow
TG_SUMMARY_OUTPUT_DIR=output/telegram_daily_html
TG_SUMMARY_DESTINATION_CHAT=me
```

### What each variable means

- `TG_API_ID` — Telegram API ID
- `TG_API_HASH` — Telegram API hash
- `TG_SESSION_NAME` — Telethon session file path prefix
- `TG_SUMMARY_CHAT` — source chat to read from
- `TG_SUMMARY_CHAT_LABEL` — label shown in summary header
- `TG_SUMMARY_WINDOW` — summary window, recommended: `yesterday`
- `TG_SUMMARY_TIMEZONE` — timezone for the daily window
- `TG_SUMMARY_OUTPUT_DIR` — where artifacts are saved
- `TG_SUMMARY_DESTINATION_CHAT` — where the final summary is posted

## 4. First authorization

If the session file does not exist yet, the first run will ask for:

- phone number
- Telegram code
- 2FA password, if enabled

After that, Telethon creates a local session file.

## 5. Manual run

Recommended command:

```bash
./scripts/run_daily_summary.sh
```

The wrapper:
- loads `.env`
- uses the configured chat and destination
- builds the summary
- posts it to the destination chat

### Examples

Send to Saved Messages:

```bash
./scripts/run_daily_summary.sh --destination-chat me
```

Send to a specific chat/channel:

```bash
./scripts/run_daily_summary.sh --destination-chat -1003631955503
```

Override the source chat without changing `.env`:

```bash
./scripts/run_daily_summary.sh \
  --chat vibecod3rs \
  --chat-label "vibecod3rs"
```

## 6. Output files

By default the script saves:

- `output/telegram_daily_html/YYYY-MM-DD_<chat>_summary.html.txt`
- `output/telegram_daily_html/YYYY-MM-DD_<chat>_links.json`

## 7. Telegram formatting

The summary is built as one Telegram HTML message.

Sections:
- `Основные темы`
- `Репозитории и сервисы`
- `Другие ссылки`

Links include:
- `Источник` for topics
- `Обсуждение` for repo/service/link mentions

## 8. Automation in Codex

Recommended schedule:
- every day
- `09:00`
- timezone: `Europe/Moscow`
- window: previous calendar day

Recommended command for automation:

```bash
cd /path/to/telegram-daily-html-summary
./scripts/run_daily_summary.sh
```

## 9. How to change source and destination

### Change source chat

Edit:

```dotenv
TG_SUMMARY_CHAT=your_source_chat
TG_SUMMARY_CHAT_LABEL=Your Chat Name
```

### Change destination chat

Edit:

```dotenv
TG_SUMMARY_DESTINATION_CHAT=me
```

or use a numeric Telegram chat/channel id:

```dotenv
TG_SUMMARY_DESTINATION_CHAT=-1003631955503
```

Using numeric IDs is more reliable than display titles.

## 10. Security

Do not commit:
- `.env`
- `*.session`
- any real API keys or hashes

This repository is safe to publish only if you keep secrets local.
