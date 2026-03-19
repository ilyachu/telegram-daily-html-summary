# Telegram Daily HTML Summary

Инструмент для ежедневных Telegram-сводок.

Скрипт читает сообщения из одного Telegram-чата, собирает HTML-summary за прошлый календарный день и публикует его в другой чат или канал.

Что попадает в сводку:
- основные темы дня;
- репозитории и сервисы, которые обсуждали;
- другие полезные ссылки;
- ссылки на исходные сообщения в Telegram (`Источник` / `Обсуждение`).

## Что есть в репозитории

- `scripts/telegram_daily_html_summary.py` — основная логика
- `scripts/run_daily_summary.sh` — стабильная точка входа для ручного запуска и automation
- `.env.example` — шаблон конфигурации
- `scripts/requirements-telegram-summary.txt` — Python-зависимости

## Что нужно для запуска

1. Python 3.11+
2. Telegram `API_ID` и `API_HASH`
3. Session-файл Telethon для вашего Telegram-аккаунта

Важно: это user-account интеграция, а не бот через Bot API.

## 1. Как получить Telegram API credentials

1. Откройте [my.telegram.org](https://my.telegram.org/)
2. Войдите по номеру телефона
3. Создайте приложение
4. Скопируйте:
   - `API_ID`
   - `API_HASH`

## 2. Установка

```bash
git clone https://github.com/ilyachu/telegram-daily-html-summary.git
cd telegram-daily-html-summary
python3 -m pip install -r scripts/requirements-telegram-summary.txt
cp .env.example .env
```

## 3. Что менять в `.env`

Откройте `.env` и заполните:

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

### Что означает каждая переменная

- `TG_API_ID` — Telegram API ID
- `TG_API_HASH` — Telegram API hash
- `TG_SESSION_NAME` — путь-префикс к Telethon session-файлу
- `TG_SUMMARY_CHAT` — чат-источник, откуда читаем сообщения
- `TG_SUMMARY_CHAT_LABEL` — подпись в заголовке summary
- `TG_SUMMARY_WINDOW` — окно выборки; рекомендуемое значение: `yesterday`
- `TG_SUMMARY_TIMEZONE` — таймзона для daily-окна
- `TG_SUMMARY_OUTPUT_DIR` — каталог для сохранения артефактов
- `TG_SUMMARY_DESTINATION_CHAT` — чат или канал, куда отправлять итоговое summary

## 4. Первая авторизация

Если session-файла еще нет, при первом запуске Telethon попросит:
- номер телефона
- код из Telegram
- пароль 2FA, если он включен

После этого рядом появится локальный session-файл.

## 5. Ручной запуск

Рекомендуемый entrypoint:

```bash
./scripts/run_daily_summary.sh
```

Wrapper сам:
- загружает `.env`
- использует настройки окна и таймзоны
- отправляет итог в чат из `TG_SUMMARY_DESTINATION_CHAT`

### Примеры

Отправить в `Saved Messages`:

```bash
./scripts/run_daily_summary.sh --destination-chat me
```

Отправить в конкретный чат/канал:

```bash
./scripts/run_daily_summary.sh --destination-chat -1003631955503
```

Запустить для другого source-чата без правки `.env`:

```bash
./scripts/run_daily_summary.sh \
  --chat vibecod3rs \
  --chat-label "vibecod3rs"
```

## 6. Что сохраняется на диск

По умолчанию создаются:

- `output/telegram_daily_html/YYYY-MM-DD_<chat>_summary.html.txt`
- `output/telegram_daily_html/YYYY-MM-DD_<chat>_links.json`

## 7. Формат summary

Сообщение собирается как один Telegram HTML post.

Структура:
- `Основные темы`
- `Репозитории и сервисы`
- `Другие ссылки`

Для тем добавляется:
- `Источник`

Для ссылок добавляется:
- `Обсуждение`

## 8. Как менять source и destination

### Изменить source chat

В `.env`:

```dotenv
TG_SUMMARY_CHAT=your_source_chat
TG_SUMMARY_CHAT_LABEL=Your Chat Name
```

### Изменить destination chat

В `.env`:

```dotenv
TG_SUMMARY_DESTINATION_CHAT=me
```

или numeric chat/channel id:

```dotenv
TG_SUMMARY_DESTINATION_CHAT=-1003631955503
```

Использовать numeric ID надежнее, чем display title.

## 9. Automation в Codex

Рекомендуемый режим:
- каждый день
- `09:00`
- таймзона `Europe/Moscow`
- summary за прошлый календарный день

Команда для automation:

```bash
cd /path/to/telegram-daily-html-summary
./scripts/run_daily_summary.sh
```

## 10. Безопасность

Никогда не коммитьте:
- `.env`
- `*.session`
- реальные `API_HASH`
- любые приватные ключи и токены

Репозиторий можно публиковать только если секреты остаются локально.
