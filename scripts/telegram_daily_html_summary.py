#!/usr/bin/env python3
import argparse
import asyncio
import html
import json
import os
import re
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Iterable, Optional
from urllib.parse import urlparse
from zoneinfo import ZoneInfo

from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError


URL_RE = re.compile(r"https?://[^\s<>\]\)]+")

STOPWORDS = {
    "это", "как", "что", "для", "или", "вот", "про", "надо", "есть", "если", "уже",
    "только", "когда", "потом", "тоже", "вообще", "просто", "через", "чтобы", "где",
    "кто", "так", "там", "его", "она", "они", "меня", "тебя", "если", "если", "ещё",
    "очень", "много", "после", "под", "мой", "твой", "этот", "эта", "эти", "всем",
    "привет", "спасибо", "можно", "какой", "какая", "какие", "нужно", "нужен", "нужна",
    "код", "чате", "чат", "день", "дня", "дням", "было", "были", "будет",
}

SYSTEM_PATTERNS = [
    re.compile(r"поступила оплата по сделке", re.IGNORECASE),
    re.compile(r"ответственный за сделку", re.IGNORECASE),
    re.compile(r"ссылка на сделку", re.IGNORECASE),
    re.compile(r"оплачено в гк", re.IGNORECASE),
    re.compile(r"сумма платежа", re.IGNORECASE),
    re.compile(r"бюджет сделки", re.IGNORECASE),
    re.compile(r"ostалось оплатить", re.IGNORECASE),
]

TOPIC_RULES = [
    ("Транскрибация и speech-to-text", ("транскриб", "расшифров", "надиктов", "speech", "whisper", "диктов", "аудио", "встреч")),
    ("Claude, Cursor и AI-инструменты", ("claude", "cursor", "copilot", "code assist", "gemini", "kiro", "opus", "minimax", "кодекс")),
    ("Блокировки и платежи Anthropic", ("бан", "блокиров", "антропик", "anthropic", "карта", "gift", "prepaid", "refau", "рефанд", "оплата")),
    ("MCP, skills и агентные воркфлоу", ("mcp", "скилл", "skill", "skills", "agent", "агент", "оркестратор", "opencode")),
    ("Саммери встреч и боты", ("summary", "саммери", "fathom", "бот", "встреч", "клиент", "созвон")),
]


@dataclass
class MessageRecord:
    message_id: int
    date: str
    sender_name: str
    text: str
    reply_to_msg_id: Optional[int]


@dataclass
class LinkRecord:
    url: str
    domain: str
    kind: str
    sender_name: str
    date: str
    message_id: int
    context: str
    label: str
    description: str


def build_message_link(chat: str, message_id: int) -> Optional[str]:
    if not chat or chat.startswith("-") or " " in chat:
        return None
    return f"https://t.me/{chat}/{message_id}"


def normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip())


def is_system_message(sender_name: str, text: str) -> bool:
    lowered = text.lower().strip()
    if sender_name.lower().startswith("уведомления"):
        return True
    return any(pattern.search(lowered) for pattern in SYSTEM_PATTERNS)


def strip_urls(text: str) -> str:
    return URL_RE.sub("", text).strip()


def classify_link(url: str) -> str:
    host = (urlparse(url).netloc or "").lower()
    if any(domain in host for domain in ("github.com", "gitlab.com", "codeberg.org", "bitbucket.org")):
        return "repository"
    if any(domain in host for domain in ("youtube.com", "youtu.be")):
        return "media"
    if "t.me" in host:
        return "telegram"
    if any(domain in host for domain in ("x.com", "twitter.com", "medium.com", "substack.com", "habr.com")):
        return "article"
    return "service"


def repo_label_from_url(url: str) -> str:
    parsed = urlparse(url)
    parts = [p for p in parsed.path.split("/") if p]
    if len(parts) >= 2:
        return "/".join(parts[:2])
    if parts:
        return parts[0]
    return parsed.netloc


def service_label_from_url(url: str) -> str:
    parsed = urlparse(url)
    host = parsed.netloc.lower().removeprefix("www.")
    if host == "youtu.be":
        return "YouTube"
    if host == "t.me":
        parts = [p for p in parsed.path.split("/") if p]
        return parts[0] if parts else "Telegram"
    return host


def clean_context(text: str) -> str:
    text = strip_urls(text)
    text = re.sub(r"@\w+", "", text)
    text = re.sub(r"\s+", " ", text).strip(" -–—")
    return text


def is_same_chat_deeplink(url: str, chat: str) -> bool:
    parsed = urlparse(url)
    if "t.me" not in parsed.netloc.lower():
        return False
    parts = [p for p in parsed.path.split("/") if p]
    return len(parts) >= 2 and parts[0].lower() == chat.lower()


