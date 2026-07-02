# PESU Results Watchdog

An automated Playwright bot that logs into the PESU Academy portal, checks your ESA (End Semester Assessment) results, and texts you the moment they're published — so you don't have to keep refreshing the page yourself.

## What it does

- Launches Chromium and logs into [pesuacademy.com/Academy](https://www.pesuacademy.com/Academy/)
- Navigates to the Results page
- Reads the subject names and ESA grades for the semester(s) you specify
- Sends you an SMS (via a free phone-based webhook, no paid SMS API needed):
  - **"Results are not yet displayed"** — if grades are still pending
  - **"Congratulations your results are out!"** with the subject/grade list — once real grades appear
- When run with the scheduler, it checks in **every 2 hours** and notifies you each time — right up until your results are published, at which point it stops automatically. No manual babysitting required.

## Project structure

```
Agentic_workflow/
├── navigating_to_results_page.py   # Main automation script (login, scrape, SMS)
├── scheduler.py                    # Runs the main script repeatedly on a schedule
├── README.md                       # This file
└── .venv/                          # Python virtual environment (created during setup)
```

## Prerequisites

- macOS (these instructions are written for Mac Terminal / zsh)
- Python 3.10 or newer
- A Samsung/Android phone with the **MacroDroid** app (free) — used as your SMS gateway
- Your PESU Academy portal username and password

## Setup guide

### 1. Install Python dependencies

Open Terminal, navigate to the project folder, and run:

```bash
cd ~/Desktop/Agentic_workflow
python3 -m venv .venv
source .venv/bin/activate
pip3 install playwright requests
playwright install chromium
```

> **Tip:** any time you open a new terminal window to run these scripts, re-activate the environment first with `source .venv/bin/activate` — you'll see `(.venv)` appear at the start of your prompt when it's active.

### 2. Set your PESU credentials

The script reads credentials from environment variables (falls back to a hardcoded default if unset — check the top of `navigating_to_results_page.py` and update the `get_credentials()` function if you'd like to change the fallback values).

To set them per-session instead:

```bash
export PESU_USERNAME="your_srn"
export PESU_PASSWORD="your_password"
```

### 3. Set up MacroDroid on your phone (SMS gateway)

Since there's no built-in paid SMS API in this project, your own Android phone acts as the "SMS sender" via a webhook trigger.

1. Install **MacroDroid** from the Google Play Store
2. Create a new macro:
   - **Trigger:** Connectivity → Webhook (Web Request Received) — copy the generated URL
   - **Action:** Phone → Send SMS — set the recipient number, and map the message body to the incoming webhook's message key (use the variable picker, add a key named `message`, and insert it into the message field)
3. Make sure the macro is enabled, MacroDroid has SMS permission, and battery optimization is disabled for the app (Settings → Apps → MacroDroid → Battery → Unrestricted) so it keeps running in the background overnight

### 4. Point the script at your webhook

In `navigating_to_results_page.py`, set your real MacroDroid webhook URL:

```bash
export MACRODROID_WEBHOOK_URL="https://trigger.macrodroid.com/your-real-webhook-id/sms_trigger"
```

Test it works before relying on it:

```bash
curl "https://trigger.macrodroid.com/your-real-webhook-id/sms_trigger?message=Test123"
```

You should receive a text on your phone saying "Test123."

## Running it

### Run once, manually

```bash
source .venv/bin/activate
python3 navigating_to_results_page.py
```

A Chromium window will open, log in, check results, and send an SMS. The script exits automatically once it finds real grades, or after exhausting its retry attempts if the results page still isn't ready.

### Run automatically on a schedule (recommended for overnight monitoring)

The scheduler runs the main script repeatedly within a defined time window (e.g. every 2 hours from 4:30 PM today to 10:00 AM tomorrow), texting you an update at each check-in, and stops early the moment results are detected as published.

```bash
brew install tmux          # one-time install, if not already installed
tmux new -s pesu_scheduler
caffeinate -s python3 scheduler.py
```

Detach from the session (safe to close your terminal after this — it keeps running):

```
Ctrl+B, then D
```

Check on it anytime:

```bash
tmux attach -t pesu_scheduler
```

> `caffeinate -s` prevents your Mac from sleeping while the scheduler runs. Keep your laptop plugged in and the lid open overnight for this to work reliably.

To change the schedule window or interval, edit the `start`, `end`, and `INTERVAL_HOURS` values near the top of `scheduler.py`.

## Configuration reference

| Setting | Where | Purpose |
|---|---|---|
| `PESU_USERNAME` / `PESU_PASSWORD` | env vars or `get_credentials()` | Portal login |
| `MACRODROID_WEBHOOK_URL` | env var or top of script | Where SMS-trigger requests are sent |
| `semesters_to_check` | inside `run()` | Which semester(s) to check/report on |
| `max_retries` / `retry_delay_seconds` | inside `run()` | How hard a single run retries before giving up |
| `INTERVAL_HOURS` / `start` / `end` | `scheduler.py` | How often (every 2 hrs, by default) and how long the scheduler runs overnight |
| `RESULTS_READY_EXIT_CODE` | both files (must match) | Internal signal used to tell the scheduler to stop early |

## Troubleshooting

- **`ModuleNotFoundError`** — your virtual environment isn't activated, or the package isn't installed inside it. Run `source .venv/bin/activate` then `pip3 install .`
- **Login hangs / times out** — check the live browser window for a CAPTCHA; this can appear if you've attempted many logins in a short time. It must be solved manually.
- **`Locator.wait_for: Timeout exceeded`** — the page layout may have changed, or an unexpected popup is blocking the page. Check the saved screenshot files (e.g. `results_load_failed_attempt1.png`) in the project folder for a snapshot of what the page looked like at the moment of failure.
- **SMS never arrives** — retest your webhook URL directly with `curl` (see step 4 above). If that also fails, check the MacroDroid macro is enabled, has SMS permission, and isn't being killed by battery optimization.
- **Scheduler stops unexpectedly overnight** — make sure it's running inside `tmux` (not a plain terminal window) and that `caffeinate -s` is active, so your Mac sleeping or the terminal losing focus can't interrupt it.
- **The script seems to be taking a long time / isn't responding right away** — this usually just means the Results page wasn't reachable or fully loaded on the first try. The script automatically retries the whole navigate → check → SMS sequence (up to `max_retries` times, waiting `retry_delay_seconds` between each attempt — see the Configuration reference above) until it successfully reaches the results grade. This is expected behavior, not a crash — just let it keep running. If you'd like it to give up sooner (or try harder for longer), adjust `max_retries` and `retry_delay_seconds` inside `run()`.

## Notes on responsible use

Running many automated logins in a short window (e.g. every 2 minutes) significantly increases the chance of triggering the portal's CAPTCHA or rate-limiting protections. A 1–2 hour interval is a reasonable balance between responsiveness and not hammering the login system unnecessarily.
