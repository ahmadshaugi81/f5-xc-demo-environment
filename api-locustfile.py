"""
vuln-bank API Traffic Generator
=================================
Based on: https://vulnbank.mytechlab.my.id/api/docs/
Excludes: ai-agent, forgot/reset password, admin endpoints

Workflow 1 - PreLoginAPIUser  : Public/unauthenticated API flows (2 tasks)
Workflow 2 - PostLoginAPIUser : Authenticated API flows (8 tasks)

Each virtual user gets ONE random IP (X-Forwarded-For) and ONE random
User-Agent in on_start and keeps them for the whole session.

Run examples:
  locust -f api_locustfile.py --host=https://vulnbank.mytechlab.my.id --users 50 --spawn-rate 5
  locust -f api_locustfile.py --host=https://vulnbank.mytechlab.my.id --headless --users 50 --spawn-rate 5 --run-time 3d
"""

import random

from locust import HttpUser, between, task
from locust.exception import StopUser

# ──────────────────────────────────────────────────────────────
# Spoofed identity pools
# ──────────────────────────────────────────────────────────────

PUBLIC_IPS = [
    # North America
    "12.34.56.78",   "23.45.67.89",   "34.56.78.90",   "45.67.89.01",
    "56.78.90.12",   "67.89.01.23",   "98.12.34.56",   "104.23.45.67",
    "108.34.56.78",  "172.56.78.90",  "184.67.89.01",  "199.78.90.12",
    "204.89.01.23",  "209.90.12.34",  "216.01.23.45",  "24.12.34.56",
    "50.23.45.67",   "64.34.56.78",   "66.45.67.89",   "68.56.78.90",
    # Europe
    "2.67.89.01",    "5.78.90.12",    "31.89.01.23",   "37.90.12.34",
    "46.01.23.45",   "62.12.34.56",   "77.23.45.67",   "80.34.56.78",
    "82.45.67.89",   "83.56.78.90",   "84.67.89.01",   "85.78.90.12",
    "86.89.01.23",   "87.90.12.34",   "88.01.23.45",   "89.12.34.56",
    "90.23.45.67",   "91.34.56.78",   "92.45.67.89",   "93.56.78.90",
    "94.67.89.01",   "95.78.90.12",   "109.89.01.23",  "176.90.12.34",
    "178.01.23.45",  "188.12.34.56",  "194.23.45.67",  "195.34.56.78",
    "212.45.67.89",  "213.56.78.90",
    # Asia Pacific
    "1.67.89.01",    "14.78.90.12",   "27.89.01.23",   "36.90.12.34",
    "39.01.23.45",   "42.12.34.56",   "43.23.45.67",   "49.34.56.78",
    "58.45.67.89",   "59.56.78.90",   "60.67.89.01",   "61.78.90.12",
    "101.89.01.23",  "103.90.12.34",  "106.01.23.45",  "110.12.34.56",
    "111.23.45.67",  "112.34.56.78",  "113.45.67.89",  "114.56.78.90",
    "115.67.89.01",  "116.78.90.12",  "117.89.01.23",  "118.90.12.34",
    "119.01.23.45",  "120.12.34.56",  "121.23.45.67",  "122.34.56.78",
    "123.45.67.89",  "124.56.78.90",
    # South America
    "177.67.89.01",  "179.78.90.12",  "181.89.01.23",  "186.90.12.34",
    "187.01.23.45",  "189.12.34.56",  "190.23.45.67",  "191.34.56.78",
    "200.45.67.89",  "201.56.78.90",
    # Africa & Middle East
    "41.67.89.01",   "41.78.90.12",   "41.89.01.23",   "41.90.12.34",
    "105.01.23.45",  "105.12.34.56",  "197.23.45.67",  "196.34.56.78",
    "196.45.67.89",  "41.99.88.77",
]

USER_AGENTS = [
    # Chrome – Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    # Chrome – macOS
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_4) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    # Chrome – Linux
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    # Chrome – Android
    "Mozilla/5.0 (Linux; Android 13; Pixel 7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Mobile Safari/537.36",
    "Mozilla/5.0 (Linux; Android 12; Samsung Galaxy S22) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.6099.144 Mobile Safari/537.36",
    # Firefox – Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0",
    # Firefox – macOS
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14.4; rv:125.0) Gecko/20100101 Firefox/125.0",
    # Firefox – Linux
    "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:124.0) Gecko/20100101 Firefox/124.0",
    # Safari – macOS
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_4_1) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4.1 Safari/605.1.15",
    # Safari – iPhone
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Mobile/15E148 Safari/604.1",
    # Edge – Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36 Edg/124.0.0.0",
    # Opera – Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36 OPR/109.0.0.0",
]

def pick_identity() -> tuple:
    """Return a (ip, user_agent) pair for one virtual user session."""
    return random.choice(PUBLIC_IPS), random.choice(USER_AGENTS)


