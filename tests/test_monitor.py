import sys
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import monitor  # noqa: E402


class Resp:
    def __init__(self, status=200, text=""):
        self.status_code, self.content = status, text.encode()


def fake_fetch(monkeypatch, resp, ms=100):
    def f(url, timeout=15):
        if isinstance(resp, Exception):
            raise resp
        return resp, ms

    monkeypatch.setattr(monitor, "fetch", f)


UPTIME = {"name": "site", "url": "http://x", "type": "uptime"}


def test_uptime_down_then_up_alerts_once_each(monkeypatch):
    fake_fetch(monkeypatch, Resp(500))
    state, msg = monitor.check(UPTIME, None)
    assert "DOWN" in msg
    state, msg = monitor.check(UPTIME, state)  # still down: silent
    assert msg is None
    fake_fetch(monkeypatch, Resp(200))
    state, msg = monitor.check(UPTIME, state)
    assert "back UP" in msg
    state, msg = monitor.check(UPTIME, state)
    assert msg is None


def test_uptime_network_error_and_slow(monkeypatch):
    fake_fetch(monkeypatch, requests.ConnectionError())
    assert "DOWN" in monitor.check(UPTIME, None)[1]
    fake_fetch(monkeypatch, Resp(200), ms=9000)
    assert "slow" in monitor.check(UPTIME, None)[1]


CONTENT = {"name": "price", "url": "http://x", "type": "content", "selector": "p.price"}


def test_content_change_detection(monkeypatch):
    fake_fetch(monkeypatch, Resp(text='<p class="price">$10</p>'))
    state, msg = monitor.check(CONTENT, None)
    assert msg is None and state["value"] == "$10"  # baseline, no alert
    state, msg = monitor.check(CONTENT, state)
    assert msg is None  # unchanged
    fake_fetch(monkeypatch, Resp(text='<p class="price">$12</p>'))
    state, msg = monitor.check(CONTENT, state)
    assert "$10" in msg and "$12" in msg


KEYWORD = {"name": "stock", "url": "http://x", "type": "keyword", "keyword": "out of stock"}


def test_keyword_appears_and_disappears(monkeypatch):
    fake_fetch(monkeypatch, Resp(text="<p>In stock</p>"))
    state, msg = monitor.check(KEYWORD, None)
    assert msg is None and state["value"] == "absent"
    fake_fetch(monkeypatch, Resp(text="<p>Sorry, OUT OF STOCK</p>"))
    state, msg = monitor.check(KEYWORD, state)
    assert "PRESENT" in msg
    fake_fetch(monkeypatch, Resp(text="<p>Back</p>"))
    assert "ABSENT" in monitor.check(KEYWORD, state)[1]


def test_send_dry_run(monkeypatch, capsys):
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    monkeypatch.delenv("TELEGRAM_CHAT_ID", raising=False)

    def boom(*a, **k):
        raise AssertionError("no network in dry-run")

    monkeypatch.setattr(monitor.requests, "post", boom)
    monitor.send("hello")
    assert "[dry-run] hello" in capsys.readouterr().out


def test_send_telegram(monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "TOK")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "42")
    calls = []

    class R:
        def raise_for_status(self):
            pass

    monkeypatch.setattr(monitor.requests, "post", lambda url, **k: calls.append((url, k)) or R())
    monitor.send("hi")
    url, kw = calls[0]
    assert url == "https://api.telegram.org/botTOK/sendMessage"
    assert kw["json"] == {"chat_id": "42", "text": "hi", "disable_web_page_preview": True}
