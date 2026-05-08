"""
Hardened Selenium — vuln-bank Login Traffic Simulator
=======================================================
Simulates human-like login traffic to POST /login on the vuln-bank app.
Rotates between john and franklin credentials with randomized timing.

Uses Playwright with Chromium (ARM64-compatible, non-snap).

Run:
  python3 selenium-login.py
"""

import random
import time
import urllib.request
from playwright.sync_api import sync_playwright

# ── Config ────────────────────────────────────────────────────
TARGET_URL   = "https://vulnbank.mytechlab.my.id"
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


def get_public_ip():
    try:
        return urllib.request.urlopen("https://api.ipify.org").read().decode()
    except Exception:
        return "unavailable"


# ── Main simulation ───────────────────────────────────────────

def simulate_login(page, cred, iteration):
    print(f"[{iteration}] Logging in as: {cred['username']}")

    try:
        # Navigate to login page
        page.goto(f"{TARGET_URL}/login", wait_until="domcontentloaded")
        human_delay(2, 5)   # simulate page read time

        # Fill username — character by character
        username_field = page.locator("input[name='username']")
        username_field.click()
        human_delay(0.3, 0.8)
        for char in cred["username"]:
            page.keyboard.type(char)
            time.sleep(random.uniform(0.05, 0.2))

        human_delay(0.5, 1.5)

        # Fill password — character by character
        password_field = page.locator("input[name='password']")
        password_field.click()
        human_delay(0.3, 0.8)
        for char in cred["password"]:
            page.keyboard.type(char)
            time.sleep(random.uniform(0.05, 0.2))

        human_delay(0.5, 2.0)   # simulate user pausing before submitting

        # Click submit
        page.locator("button[type='submit']").click()
        human_delay(2, 4)   # wait for response / dashboard load

        print(f"[{iteration}] Current URL after login: {page.url}")

        human_delay(3, 8)   # simulate browsing after login

        # Logout if possible
        try:
            logout = page.locator("text=Logout, text=Sign out").first
            if logout.is_visible():
                logout.click()
                human_delay(1, 3)
        except Exception:
            pass   # no logout button found — continue

    except Exception as e:
        print(f"[{iteration}] Error: {e}")


def main():
    public_ip = get_public_ip()
    print(f"Public IP       : {public_ip}")
    print(f"Target          : {TARGET_URL}")
    print(f"Iterations      : {ITERATIONS}")
    print("─" * 60)

    with sync_playwright() as p:
        for i in range(1, ITERATIONS + 1):
            cred = random.choice(CREDENTIALS)
            ua   = random.choice(USER_AGENTS)

            # New browser instance per session — avoids session fingerprinting
            browser = p.chromium.launch(
                headless=True,
                args=[
                    "--no-sandbox",
                    "--disable-gpu",
                    "--disable-dev-shm-usage",
                    "--disable-blink-features=AutomationControlled",
                ],
            )

            context = browser.new_context(
                user_agent=ua,
                viewport={"width": 1366, "height": 768},
                locale="en-US",
                java_script_enabled=True,
            )

            # Patch navigator.webdriver to undefined
            context.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                });
            """)

            page = context.new_page()

            try:
                simulate_login(page, cred, i)
            finally:
                context.close()
                browser.close()

            wait_s = random.uniform(*WAIT_BETWEEN)
            print(f"[{i}] Waiting {wait_s:.1f}s before next session...")
            time.sleep(wait_s)

    print("─" * 60)
    print("Simulation complete.")


if __name__ == "__main__":
    main()