# ──────────────────────────────────────────────────────────────
# Workflow 1 – Pre-login API (public, no auth)
# ──────────────────────────────────────────────────────────────

class PreLoginAPIUser(HttpUser):
    """
    Simulates normal anonymous API traffic — public endpoints only.
    No auth, no exploitation. BOLA/attack simulation is a separate script.
    """

    wait_time = between(1, 3)

    def on_start(self):
        ip, ua = pick_identity()
        self.client.headers.update({
            "X-Forwarded-For":  ip,
            "User-Agent":       ua,
            "Content-Type":     "application/json",
            "Accept":           "application/json",
        })

    # ── 1. Bill Categories ────────────────────────────────────

    @task(3)
    def bill_categories(self):
        self.client.get(
            "/api/bill-categories",
            name="[Pre] Bill Categories",
        )

    # ── 2. Billers by Category ────────────────────────────────

    @task(2)
    def billers_by_category(self):
        res = self.client.get(
            "/api/bill-categories",
            name="[Pre] Bill Categories (for billers lookup)",
        )
        if res.status_code != 200:
            return
        cats = res.json().get("categories", [])
        if not cats:
            return
        cat_id = random.choice(cats).get("id")
        self.client.get(
            f"/api/billers/by-category/{cat_id}",
            name="[Pre] Billers by Category",
        )


# ──────────────────────────────────────────────────────────────
# Workflow 2 – Post-login API (authenticated)
# ──────────────────────────────────────────────────────────────