def best_context_for_message(messages: list[MessageRecord], idx: int) -> str:
    current = clean_context(messages[idx].text)
    if current:
        return current

    candidates: list[str] = []
    for offset in (-3, -2, -1, 1, 2, 3):
        j = idx + offset
        if 0 <= j < len(messages):
            candidate = clean_context(messages[j].text)
            if candidate:
                candidates.append(candidate)

    def score(text: str) -> tuple[int, int]:
        lowered = text.lower()
        informative = 1 if len(text) >= 25 else 0
        bonus = 0
        if any(token in lowered for token in ("репо", "опенсорс", "инструмент", "сервис", "поиск", "дизайн", "speech", "расшифров", "бесплатн", "локальн")):
            bonus += 2
        if text.endswith("?"):
            bonus -= 1
        return (informative + bonus, len(text))

    if candidates:
        candidates.sort(key=score, reverse=True)
        return candidates[0]
    return ""


def summarize_link_context(contexts: Iterable[str], kind: str, url: str) -> tuple[str, str]:
    contexts = [c for c in contexts if c]
    base = contexts[0] if contexts else ""
    if kind == "repository":
        label = repo_label_from_url(url)
        description = compress_description(base, kind, url) or "Репозиторий, который обсуждали в чате."
        return label, description
    label = service_label_from_url(url)
    if not base:
        host = urlparse(url).netloc.lower()
        if "exa.ai" in host:
            return label, "Поисковый сервис для AI-агентов и исследовательских задач."
        if "handy.computer" in host:
            return label, "Локальный speech-to-text инструмент для быстрой надиктовки текста."
        if any(domain in host for domain in ("v0.app", "21st.dev", "variant.com")):
            return label, "Инструмент для генерации и подбора UI/дизайн-референсов."
        if "status.claude.com" in host:
            return label, "Статус-страница Claude для проверки сбоев и инцидентов."
        if kind == "media":
            return label, "Видео или медиа-ссылка, которую принесли как пример или обзор."
        if kind == "telegram":
            return label, "Telegram-ссылка, которую скинули в контексте обсуждения."
        if kind == "article":
            return label, "Статья или пост, который использовали как источник или кейс."
        return label, "Сервис или инструмент, который обсуждали в чате."
    return label, compress_description(base, kind, url)


def compress_description(text: str, kind: str, url: str) -> str:
    text = clean_context(text)
    if not text:
        return ""

    host = urlparse(url).netloc.lower()
    lowered = text.lower()

    if kind == "repository":
        if "skill" in lowered or "скилл" in lowered:
            return "Репозиторий со skills для агентной разработки."
        if "локаль" in lowered or "полностью локаль" in lowered:
            return "Локальная версия инструмента, которую принесли на тест."
        if "прокси" in lowered or "router" in lowered:
            return "Прокси-роутер для CLI/API интеграций."
        return "Репозиторий, который обсуждали как полезный инструмент."

    if "21st.dev" in host or "v0.app" in host or "variant.com" in host:
        return "Инструмент для UI-референсов и генерации интерфейсов."
    if "exa.ai" in host:
        return "Поисковый сервис для research-задач и извлечения данных."
    if "handy.computer" in host:
        return "Бесплатный open-source speech-to-text инструмент для macOS."
    if "status.claude.com" in host:
        return "Статус-страница Claude для проверки сбоев."
    if "dashboard.hydraai.ru" in host:
        return "Каталог моделей; обсуждали низкие цены на токены."
    if "anthropic.com" in host:
        return "Материал Anthropic про ожидания пользователей от AI."
    if "macrumors.com" in host:
        return "Новость про Apple и ограничения для vibe-coding приложений."
    if "google" in host and "stitch" in url:
        return "Пост про Stitch и генерацию UI."
    if kind == "telegram":
        if "mcp" in lowered:
            return "Telegram-пост про MCP и веб-поиск."
        return "Telegram-ссылка, которую использовали как пример или источник."
    if kind == "article":
        return "Статья или пост, который обсуждали в чате."
    if kind == "media":
        return "Видео или эфир, который привели как пример."

    text = re.sub(r"\s+", " ", text).strip()
    if len(text) > 90:
        text = text[:87].rstrip(" ,.:;!-") + "..."
    return text


def infer_topics(messages: list[MessageRecord], max_topics: int = 4) -> list[str]:
    scores = Counter()
    for message in messages:
        lowered = message.text.lower()
        for label, markers in TOPIC_RULES:
            if any(marker in lowered for marker in markers):
                scores[label] += 1
    return [label for label, _ in scores.most_common(max_topics)]


