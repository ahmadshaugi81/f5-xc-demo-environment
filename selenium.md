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
pip3 install undetected-chromedriver selenium
```

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

Create a file named `selenium-login.py` and paste the following:

```python
"""
Hardened Selenium — vuln-bank Login Traffic Simulator
=======================================================
Simulates human-like login traffic to POST /login on the vuln-bank app.
Rotates between john and franklin credentials with randomized timing.

Run:
  python3 selenium-login.py
"""

import random
import time
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# ── Config ────────────────────────────────────────────────────
TARGET_URL   = "https://YOUR_VULNBANK_DOMAIN"   # e.g. https://vulnbank.yourdomain.com
ITERATIONS   = 50                               # number of login attempts to simulate
WAIT_BETWEEN = (5, 15)                          # seconds between each login session

CREDENTIALS = [
    {"username": "john",     "password": "123456"},
    {"username": "franklin", "password": "123456"},
]

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_4_1) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4.1 Safari/605.1.15",
]

# ── Helpers ───────────────────────────────────────────────────

def human_delay(min_s=0.5, max_s=2.0):
    """Pause for a random human-like duration."""
    time.sleep(random.uniform(min_s, max_s))


def type_like_human(element, text):
    """Type text character by character with random keystroke delays."""
    for char in text:
        element.send_keys(char)
        time.sleep(random.uniform(0.05, 0.2))


def build_driver():
    """Build a hardened undetected Chrome driver instance."""
    ua = random.choice(USER_AGENTS)

    options = uc.ChromeOptions()
    options.add_argument(f"--user-agent={ua}")
    options.add_argument("--window-size=1366,768")
    options.add_argument("--disable-notifications")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-gpu")

    driver = uc.Chrome(options=options)

    # Patch navigator.webdriver to undefined via CDP
    driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
        "source": """
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
        """
    })

    return driver


# ── Main loop ─────────────────────────────────────────────────

def simulate_login(driver, cred, iteration):
    print(f"[{iteration}] Logging in as: {cred['username']}")

    try:
        # Navigate to login page
        driver.get(f"{TARGET_URL}/login")
        human_delay(2, 5)   # simulate page read time

        wait = WebDriverWait(driver, 10)

        # Fill username
        username_field = wait.until(
            EC.presence_of_element_located((By.NAME, "username"))
        )
        human_delay(0.5, 1.5)
        type_like_human(username_field, cred["username"])

        human_delay(0.5, 1.5)

        # Fill password
        password_field = driver.find_element(By.NAME, "password")
        type_like_human(password_field, cred["password"])

        human_delay(0.5, 2.0)   # simulate user pausing before submitting

        # Click submit
        submit_btn = driver.find_element(By.XPATH, "//button[@type='submit']")
        submit_btn.click()

        human_delay(2, 4)   # wait for response / dashboard load

        print(f"[{iteration}] Current URL after login: {driver.current_url}")

        # Optional: navigate to dashboard briefly before logging out
        human_delay(3, 8)

        # Logout if possible
        try:
            logout = driver.find_element(By.XPATH, "//*[contains(text(),'Logout') or contains(text(),'Sign out')]")
            logout.click()
            human_delay(1, 3)
        except Exception:
            pass   # no logout button found — continue

    except Exception as e:
        print(f"[{iteration}] Error: {e}")


def main():
    print(f"Starting {ITERATIONS} login simulations against {TARGET_URL}")
    print("─" * 60)

    for i in range(1, ITERATIONS + 1):
        cred   = random.choice(CREDENTIALS)
        driver = build_driver()

        try:
            simulate_login(driver, cred, i)
        finally:
            driver.quit()

        # Wait between sessions — new driver instance each time
        wait_s = random.uniform(*WAIT_BETWEEN)
        print(f"[{i}] Waiting {wait_s:.1f}s before next session...")
        time.sleep(wait_s)

    print("─" * 60)
    print("Simulation complete.")


if __name__ == "__main__":
    main()
```

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
