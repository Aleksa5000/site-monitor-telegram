"""Website monitor: uptime, content-change and keyword checks with Telegram alerts."""
import json
import os
import sys
import time
from pathlib import Path

import requests
import yaml
from bs4 import BeautifulSoup

HEADERS = {"User-Agent": "site-monitor-telegram/1.0 (+https://github.com/Aleksa5000/site-monitor-telegram)"}
STATE_FILE = Path(os.environ.get("STATE_FILE", "state.json"))
CONFIG_FILE = Path(os.environ.get("MONITORS_FILE", "monitors.yaml"))


def fetch(url, timeout=15):
    """Return (response, elapsed_ms). Raises requests exceptions on network failure."""
    start = time.monotonic()
    resp = requests.get(url, headers=HEADERS, timeout=timeout)
    return resp, (time.monotonic() - start) * 1000


def check(monitor, prev):
    """Run one check. Returns (new_state, alert_message_or_None). Only changes alert."""
    name, url, kind = monitor["name"], monitor["url"], monitor["type"]
    if kind not in ("uptime", "content", "keyword"):
        raise ValueError(f"{name}: unknown type '{kind}'")
    prev = prev or {}
    try:
        resp, ms = fetch(url, monitor.get("timeout", 15))
        problem = None
        if resp.status_code >= 400:
            problem = f"HTTP {resp.status_code}"
        elif ms > monitor.get("max_response_ms", 3000):
            problem = f"slow response ({ms:.0f} ms)"
    except requests.RequestException as exc:
        resp, problem = None, f"request failed ({type(exc).__name__})"

    # Down / recovered transitions apply to every check type.
    if problem:
        msg = f"\U0001F534 {name} is DOWN: {problem}\n{url}" if prev.get("status") != "down" else None
        return {**prev, "status": "down"}, msg
    new = {**prev, "status": "up"}
    msg = f"\U0001F7E2 {name} is back UP\n{url}" if prev.get("status") == "down" else None
    if kind == "uptime":
        return new, msg

    soup = BeautifulSoup(resp.content, "html.parser")
    old = prev.get("value")
    if kind == "content":
        el = soup.select_one(monitor["selector"])
        new["value"] = el.get_text(" ", strip=True) if el else "(selector not found)"
        if old is not None and old != new["value"]:
            msg = f"\U0001F514 {name} changed\nwas: {old}\nnow: {new['value']}\n{url}"
    else:  # keyword
        word = monitor["keyword"]
        new["value"] = "present" if word.lower() in soup.get_text(" ").lower() else "absent"
        if old is not None and old != new["value"]:
            msg = f"\U0001F514 {name}: keyword '{word}' is now {new['value'].upper()}\n{url}"
    return new, msg


def send(text):
    """Send via Telegram if configured, otherwise print (dry-run)."""
    token, chat = os.environ.get("TELEGRAM_BOT_TOKEN"), os.environ.get("TELEGRAM_CHAT_ID")
    if not (token and chat):
        print(f"[dry-run] {text}\n")
        return
    r = requests.post(
        f"https://api.telegram.org/bot{token}/sendMessage",
        json={"chat_id": chat, "text": text, "disable_web_page_preview": True},
        timeout=15,
    )
    r.raise_for_status()


def main():
    monitors = yaml.safe_load(CONFIG_FILE.read_text(encoding="utf-8"))["monitors"]
    state = json.loads(STATE_FILE.read_text(encoding="utf-8")) if STATE_FILE.exists() else {}
    for m in monitors:
        state[m["name"]], msg = check(m, state.get(m["name"]))
        print(f"{m['name']}: {state[m['name']]['status']}")
        if msg:
            send(msg)
    STATE_FILE.write_text(json.dumps(state, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


if __name__ == "__main__":
    sys.exit(main())