def topic_source_links(messages: list[MessageRecord], topics: list[str], chat: str) -> dict[str, str]:
    result: dict[str, str] = {}
    for label in topics:
        markers = None
        for rule_label, rule_markers in TOPIC_RULES:
            if rule_label == label:
                markers = rule_markers
                break
        if not markers:
            continue
        for message in messages:
            lowered = message.text.lower()
            if any(marker in lowered for marker in markers):
                link = build_message_link(chat, message.message_id)
                if link:
                    result[label] = link
                break
    return result


def extract_links(messages: list[MessageRecord], chat: str) -> list[LinkRecord]:
    grouped: dict[str, list[tuple[MessageRecord, str]]] = defaultdict(list)
    for idx, message in enumerate(messages):
        for url in URL_RE.findall(message.text):
            if is_same_chat_deeplink(url, chat):
                continue
            grouped[url].append((message, best_context_for_message(messages, idx)))

    links = []
    for url, items in grouped.items():
        items.sort(key=lambda pair: pair[0].date)
        domain = urlparse(url).netloc.lower().removeprefix("www.")
        kind = classify_link(url)
        label, description = summarize_link_context([ctx for _, ctx in items], kind, url)
        if kind == "telegram" and "которую скинули в контексте обсуждения" in description.lower():
            continue
        links.append(
            LinkRecord(
                url=url,
                domain=domain,
                kind=kind,
                sender_name=items[-1][0].sender_name,
                date=items[-1][0].date,
                message_id=items[-1][0].message_id,
                context=items[-1][1],
                label=label,
                description=description,
            )
        )

    priority = {"repository": 0, "service": 1, "telegram": 2, "article": 3, "media": 4}
    links.sort(key=lambda item: (priority.get(item.kind, 99), item.domain, item.url))
    return links


def build_html_summary(chat: str, chat_label: str, start_local: datetime, end_local: datetime, messages: list[MessageRecord], links: list[LinkRecord]) -> str:
    topics = infer_topics(messages)
    topic_links = topic_source_links(messages, topics, chat)
    repo_and_services = [link for link in links if link.kind in {"repository", "service"}]
    other_links = [link for link in links if link.kind not in {"repository", "service"}]

    lines = [
        f"<b>{html.escape(chat_label)} — daily summary</b>",
        f"<i>{html.escape(start_local.strftime('%d.%m.%Y'))}</i>",
        "",
    ]

    if topics:
        lines.append("<b>Основные темы</b>")
        for topic in topics[:4]:
            link = topic_links.get(topic)
            if link:
                lines.append(
                    f"• {html.escape(topic)} <a href=\"{html.escape(link, quote=True)}\">Источник</a>"
                )
            else:
                lines.append(f"• {html.escape(topic)}")
        lines.append("")

    if repo_and_services:
        lines.append("<b>Репозитории и сервисы</b>")
        for link in repo_and_services[:10]:
            desc = html.escape(link.description[:180])
            label = html.escape(link.label)
            msg_link = build_message_link(chat, link.message_id)
            suffix = (
                f' <a href="{html.escape(msg_link, quote=True)}">Обсуждение</a>'
                if msg_link
                else ""
            )
            lines.append(f"• <a href=\"{html.escape(link.url, quote=True)}\">{label}</a> — {desc}{suffix}")
        lines.append("")

    if other_links:
        lines.append("<b>Другие ссылки</b>")
        for link in other_links[:6]:
            desc = html.escape(link.description[:140])
            label = html.escape(link.label)
            msg_link = build_message_link(chat, link.message_id)
            suffix = (
                f' <a href="{html.escape(msg_link, quote=True)}">Обсуждение</a>'
                if msg_link
                else ""
            )
            lines.append(f"• <a href=\"{html.escape(link.url, quote=True)}\">{label}</a> — {desc}{suffix}")
        lines.append("")

    if not repo_and_services and not other_links:
        lines.append("<b>Ссылок за день не было</b>")
        lines.append("")

    message = "\n".join(lines).strip()
    return fit_to_telegram_limit(message)


def fit_to_telegram_limit(message: str, limit: int = 4000) -> str:
    if len(message) <= limit:
        return message

    lines = message.splitlines()
    while len("\n".join(lines)) > limit and lines:
        # Prefer removing last non-header bullet.
        for idx in range(len(lines) - 1, -1, -1):
            if lines[idx].startswith("• "):
                lines.pop(idx)
                break
        else:
            lines.pop()

    result = "\n".join(lines).strip()
    if len(result) > limit:
        result = result[: limit - 3].rstrip() + "..."
    return result


async def build_client(session_name: str, api_id: int, api_hash: str) -> TelegramClient:
    client = TelegramClient(session_name, api_id, api_hash)
    await client.connect()
    if not await client.is_user_authorized():
        phone = input("Telegram phone number (international format): ").strip()
        await client.send_code_request(phone)
        code = input("Telegram code: ").strip()
        try:
            await client.sign_in(phone=phone, code=code)
        except SessionPasswordNeededError:
            password = input("Telegram 2FA password: ").strip()
            await client.sign_in(password=password)
    return client


