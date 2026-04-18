# F5 Distributed Cloud — Demo Environment

## Introduction

This repo is a step-by-step guide to setting up a demo environment for **F5 Distributed Cloud (XC)**. It covers three areas:

1. Deploying the backend demo application (**vuln-bank**) on a Linux server — see [vuln-bank-install.md](vuln-bank-install.md)
2. Configuring F5 XC security services (WAAP, Bot Defense, API Discovery) via the Postman collection — see [xc-config.md](xc-config.md)
3. Setting up a traffic generator to produce continuous, realistic traffic through the XC load balancer — see [traffic-generator.md](traffic-generator.md)

---

## Components

```
Android Device / Browser
        │
        │  HTTPS
        ▼
┌─────────────────────────────────────────┐
│         F5 Distributed Cloud (XC)       │
│  ┌──────────────────────────────────┐   │
│  │  HTTP Load Balancer (lb-vuln-bank│   │
│  │  ├── WAAP / App Firewall         │   │
│  │  ├── Bot Defense                 │   │
│  │  └── API Discovery & Testing     │   │
│  └──────────────┬───────────────────┘   │
│                 │ Origin Pool           │
└─────────────────┼───────────────────────┘
                  │  HTTP :5000
                  ▼
        ┌──────────────────┐
        │  Backend Server  │
        │  ├── vuln-bank   │
        │  │   (Flask API) │
        │  └── PostgreSQL  │
        └──────────────────┘

Traffic Generator Server
  └── Locust ──────────────────────────▶ XC Load Balancer endpoint
```

### 1. F5 XC WAAP and Bot Defense

**F5 Distributed Cloud** is a SaaS-delivered security and networking platform. In this demo, it sits in front of the vuln-bank backend and acts as the single point of entry for all traffic.

Key capabilities used in this demo:

| Capability | Description |
|---|---|
| **WAAP (Web App & API Protection)** | WAF that inspects HTTP traffic and blocks OWASP Top 10 attacks (SQLi, XSS, RCE, etc.) in real time |
| **Bot Defense** | Detects and mitigates automated bot traffic on protected endpoints (e.g. `/login`) using JS telemetry and behavioral analysis |
| **API Discovery** | Automatically maps all API endpoints observed in traffic, including shadow and unauthenticated endpoints |
| **AI Enhancements** | Risk-based threat scoring that adjusts blocking behavior based on attack confidence |
| **DDoS / L7 Protection** | Rate limiting and volumetric attack mitigation at the application layer |

In this demo, XC generates a rich stream of security telemetry — security events, bot signals, API inventory — driven by the traffic that Locust sends through it.

### 2. vuln-bank

**vuln-bank** ([github.com/Commando-X/vuln-bank](https://github.com/Commando-X/vuln-bank)) is a deliberately vulnerable banking application built by [Commando-X](https://github.com/Commando-X) for security demos and testing.

It includes:
- A Flask REST API backend with intentional vulnerabilities (SQLi, IDOR, broken auth, etc.)
- A PostgreSQL database
- An AI customer support agent (OpenAI-compatible, configurable via [AI-model-update.md](AI-model-update.md))
- A React Native mobile frontend: **vuln-bank-mobile** ([github.com/Commando-X/vuln-bank-mobile](https://github.com/Commando-X/vuln-bank-mobile))

In this demo, vuln-bank runs on a Linux server as the **origin** behind F5 XC. The mobile app (optional) can be built and installed on an Android device to simulate mobile API traffic through XC.

Demo user accounts used by the traffic generator and API testing:

| Username | Password | Role |
|---|---|---|
| `admin` | `admin123` | Admin |
| `franklin` | `123456` | Standard user |
| `john` | `123456` | Standard user |

### 3. Locust

**Locust** ([locust.io](https://locust.io)) is an open-source Python-based load testing tool. It simulates realistic user behaviour by executing scripted API flows against a target endpoint.

In this demo, Locust runs on a dedicated server and continuously sends traffic to the F5 XC load balancer endpoint. This generates the security events, bot signals, and API traffic data that populate the XC dashboards.

The traffic script is in [api-locustfile.py](api-locustfile.py), configured to run 50 concurrent simulated users. Full setup instructions are in [traffic-generator.md](traffic-generator.md).

---

## Requirements

### Backend Server (vuln-bank)

The backend server hosts the vuln-bank Flask API. If you plan to also build the mobile APK on the same server, use the higher specs.

| Spec | Minimum | Notes |
|---|---|---|
| **CPU** | 2 vCPUs | Single core will cause Gradle to hang at 0% INITIALIZING during mobile build |
| **RAM** | 8 GB | Less than 4 GB causes Gradle daemon to hang or OOM during mobile APK build |
| **Storage** | 20 GB free | Android SDK + Gradle cache + build artifacts are large |
| **OS** | Ubuntu 20.04 / 22.04 LTS | Other distros not tested |
| **Network** | Stable internet | Gradle downloads ~500MB+ of dependencies on first build |

> If you are only running the Flask backend (no mobile APK build), a **2 vCPU / 4 GB** server is sufficient.

> Port 5000 must be accessible from F5 XC Regional Edge IPs only — do not expose it to the public internet.

### Traffic Generator Server

A separate server is recommended for Locust so that its CPU and network usage does not interfere with backend performance metrics.

| Spec | Minimum |
|---|---|
| **CPU** | 1 vCPU |
| **RAM** | 2 GB |
| **OS** | Ubuntu 20.04 / 22.04 LTS |
| **Python** | 3.8+ |
| **Network** | Stable internet, low latency to the XC endpoint |

### Postman

The F5 XC configuration is performed via API using a provided Postman collection. Postman Desktop (any recent version) is required.

**Collection file:** [F5 XC - Vuln-Bank Setup.postman_collection.json](F5%20XC%20-%20Vuln-Bank%20Setup.postman_collection.json)

To import:
1. Open Postman Desktop
2. Click **Import** (top left)
3. Select [F5 XC - Vuln-Bank Setup.postman_collection.json](F5%20XC%20-%20Vuln-Bank%20Setup.postman_collection.json)

Before running any requests, set the following collection variables:

| Variable | Description |
|---|---|
| `xc_tenant` | Your F5 XC tenant subdomain (e.g. `mycompany`) |
| `xc_api_token` | Your F5 XC API token — generate from Console → Administration → Credentials |
| `vulnbank_base_url` | Domain for the load balancer, without `https://` (e.g. `vulnbank.yourdomain.com`) |

For the full step-by-step XC configuration walkthrough, see [xc-config.md](xc-config.md).

---

## References

- [vuln-bank — GitHub](https://github.com/Commando-X/vuln-bank)
- [vuln-bank-mobile — GitHub](https://github.com/Commando-X/vuln-bank-mobile)
- [F5 Distributed Cloud Documentation](https://docs.cloud.f5.com/docs-v2/)
- [F5 Distributed Cloud API Reference](https://docs.cloud.f5.com/docs-v2/api)
- [Locust Documentation](https://docs.locust.io)
