"""
Hardened Selenium — vuln-bank Login Traffic Simulator
=======================================================
Simulates human-like login traffic to POST /login on the vuln-bank app.
Rotates between john and franklin credentials with randomized timing.

Run:
  python3 selenium-login.py
"""

import os
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
    """Build a hardened undetected Chromium driver instance."""
    ua = random.choice(USER_AGENTS)

    options = uc.ChromeOptions()
    options.add_argument(f"--user-agent={ua}")
    options.add_argument("--window-size=1366,768")
    options.add_argument("--disable-notifications")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-gpu")
    options.add_argument("--headless=new")

    driver = uc.Chrome(
        options=options,
        browser_executable_path="/usr/bin/chromium-browser",
        driver_executable_path=os.path.expanduser("~/selenium-env/bin/chromedriver"),
    )

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