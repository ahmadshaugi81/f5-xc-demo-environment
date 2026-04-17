# F5 Distributed Cloud — Demo Environment Setup

A step-by-step guide to setting up a complete demo environment for **F5 Distributed Cloud (XC)**, covering:

1. [Backend Demo Apps](#1-backend-demo-apps)
2. [F5 XC Configuration](#2-f5-xc-configuration)
3. [Traffic Generator](#3-traffic-generator)

---

## Architecture Overview

```
Android Device / Browser
        │
        │  HTTPS
        ▼
F5 Distributed Cloud (XC)
  ├── HTTP Load Balancer (lb-vuln-bank)
  │     ├── WAAP / App Firewall (policy-vuln-bank)
  │     ├── Bot Defense
  │     └── API Discovery
  └── Origin Pool (origin-vuln-bank)
              │
              │  HTTP :5000
              ▼
        Backend Server (Linux)
          ├── vuln-bank (Flask API)  ← port 5000
          └── PostgreSQL             ← port 5432 (internal)

Traffic Generator Server (Linux)
  └── Locust → sends simulated traffic → F5 XC endpoint
```

---

## 1. Backend Demo Apps

The backend consists of two components from the [vuln-bank](https://github.com/Commando-X/vuln-bank) project:

- **vuln-bank** — a deliberately vulnerable Flask banking API (the backend)
- **vuln-bank-mobile** — a React Native mobile app that calls the Flask API

Full setup instructions are in [VULN-APP.md](VULN-APP.md).

### Summary

#### 1.1 — Deploy vuln-bank (Flask Backend)

```bash
sudo apt update
sudo apt install -y docker.io docker-compose
sudo systemctl enable docker && sudo systemctl start docker
sudo usermod -aG docker $USER && newgrp docker

git clone https://github.com/Commando-X/vuln-bank.git
cd vuln-bank
docker-compose up --build -d
```

Verify:

```bash
curl http://localhost:5000
```

Open firewall for XC Regional Edge access only:

```bash
sudo ufw allow from <XC_RE_IP_RANGE> to any port 5000
sudo ufw reload
```

> Restrict port 5000 to F5 XC Regional Edge (Asia) IPs only. Do not expose it publicly.

#### 1.2 — Configure the AI Agent (Optional)

The vuln-bank AI customer support agent uses an OpenAI-compatible API. See [AI-model-update.md](AI-model-update.md) for how to configure DeepSeek or OpenRouter.

#### 1.3 — Build and Install vuln-bank-mobile (Optional)

For the mobile app demo, see [VULN-APP.md](VULN-APP.md) for the full build and APK installation walkthrough.

After building, update `src/utils/api.ts` to point `API_BASE` at your F5 XC load balancer domain (not the backend IP directly):

```typescript
export const API_BASE = 'https://vulnbank.yourdomain.com';
```

#### 1.4 — Create Demo Users

After the backend is running, create the required demo user accounts via the vuln-bank API or the Postman collection. The demo uses:

| Username | Password | Role |
|---|---|---|
| `admin` | `admin123` | Admin |
| `franklin` | `123456` | Standard user |
| `john` | `123456` | Standard user |

---

## 2. F5 XC Configuration

F5 XC is configured via API using the provided Postman collection: **`F5 XC - Vuln-Bank Setup.postman_collection.json`**

### Prerequisites

- An active F5 XC tenant
- An API token: **Console → Administration → Credentials → Add Credentials → API Token**

### Postman Collection Variables

Set these variables in the collection before running any requests:

| Variable | Description | Example |
|---|---|---|
| `xc_tenant` | Your tenant subdomain | `mycompany` |
| `xc_api_token` | F5 XC API Token | `APIToken abc123...` |
| `vulnbank_base_url` | Domain for the LB (no `https://`) | `vulnbank.yourdomain.com` |
| `xc_tenant_fullname` | Auto-populated — do not set manually | — |

### Step-by-Step Setup (run in order)

#### Step 1 — Get Tenant Info

Run **"Get Tenant Info (auto-set xc_tenant_fullname)"** — this auto-populates `xc_tenant_fullname`, which is required by all subsequent requests.

#### Step 2 — Create Namespace

**POST** `Namespaces → Create Namespace - vuln-bank`

Creates the `vuln-bank` namespace that isolates all demo resources.

#### Step 3 — Create Health Check

**POST** `Health Check → Create Health Check - tcp-monitor`

Creates a TCP health check (`tcp-monitor`) used by the origin pool to monitor backend availability.

#### Step 4 — Create Origin Pool

**POST** `Origin Pool → Create Origin Pool - origin-vuln-bank`

Creates an origin pool pointing to your backend server IP on port 5000, with `tcp-monitor` attached.

> Update the IP address in the request body to match your actual backend server IP.

#### Step 5 — Create App Firewall Policy

**POST** `App Firewall Policy → Create App Firewall - policy-vuln-bank`

Creates a WAF policy in **blocking mode** with AI-enhanced threat detection.

#### Step 6 — Create HTTP Load Balancer

**POST** `Create HTTP LB - lb-vuln-bank`

Creates the HTTPS load balancer that:
- Terminates TLS with auto-cert
- Redirects HTTP → HTTPS
- Attaches the WAF policy (`policy-vuln-bank`)
- Attaches the origin pool (`origin-vuln-bank`)
- Enables Bot Defense on the `/login` endpoint
- Enables API Discovery with API Crawler
- Enables API Testing

After this request succeeds, your demo app should be accessible at `https://vulnbank.yourdomain.com`.

### Teardown (reverse order)

To tear down, run the corresponding **Delete** requests in reverse order:

1. Delete HTTP LB - lb-vuln-bank
2. Delete App Firewall - policy-vuln-bank
3. Delete Origin Pool - origin-vuln-bank
4. Delete Health Check - tcp-monitor
5. Delete Namespace - vuln-bank

---

## 3. Traffic Generator

The traffic generator uses [Locust](https://locust.io) to simulate realistic user traffic against the F5 XC load balancer endpoint.

Full setup and locustfile details are in [traffic-generator.md](traffic-generator.md).

### 3.1 — Set Up the Traffic Generator Server

Provision a separate Linux server (Ubuntu 20.04/22.04 recommended) for running Locust. A small instance (1–2 vCPU, 2GB RAM) is sufficient.

Install Locust:

```bash
sudo apt update
sudo apt install -y python3-pip
pip3 install locust
```

Transfer the locustfile to the server:

```bash
scp api-locustfile.py user@<TRAFFIC_GEN_SERVER_IP>:~/locustfile.py
```

### 3.2 — Configure Log Rotation (Before Starting Locust)

Set up logrotate first so log rotation is active from the moment Locust starts:

```bash
sudo nano /etc/logrotate.d/locust
```

Paste the following (update the path to match your user's home directory):

```
/home/<your_user>/locust.log {
    size 100M
    rotate 3
    compress
    missingok
    notifempty
    copytruncate
}
```

Test the config:

```bash
sudo logrotate -d /etc/logrotate.d/locust
```

### 3.3 — Start Traffic Generation

```bash
nohup locust -f locustfile.py \
  --host=https://vulnbank.yourdomain.com \
  --headless --users 50 --spawn-rate 5 --run-time 3d \
  > locust.log 2>&1 &
```

### 3.4 — Monitor and Manage

Confirm Locust is running:

```bash
ps aux | grep locust
tail -f locust.log
```

Stop Locust:

```bash
# Graceful stop
kill <PID>

# Force stop (if unresponsive)
kill -9 <PID>
```

---

## Files in This Repo

| File | Description |
|---|---|
| [VULN-APP.md](VULN-APP.md) | Full guide: deploy vuln-bank backend + build vuln-bank-mobile APK |
| [AI-model-update.md](AI-model-update.md) | Configure the AI agent (DeepSeek / OpenRouter) |
| [traffic-generator.md](traffic-generator.md) | Locust traffic generator setup and log rotation |
| [api-locustfile.py](api-locustfile.py) | Locust script for simulating API traffic |
| `F5 XC - Vuln-Bank Setup.postman_collection.json` | Postman collection for all F5 XC API configuration steps |

---

## References

- [vuln-bank — GitHub](https://github.com/Commando-X/vuln-bank)
- [vuln-bank-mobile — GitHub](https://github.com/Commando-X/vuln-bank-mobile)
- [F5 Distributed Cloud API Reference](https://docs.cloud.f5.com/docs-v2/api)
- [Locust Documentation](https://docs.locust.io)
