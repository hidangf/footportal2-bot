#!/usr/bin/env python3
"""ФУТПОРТАЛ 2: публикация готовых пародийных постов из GitHub, без OpenAI API."""
from __future__ import annotations
import argparse
import html
import json
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parent
QUEUE_DIR = ROOT / "queue"
STATE_FILE = ROOT / "data" / "sent.json"

def load_state():
    if not STATE_FILE.exists():
        return {"sent_files": [], "sent_urls": [], "sent_commentary_keys": []}
    data = json.loads(STATE_FILE.read_text(encoding="utf-8"))
    return {"sent_files": data.get("sent_files", []), "sent_urls": data.get("sent_urls", []),
            "sent_commentary_keys": data.get("sent_commentary_keys", [])}

def save_state(state):
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    state["sent_files"] = state["sent_files"][-5000:]
    state["sent_urls"] = state["sent_urls"][-5000:]
    state["sent_commentary_keys"] = state.get("sent_commentary_keys", [])[-5000:]
    tmp = STATE_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(STATE_FILE)

def url_key(url):
    p = urlsplit(url.strip())
    return p.scheme.lower() + "://" + p.netloc.lower() + p.path.rstrip("/")

def validate(post):
    if not isinstance(post, dict):
        raise ValueError("Пост должен быть JSON-объектом")
    for key in ("title", "body", "source_url"):
        if not isinstance(post.get(key), str):
            raise ValueError("Нет поля " + key)
    title, body, source = (post[k].strip() for k in ("title", "body", "source_url"))
    if not 10 <= len(title) <= 190 or not 120 <= len(body) <= 3200:
        raise ValueError("Неверная длина текста")
    parsed = urlsplit(source)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc or parsed.username or parsed.password:
        raise ValueError("Неверная ссылка на спортивную новость")
    if re.search(r"[\r\n]", source):
        raise ValueError("Переносы строк в ссылке")
    name = str(post.get("source_name", "Источник")).strip()[:80] or "Источник"
    kind = str(post.get("kind", "news")).strip()
    if kind not in {"news", "commentary"}:
        raise ValueError("Неизвестный тип публикации")
    speaker = str(post.get("speaker", "")).strip()
    if kind == "commentary" and speaker not in {"ivan-vyatkin", "nikita-filatov"}:
        raise ValueError("Для комментария обязателен известный speaker")
    return {"title": title, "body": body, "source_url": source, "source_name": name,
            "kind": kind, "speaker": speaker}

def message(post):
    output = (f"<b>{html.escape(post['title'])}</b>\n\n"
              f"{html.escape(post['body'])}\n\n"
              f"Ссылка на источник: <a href=\"{html.escape(post['source_url'], quote=True)}\">"
              f"{html.escape(post['source_name'])}</a>")
    if len(output) > 4096:
        raise ValueError("Превышен лимит сообщения Telegram")
    return output

def send_telegram(token, text):
    # Токен содержится в URL, поэтому не выводим URL/объект исключения в лог.
    request = urllib.request.Request(
        f"https://api.telegram.org/bot{token}/sendMessage",
        data=json.dumps({"chat_id": "@footportal2", "text": text, "parse_mode": "HTML",
                         "link_preview_options": {"is_disabled": True}}).encode("utf-8"),
        headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=30) as resp:
            result = json.load(resp)
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"Telegram HTTP {exc.code}: проверьте права и секрет") from None
    except urllib.error.URLError:
        raise RuntimeError("Telegram временно недоступен") from None
    if not result.get("ok"):
        raise RuntimeError("Telegram не подтвердил отправку")

def run(dry_run=False):
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    if not dry_run and not token:
        raise RuntimeError("Не настроен TELEGRAM_BOT_TOKEN в Secrets GitHub")
    state = load_state()
    sent_files = set(state["sent_files"])
    sent_urls = set(state["sent_urls"])
    sent_commentary_keys = set(state.get("sent_commentary_keys", []))
    posted = skipped = errors = 0
    for file in sorted(QUEUE_DIR.glob("*.json")):
        rel = file.relative_to(ROOT).as_posix()
        if rel in sent_files:
            continue
        try:
            post = validate(json.loads(file.read_text(encoding="utf-8")))
            key = url_key(post["source_url"])
            is_commentary = post["kind"] == "commentary"
            comment_key = f"{post['speaker']}::{key}"
            # У отдельных комментариев свой реестр: одно и то же реальное
            # событие может стать новостью и получить реакции двух героев.
            duplicate = (comment_key in sent_commentary_keys if is_commentary
                         else key in sent_urls)
            if duplicate:
                state["sent_files"].append(rel)
                sent_files.add(rel)
                if not dry_run:
                    save_state(state)
                skipped += 1
                continue
            text = message(post)
            if dry_run:
                print(f"ПРОВЕРКА: {file.name}: {post['title']} ({len(text)} символов)")
            else:
                send_telegram(token, text)
                state["sent_files"].append(rel)
                sent_files.add(rel)
                if is_commentary:
                    state.setdefault("sent_commentary_keys", []).append(comment_key)
                    sent_commentary_keys.add(comment_key)
                else:
                    state["sent_urls"].append(key)
                    sent_urls.add(key)
                save_state(state)
                print("Отправлено:", post["title"])
            posted += 1
        except (ValueError, KeyError, json.JSONDecodeError) as exc:
            errors += 1
            print(f"Некорректный файл {file.name}: {exc}", file=sys.stderr)
        except RuntimeError as exc:
            errors += 1
            print(f"Ошибка отправки {file.name}: {exc}", file=sys.stderr)
            break
    print(f"Всего: {posted} обработано; {skipped} повторов; {errors} ошибок")
    return 1 if errors else 0

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="Ничего не отправлять")
    args = parser.parse_args()
    raise SystemExit(run(args.dry_run))