class PostLoginAPIUser(HttpUser):
    """
    Simulates authenticated API traffic.
    on_start logs in with one of two known credentials.
    """

    wait_time = between(1, 3)

    CREDENTIALS = [
        {"username": "shaugi",    "password": "123456"},
        {"username": "mytechlab", "password": "123456"},
    ]

    def on_start(self):
        self.token          = None
        self.account_number = None
        self.user_id        = None
        self.card_id        = None

        ip, ua = pick_identity()
        self.client.headers.update({
            "X-Forwarded-For":  ip,
            "User-Agent":       ua,
            "Content-Type":     "application/json",
            "Accept":           "application/json",
        })

        cred = random.choice(self.CREDENTIALS)
        self.username = cred["username"]

        res = self.client.post("/login", json=cred, name="[Setup] Login")
        if res.status_code != 200:
            raise StopUser()

        body = res.json()
        self.token          = body.get("token")
        self.account_number = body.get("accountNumber")
        self.user_id        = body.get("debug_info", {}).get("user_id")

        if not self.token:
            raise StopUser()

    def _auth(self) -> dict:
        """Return Authorization header. Content-Type already on session."""
        return {"Authorization": f"Bearer {self.token}"}

    # ── 1. User Profile ───────────────────────────────────────

    @task(3)
    def user_profile(self):
        if not self.user_id:
            return
        self.client.get(
            f"/api/v3/user/{self.user_id}",
            headers=self._auth(),
            name="[Post] User Profile",
        )

    # ── 2. Check Balance ──────────────────────────────────────

    @task(5)
    def check_balance(self):
        if not self.account_number:
            return
        self.client.get(
            f"/check_balance/{self.account_number}",
            headers=self._auth(),
            name="[Post] Check Balance",
        )

    # ── 3. Transfer Money ─────────────────────────────────────

    @task(2)
    def transfer_money(self):
        if not self.account_number:
            return

        # Check balance before transferring — skip if account is dry
        bal_res = self.client.get(
            f"/check_balance/{self.account_number}",
            headers=self._auth(),
            name="[Post] Transfer - Balance Check",
        )
        if bal_res.status_code != 200:
            return
        if float(bal_res.json().get("balance", 0)) < 0.01:
            return  # skip — avoid a doomed 400

        # Lookup recipient account number
        other_username = "mytechlab" if self.username == "shaugi" else "shaugi"
        res = self.client.post(
            "/login",
            json={"username": other_username, "password": "123456"},
            name="[Post] Transfer - Lookup Recipient",
            catch_response=True,
        )
        with res as r:
            to_account = (
                r.json().get("accountNumber", self.account_number)
                if r.status_code == 200
                else self.account_number
            )
            r.success()

        self.client.post(
            "/transfer",
            json={
                "to_account":  to_account,
                "amount":      0.01,
                "description": f"API load test {random.randint(1000, 9999)}",
            },
            headers=self._auth(),
            name="[Post] Transfer",
        )

    # ── 4. Transaction History ────────────────────────────────

    @task(3)
    def transaction_history(self):
        if not self.account_number:
            return
        self.client.get(
            f"/transactions/{self.account_number}",
            headers=self._auth(),
            name="[Post] Transaction History (legacy)",
        )
        self.client.get(
            f"/api/transactions?account_number={self.account_number}",
            headers=self._auth(),
            name="[Post] Transaction History (API)",
        )

    # ── 5. Request Loan ───────────────────────────────────────

    @task(1)
    def request_loan(self):
        self.client.post(
            "/request_loan",
            json={"amount": round(random.uniform(100.0, 2000.0), 2)},
            headers=self._auth(),
            name="[Post] Request Loan",
        )

    # ── 6. Virtual Cards ──────────────────────────────────────

    @task(2)
    def virtual_cards_flow(self):
        # Create
        res = self.client.post(
            "/api/virtual-cards/create",
            json={
                "card_limit": round(random.uniform(500.0, 3000.0), 2),
                "card_type":  random.choice(["standard", "premium"]),
                "currency":   random.choice(["USD", "EUR", "GBP"]),
            },
            headers=self._auth(),
            name="[Post] Virtual Cards - Create",
        )
        if res.status_code == 200:
            cid = res.json().get("card_details", {}).get("id")
            if cid:
                self.card_id = cid

        # List
        self.client.get(
            "/api/virtual-cards",
            headers=self._auth(),
            name="[Post] Virtual Cards - List",
        )

        if not self.card_id:
            return

        # Fund only if main balance is sufficient
        bal_res = self.client.get(
            f"/check_balance/{self.account_number}",
            headers=self._auth(),
            name="[Post] Virtual Cards - Balance Check",
        )
        if bal_res.status_code == 200 and float(bal_res.json().get("balance", 0)) >= 0.01:
            self.client.post(
                f"/api/virtual-cards/{self.card_id}/fund",
                json={"amount": 0.01},
                headers=self._auth(),
                name="[Post] Virtual Cards - Fund",
            )

        # Toggle freeze → unfreeze immediately
        for _ in range(2):
            self.client.post(
                f"/api/virtual-cards/{self.card_id}/toggle-freeze",
                headers=self._auth(),
                name="[Post] Virtual Cards - Toggle Freeze",
            )

        # Update limit
        self.client.post(
            f"/api/virtual-cards/{self.card_id}/update-limit",
            json={"card_limit": round(random.uniform(1000.0, 5000.0), 2)},
            headers=self._auth(),
            name="[Post] Virtual Cards - Update Limit",
        )

        # Card transactions
        self.client.get(
            f"/api/virtual-cards/{self.card_id}/transactions",
            headers=self._auth(),
            name="[Post] Virtual Cards - Transactions",
        )

    # ── 7. Bill Payment ───────────────────────────────────────

    @task(2)
    def bill_payment_flow(self):
        # Categories
        cats_res = self.client.get(
            "/api/bill-categories",
            headers=self._auth(),
            name="[Post] Bill Payment - Categories",
        )
        if cats_res.status_code != 200:
            return
        cats = cats_res.json().get("categories", [])
        if not cats:
            return

        # Billers
        cat_id = random.choice(cats).get("id")
        billers_res = self.client.get(
            f"/api/billers/by-category/{cat_id}",
            headers=self._auth(),
            name="[Post] Bill Payment - Billers",
        )
        if billers_res.status_code != 200:
            return
        billers = billers_res.json().get("billers", [])
        if not billers:
            return

        # Pick cheapest biller
        billers_sorted = sorted(billers, key=lambda b: float(b.get("minimum_amount") or 0))
        biller     = billers_sorted[0]
        biller_id  = biller.get("id")
        min_amount = float(biller.get("minimum_amount") or 1.0)

        # Check balance before paying
        bal_res = self.client.get(
            f"/check_balance/{self.account_number}",
            headers=self._auth(),
            name="[Post] Bill Payment - Balance Check",
        )
        if bal_res.status_code != 200:
            return
        if float(bal_res.json().get("balance", 0)) < min_amount:
            return  # skip — avoid a doomed 400

        # Pay
        self.client.post(
            "/api/bill-payments/create",
            json={
                "biller_id":      biller_id,
                "amount":         min_amount,
                "payment_method": "balance",
                "description":    "API load test bill payment",
            },
            headers=self._auth(),
            name="[Post] Bill Payment - Create",
        )

        # History
        self.client.get(
            "/api/bill-payments/history",
            headers=self._auth(),
            name="[Post] Bill Payment - History",
        )

    # ── 8. Upload Profile Picture by URL ──────────────────────

    @task(1)
    def upload_profile_picture_url(self):
        # Use a publicly accessible small image URL
        sample_images = [
            "https://www.gravatar.com/avatar/00000000000000000000000000000000?d=mp&s=200",
            "https://picsum.photos/seed/locust1/200",
            "https://picsum.photos/seed/locust2/200",
            "https://picsum.photos/seed/locust3/200",
        ]
        self.client.post(
            "/upload_profile_picture_url",
            json={"image_url": random.choice(sample_images)},
            headers=self._auth(),
            name="[Post] Upload Profile Pic URL",
        )