async def resolve_destination(client: TelegramClient, destination: str):
    destination = destination.strip()
    if re.fullmatch(r"-?\d+", destination):
        try:
            return await client.get_entity(int(destination))
        except Exception:
            pass
    return await client.get_entity(destination)


async def fetch_messages_for_window(client: TelegramClient, chat: str, start_utc: datetime, end_utc: datetime) -> list[MessageRecord]:
    entity = await client.get_entity(chat)
    records: list[MessageRecord] = []
    async for message in client.iter_messages(entity, reverse=False):
        if not message.date:
            continue
        message_utc = message.date.astimezone(timezone.utc)
        if message_utc < start_utc:
            break
        if message_utc >= end_utc:
            continue
        text = normalize_text(message.message or "")
        sender = await message.get_sender()
        sender_name = (
            getattr(sender, "first_name", None)
            or getattr(sender, "title", None)
            or getattr(sender, "username", None)
            or "Unknown"
        )
        sender_last = getattr(sender, "last_name", None)
        if sender_last:
            sender_name = f"{sender_name} {sender_last}".strip()
        if not text or is_system_message(sender_name, text):
            continue
        records.append(
            MessageRecord(
                message_id=message.id,
                date=message_utc.isoformat(),
                sender_name=sender_name,
                text=text,
                reply_to_msg_id=getattr(getattr(message, "reply_to", None), "reply_to_msg_id", None),
            )
        )
    return records


async def main_async(args: argparse.Namespace) -> None:
    api_id = int(os.environ.get("TG_API_ID") or args.api_id or 0)
    api_hash = os.environ.get("TG_API_HASH") or args.api_hash
    if not api_id or not api_hash:
        raise SystemExit("Missing TG_API_ID or TG_API_HASH.")

    tz = ZoneInfo(args.timezone)
    now_local = datetime.now(tz)
    if args.window == "yesterday":
        end_local = now_local.replace(hour=0, minute=0, second=0, microsecond=0)
        start_local = end_local - timedelta(days=1)
    else:
        end_local = now_local
        start_local = end_local - timedelta(hours=args.hours)
    start_utc = start_local.astimezone(timezone.utc)
    end_utc = end_local.astimezone(timezone.utc)

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    client = await build_client(args.session_name, api_id, api_hash)
    try:
        messages = await fetch_messages_for_window(client, args.chat, start_utc, end_utc)
        links = extract_links(messages, args.chat)
        html_summary = build_html_summary(args.chat, args.chat_label or args.chat, start_local, end_local, messages, links)

        stamp = end_local.strftime("%Y-%m-%d")
        summary_path = output_dir / f"{stamp}_{args.chat.replace('/', '_')}_summary.html.txt"
        data_path = output_dir / f"{stamp}_{args.chat.replace('/', '_')}_links.json"
        summary_path.write_text(html_summary, encoding="utf-8")
        data_path.write_text(
            json.dumps([asdict(link) for link in links], ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        print(f"messages={len(messages)} links={len(links)}")
        print(summary_path)
        print(data_path)
        print("----HTML----")
        print(html_summary)

        if args.send_to_saved or args.send_to_chat:
            destination = args.destination_chat or "me"
            entity = await resolve_destination(client, destination)
            await client.send_message(entity, html_summary, parse_mode="html")
    finally:
        await client.disconnect()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build Telegram-safe HTML daily summary for a chat.")
    parser.add_argument("--chat", default=os.environ.get("TG_SUMMARY_CHAT"))
    parser.add_argument("--chat-label", default=os.environ.get("TG_SUMMARY_CHAT_LABEL"))
    parser.add_argument("--hours", type=int, default=24)
    parser.add_argument("--window", choices=["rolling", "yesterday"], default=os.environ.get("TG_SUMMARY_WINDOW", "yesterday"))
    parser.add_argument("--timezone", default=os.environ.get("TG_SUMMARY_TIMEZONE", "Europe/Moscow"))
    parser.add_argument("--output-dir", default=os.environ.get("TG_SUMMARY_OUTPUT_DIR", "output/telegram_daily_html"))
    parser.add_argument("--session-name", default=os.environ.get("TG_SESSION_NAME", "telegram_user"))
    parser.add_argument("--send-to-saved", action="store_true")
    parser.add_argument("--send-to-chat", action="store_true")
    parser.add_argument("--destination-chat", default=os.environ.get("TG_SUMMARY_DESTINATION_CHAT"))
    parser.add_argument("--api-id")
    parser.add_argument("--api-hash")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    if not args.chat:
        raise SystemExit("Missing chat. Pass --chat or set TG_SUMMARY_CHAT.")
    asyncio.run(main_async(args))


if __name__ == "__main__":
    main()
