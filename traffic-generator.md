[Home Page](README.md) · [Vuln-Bank Installation](vuln-bank-install.md) · [F5 XC Configuration](xc-config.md)

---

# Traffic Generator

## Overview

The traffic generator produces continuous, realistic traffic through the F5 XC load balancer endpoint. Without traffic, the XC dashboards stay empty — no security events, no bot signals, no API discovery data. The traffic generator is what makes the demo environment come alive.

This repo includes two Locust scripts, each serving a distinct purpose:

### `locust-legitimate.py` — Normal User Traffic

Simulates realistic banking activity from authenticated and unauthenticated users. This generates the baseline traffic that populates API Discovery, drives Bot Defense telemetry, and shows normal request patterns in the XC dashboards.

Flows covered:
- Anonymous browsing: landing pages, info pages, Swagger docs, debug endpoint, bill categories
- Authenticated banking: login, check balance, transfer money, transaction history, request loan, virtual card management, bill payments, GraphQL queries, profile picture upload

### `locust-attack.py` — Attack Traffic

Simulates malicious traffic to trigger WAF blocks, API threat detections, and security events in the XC Console. Runs two user classes in parallel:

**Unauthenticated attacks (public endpoints):**
| Attack | Description |
|---|---|
| SQL Injection | Payloads in `POST /login` body and GET query parameters across multiple endpoints |
| Cross-Site Scripting (XSS) | Injected into query params on `/login`, `/api/docs`, `/blog` |
| Path Traversal / LFI | `../../../../etc/passwd` variants on `/transactions/`, `/check_balance/`, `/api/docs` |
| Command Injection / RCE | Shell payloads (`;whoami`, `$(id)`) on debug and lookup endpoints |
| Prototype Pollution | `__proto__` and `constructor.prototype` injected into `/login` body |

**Authenticated attacks (logged in as john or franklin):**
| Attack | Description |
|---|---|
| BOLA | Uses own JWT to access the other user's balance, transactions, profile, and virtual cards |
| BOLA — Forced Transfer | Attempts to transfer funds from the other user's account to own account |
| BOPLA | Injects privilege-escalation fields (`is_admin`, `approved`, `bypass_limit`, `role: admin`) into transfer, loan, card creation, and bill payment requests |
| SQLi (authenticated) | Payloads injected into authenticated GET params and POST bodies |
| XSS (authenticated) | Injected into `description`, `card_type`, and `image_url` fields on POST endpoints |
| Path Traversal (authenticated) | LFI payloads on authenticated GET endpoints |
| Command Injection (authenticated) | Shell payloads in `image_url` and `description` POST fields |
| Prototype Pollution (authenticated) | `__proto__` fields merged into virtual card, transfer, and bill payment bodies |
| GraphQL Injection | Schema introspection, type enumeration, and destructive mutation attempts |

---

## Getting the Files

Clone or pull this repo directly on your traffic generator server — no need to manually copy scripts:

```bash
# First time
git clone https://github.com/ahmadshaugi81/f5-xc-demo-environment.git
cd f5-xc-demo-environment

# Already cloned — pull latest
git pull
```

Both `locust-legitimate.py` and `locust-attack.py` will be available in the repo root.

---

## Section 1 — Install Locust

```bash
sudo apt update && sudo apt install -y python3 python3-pip
pip3 install locust
```

Verify the install:

```bash
locust --version
```

---

## Section 2 — Set Up Log Rotation

Set this up **before** running Locust, so log rotation is already watching from the moment the log files are created.

**Step 1 — Create the logrotate config:**

```bash
sudo nano /etc/logrotate.d/locust
```

Paste the following (update the paths to match your home directory and where the log files will be written):

```
/home/youruser/locust-legitimate.log {
    size 100M
    rotate 3
    compress
    missingok
    notifempty
    copytruncate
}

/home/youruser/locust-attack.log {
    size 100M
    rotate 3
    compress
    missingok
    notifempty
    copytruncate
}
```

**Step 2 — Test the config:**

```bash
sudo logrotate -d /etc/logrotate.d/locust
```

This runs a dry-run — no actual rotation happens, just confirms there are no syntax errors.

`logrotate` runs automatically via cron every day. With `100M` per file and 3 rotations, each script uses up to 300 MB max before old logs are deleted — safe for multi-day runs.

---

## Section 3 — Run Locust in the Background

Replace `https://vulnbank.yourdomain.com` with your actual load balancer URL before running.

### `locust-legitimate.py` — Legitimate Traffic

**Option 1 — Run for 240 hours:**

```bash
nohup locust -f locust-legitimate.py \
  --host=https://vulnbank.yourdomain.com \
  --headless --users 50 --spawn-rate 5 --run-time 240h \
  > locust-legitimate.log 2>&1 &
```

**Option 2 — Run until manually stopped:**

```bash
nohup locust -f locust-legitimate.py \
  --host=https://vulnbank.yourdomain.com \
  --headless --users 50 --spawn-rate 5 \
  > locust-legitimate.log 2>&1 &
```

---

### `locust-attack.py` — Attack Traffic

**Option 1 — Run for 240 hours:**

```bash
nohup locust -f locust-attack.py \
  --host=https://vulnbank.yourdomain.com \
  --headless --users 50 --spawn-rate 5 --run-time 240h \
  > locust-attack.log 2>&1 &
```

**Option 2 — Run until manually stopped:**

```bash
nohup locust -f locust-attack.py \
  --host=https://vulnbank.yourdomain.com \
  --headless --users 50 --spawn-rate 5 \
  > locust-attack.log 2>&1 &
```

> Both scripts can run simultaneously on the same server. Each runs as a separate background process with its own log file.

---

## Section 4 — Monitor and Stop

### Check that Locust is running

```bash
ps aux | grep locust
```

You should see one process per script. Each line shows the PID (second column) and the full command.

To stream the live log output:

```bash
tail -f locust-legitimate.log
tail -f locust-attack.log
```

### Stop a Locust process

Find the PID from `ps aux | grep locust`, then:

```bash
kill <PID>
```

If the process does not stop (hung or unresponsive), force it:

```bash
kill -9 <PID>
```

To stop all running Locust processes at once:

```bash
pkill -f locust
```

**Quick reference:**

| Command | What it does |
|---|---|
| `kill <PID>` | Graceful termination (SIGTERM) |
| `kill -9 <PID>` | Force kill — cannot be ignored (SIGKILL) |
| `pkill -f locust` | Stop all processes with "locust" in the command |
| `tail -f <logfile>` | Stream live log output |
| `ps aux \| grep locust` | List running Locust processes and their PIDs |

---

## References

- [Locust Documentation](https://docs.locust.io)
- [Locust — Running without the web UI](https://docs.locust.io/en/stable/running-without-web-ui.html)
- [logrotate man page](https://linux.die.net/man/8/logrotate)
- [F5 Distributed Cloud — Security Events](https://docs.cloud.f5.com/docs-v2/security-ops/security-events)
- [F5 Distributed Cloud — API Discovery](https://docs.cloud.f5.com/docs-v2/api-security/api-discovery)
- [vuln-bank — GitHub](https://github.com/Commando-X/vuln-bank)

---

## Quick Links

[Home Page](README.md) · [Vuln-Bank Installation](vuln-bank-install.md) · [F5 XC Configuration](xc-config.md)
