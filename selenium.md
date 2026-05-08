[Home Page](README.md) · [Vuln-Bank Installation](vuln-bank-install.md) · [F5 XC Configuration](xc-config.md) · [Traffic Generator Setup](traffic-generator.md)

---

# Hardened Browser Traffic Simulation — Login Flow

This guide walks through setting up a hardened Playwright script that simulates realistic human login traffic to the `POST /login` endpoint on the vuln-bank application.

**Why hardened?** Default browser automation tools are easily detected by bot signature engines (F5 XC WAAP, Cloudflare, etc.) due to exposed automation flags. Hardening removes these signals to produce traffic that looks like a real browser user.

> This is useful for testing how traffic appears in F5 XC dashboards **without** Bot Defense enabled. With Bot Defense enabled, even hardened browser automation will be caught by JS telemetry analysis.

---

## Prerequisites

- Python 3.8+
- pip3

> No need to install Chrome or Chromium manually — Playwright downloads its own browser binary automatically, with native support for both `amd64` and `arm64`.

---

## Section 1 — Installation

**Step 1 — Install Python venv support (if not already installed):**

```bash
sudo apt install python3-full python3-venv -y
```

**Step 2 — Create and activate a virtual environment:**

```bash
python3 -m venv ~/selenium-env
source ~/selenium-env/bin/activate
```

> Your prompt will change to `(selenium-env)` confirming the venv is active. All packages installed from here go into the venv, not the system Python.

**Step 3 — Install dependencies:**

```bash
pip3 install playwright
```

| Package | Purpose |
|---|---|
| `playwright` | Browser automation framework with built-in stealth and ARM64-compatible Chromium |

**Step 4 — Download Playwright's Chromium:**

```bash
playwright install chromium
```

This downloads a Playwright-managed Chromium binary — no snap conflicts, no architecture issues.

> **Note:** Every time you open a new terminal session, re-activate the venv before running the script:
> ```bash
> source ~/selenium-env/bin/activate
> ```

---

## Section 2 — Hardening Techniques

Standard browser automation exposes several signals that bot detection engines look for. Here is what this script patches:

| Signal | Default | This Script |
|---|---|---|
| `navigator.webdriver` | `true` — instantly flags automation | Patched to `undefined` via `add_init_script` |
| User-Agent | Contains automation strings | Randomized realistic browser UA per session |
| Automation flags | `--enable-automation` present | Removed via `--disable-blink-features=AutomationControlled` |
| Interaction timing | Instant (robotic) | Random delays between keystrokes and actions |
| Login credentials | Fixed single user | Randomly rotates between `john` and `franklin` |
| Browser session | Persistent (trackable) | New browser context per session |

---

## Section 3 — The Script

The script is included in this repo as [`selenium-login.py`](selenium-login.py). After cloning or pulling the repo, the file is already available — no manual copy needed.

---

## Section 4 — Configure and Run

**Step 1 — Set your target URL:**

Open `selenium-login.py` and update the `TARGET_URL` variable at the top of the config section:

```python
TARGET_URL = "https://vulnbank.yourdomain.com"
```

**Step 2 — Adjust iteration count and timing (optional):**

```python
ITERATIONS   = 50          # total number of login sessions to run
WAIT_BETWEEN = (5, 15)     # seconds between each session
```

**Step 3 — Run the script:**

```bash
python3 selenium-login.py
```

You should see output like:

```
Public IP       : 54.x.x.x
Target          : https://vulnbank.yourdomain.com
Iterations      : 50
────────────────────────────────────────────────────────────
[1] Logging in as: franklin
[1] Current URL after login: https://vulnbank.yourdomain.com/dashboard
[1] Waiting 8.3s before next session...
[2] Logging in as: john
...
```

**Step 4 — Run in the background (optional):**

```bash
nohup python3 selenium-login.py > selenium.log 2>&1 &
```

Monitor:

```bash
tail -f selenium.log
```

---

## What This Generates in F5 XC

Each login session produces:

| Signal | Value |
|---|---|
| Method | `POST /login` |
| Source IP | Your machine's public IP |
| User-Agent | Randomized real browser UA per session |
| Bot signature | Unlikely to trigger (hardened browser) |
| Bot Defense telemetry | **Not present** (no SDK, no JS injection) |

In the F5 XC Console (`vuln-bank` namespace → Security Events), these requests will appear as normal authenticated traffic unless Bot Defense is enabled.

---

## References

- [Playwright Documentation](https://playwright.dev/python/docs/intro)
- [Playwright — Chromium](https://playwright.dev/docs/browsers)
- [F5 Bot Defense Documentation](https://docs.cloud.f5.com/docs-v2/bot-defense)
- [vuln-bank — GitHub](https://github.com/Commando-X/vuln-bank)

---

## Quick Links

[Home Page](README.md) · [Vuln-Bank Installation](vuln-bank-install.md) · [F5 XC Configuration](xc-config.md) · [Traffic Generator Setup](traffic-generator.md)
