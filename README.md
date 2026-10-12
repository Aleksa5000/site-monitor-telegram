# site-monitor-telegram

[![CI](https://github.com/Aleksa5000/site-monitor-telegram/actions/workflows/ci.yml/badge.svg)](https://github.com/Aleksa5000/site-monitor-telegram/actions/workflows/ci.yml)

**Get a Telegram message when your website goes down, a price changes, or a "sold out" label appears. It runs for free on GitHub Actions, with no server to maintain.**

## The problem it solves

Most businesses find out their site is down from a customer. Shops and resellers lose sales because a competitor's price or a supplier's stock status changed hours earlier and nobody noticed. Paid monitoring tools charge per check and are hard to bend to a specific page element.

This project checks the pages you care about every 30 minutes and alerts you **only when something changes**. It sends one message when a site goes down and one when it recovers, instead of a message every 30 minutes.

## Features

- **Three check types**
  - `uptime`: HTTP status code plus a response-time threshold.
  - `content`: watches the text of a CSS selector (price, stock label, headline) and reports old vs. new value.
  - `keyword`: alerts when a word appears on or disappears from a page.
- **Change-only alerts.** Last status and value are stored in `state.json`, so you are not spammed.
- **Telegram alerts** through the Bot API. Without credentials it prints alerts to the console (dry-run).
- **Free scheduling** with GitHub Actions cron (every 30 minutes). The workflow commits `state.json` back to the repo.
- **Configured in one YAML file**, so adding a site is a three-line change.
- Small, readable code (one ~80 line module) with offline tests.

## Example output

A real dry-run. The first run records a baseline. For the second run I changed the saved state by hand to simulate "example.com was down" and "the price used to be £49.99":

```text
$ python monitor.py            # run 2, no Telegram credentials set
Example.com uptime: up
[dry-run] 🟢 Example.com uptime is back UP
https://example.com

Book price (A Light in the Attic): up
[dry-run] 🔔 Book price (A Light in the Attic) changed
was: £49.99
now: £51.77
https://books.toscrape.com/catalogue/a-light-in-the-attic_1000/index.html

Example domain keyword: up
```

An unchanged third run prints only the three status lines and sends nothing.

## Quickstart

### Create a Telegram bot

1. In Telegram, open **@BotFather**, send `/newbot` and follow the prompts. Copy the **bot token**.
2. Open a chat with your new bot and send it any message (a bot cannot message you first).
3. Open `https://api.telegram.org/bot<TOKEN>/getUpdates` in a browser and find `"chat":{"id":123456789,...}`. That number is your **chat id**. (For a group, add the bot to the group and send a message there. The id is negative.)

### Run locally

```bash
pip install -r requirements.txt
python monitor.py                       # dry-run: alerts print to the console

export TELEGRAM_BOT_TOKEN=123:ABC       # Windows PowerShell: $env:TELEGRAM_BOT_TOKEN="123:ABC"
export TELEGRAM_CHAT_ID=123456789
python monitor.py                       # now alerts go to Telegram
```

`.env.example` lists the two variables. The script reads real environment variables, so export them or load the file with your shell.

### Run on GitHub Actions (free, no server)

1. Fork or push this repo to your GitHub account.
2. **Settings > Secrets and variables > Actions > New repository secret**: add `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID`.
3. **Settings > Actions > General > Workflow permissions**: allow read and write (the workflow also declares `contents: write`).
4. Edit `monitors.yaml`, then run **Actions > Monitor > Run workflow** once. After that it runs every 30 minutes.

GitHub's cron can be delayed a few minutes under load, and scheduled workflows are paused after 60 days without repo activity. The state commits count as activity.

## Configuration reference (`monitors.yaml`)

```yaml
monitors:
  - name: Example.com uptime        # unique label, also the state key
    url: https://example.com
    type: uptime
    max_response_ms: 3000           # optional, default 3000

  - name: Book price
    url: https://books.toscrape.com/catalogue/a-light-in-the-attic_1000/index.html
    type: content
    selector: "p.price_color"       # CSS selector, alert when its text changes

  - name: Out of stock watcher
    url: https://example.com
    type: keyword
    keyword: "Example Domain"       # case-insensitive, alert on appear/disappear
```

| Field | Types | Description |
|---|---|---|
| `name` | all | Unique name. Renaming a check resets its baseline. |
| `url` | all | Page to fetch. |
| `type` | all | `uptime`, `content` or `keyword`. |
| `max_response_ms` | all | Slower than this counts as down. Default `3000`. |
| `timeout` | all | Request timeout in seconds. Default `15`. |
| `selector` | content | CSS selector of the element to watch. |
| `keyword` | keyword | Text to look for (case-insensitive). |

Behaviour notes:

- The first run of a `content` or `keyword` check records a baseline and does not alert.
- HTTP status 400 or above, a timeout, a connection error or a slow response all count as **down**. Every check type reports down and recovered.
- If a selector matches nothing, the value becomes `(selector not found)`, so a redesign that breaks the selector is also reported.
- Pages that build their content with JavaScript are not supported (plain HTTP fetch only).

## Running tests

```bash
python -m pip install -r requirements.txt pytest
python -m pytest -q
```

The tests use no network. HTTP calls are mocked and cover down/up transitions (one alert each), content changes, keyword appear/disappear, and Telegram vs. dry-run sending.

## Tech stack

Python 3.11+, `requests`, `beautifulsoup4`, `pyyaml`, GitHub Actions, pytest.

## Need something similar?

Need a custom monitor, scraper or automation? **Contact me on Upwork** (Aleksa Djorovic, Python automation).

## License

MIT. See [LICENSE](LICENSE).
