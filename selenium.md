[Home Page](README.md) · [Vuln-Bank Installation](vuln-bank-install.md) · [F5 XC Configuration](xc-config.md) · [Traffic Generator Setup](traffic-generator.md)

---

# Hardened Selenium Traffic Simulation — Login Flow

This guide walks through setting up a hardened Selenium script that simulates realistic human login traffic to the `POST /login` endpoint on the vuln-bank application.

**Why hardened?** Default Selenium is easily detected by bot signature engines (F5 XC WAAP, Cloudflare, etc.) due to exposed automation flags. Hardening removes these signals to produce traffic that looks like a real browser user.

> This is useful for testing how traffic appears in F5 XC dashboards **without** Bot Defense enabled. With Bot Defense enabled, even hardened Selenium will be caught by JS telemetry analysis.

---

## Prerequisites

- Python 3.8+
- Chromium browser installed on your machine (works on both amd64 and arm64)
- pip3

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
pip3 install setuptools undetected-chromedriver selenium
```

> `setuptools` is required on Python 3.12+ — `distutils` was removed from the standard library and `undetected-chromedriver` depends on it.

| Package | Purpose |
|---|---|
| `undetected-chromedriver` | Auto-patches ChromeDriver to bypass bot signature detection |
| `selenium` | Browser automation framework |

**Step 4 — Install Chromium and ChromeDriver:**

Chromium works on both `amd64` and `arm64` — a single install command covers all architectures:

```bash
sudo apt update
sudo apt install chromium-browser chromium-driver -y
chromium-browser --version
```

> **Note:** Every time you open a new terminal session, re-activate the venv before running the script:
> ```bash
> source ~/selenium-env/bin/activate
> ```

---

## Section 2 — Hardening Techniques

Standard Selenium exposes several signals that bot detection engines look for. Here is what this script patches:

| Signal | Default Selenium | This Script |
|---|---|---|
| `navigator.webdriver` | `true` — instantly flags automation | Patched to `undefined` via CDP |
| User-Agent | Contains `HeadlessChrome` or automation strings | Randomized realistic browser UA |
| Automation flags | `--enable-automation` switch present | Removed via `undetected-chromedriver` |
| Browser fingerprint | Automation-typical | Patched by `undetected-chromedriver` |
| Interaction timing | Instant (robotic) | Random delays between keystrokes and actions |
| Login credentials | Fixed single user | Randomly rotates between `john` and `franklin` |

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
Starting 50 login simulations against https://vulnbank.yourdomain.com
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
| Source IP | Your machine's IP (rotated via XFF if behind proxy) |
| User-Agent | Randomized real browser UA |
| Bot signature | Unlikely to trigger (hardened driver) |
| Bot Defense telemetry | **Not present** (no SDK, no JS injection) |

In the F5 XC Console (`vuln-bank` namespace → Security Events), these requests will appear as normal authenticated traffic unless Bot Defense is enabled.

---

## References

- [undetected-chromedriver — GitHub](https://github.com/ultrafunkamsterdam/undetected-chromedriver)
- [Selenium Documentation](https://www.selenium.dev/documentation/)
- [F5 Bot Defense Documentation](https://docs.cloud.f5.com/docs-v2/bot-defense)
- [vuln-bank — GitHub](https://github.com/Commando-X/vuln-bank)

---

## Quick Links

[Home Page](README.md) · [Vuln-Bank Installation](vuln-bank-install.md) · [F5 XC Configuration](xc-config.md) · [Traffic Generator Setup](traffic-generator.md)
