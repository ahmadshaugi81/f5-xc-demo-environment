[Home Page](README.md) · [Vuln-Bank Installation](vuln-bank-install.md) · [Traffic Generator Setup](traffic-generator.md)

---

# F5 XC Configuration — Step-by-Step Guide

This guide walks through configuring F5 Distributed Cloud (XC) for the vuln-bank demo environment using the provided Postman collection.

For an overview of the demo environment and its components, see [README.md](README.md).

---

## Prerequisites

- An active F5 XC tenant
- An F5 XC API token: **Console → Administration → Credentials → Add Credentials → API Token**
- Postman Desktop with the collection imported: [postman-collection-env-setup.json](postman-collection-env-setup.json)
- The vuln-bank backend server must be running and accessible (see [vuln-bank-install.md](vuln-bank-install.md))
- A domain name you control, to be delegated to F5 XC for auto-cert TLS

---

## Postman Collection Variables

Set these in Postman before running any requests: **Collection → Variables tab**

| Variable | Set by | Description | Example |
|---|---|---|---|
| `xc_tenant` | You | Your F5 XC tenant subdomain — the part before `.console.ves.volterra.io` | `mycompany` |
| `xc_api_token` | You | Your F5 XC API token — generate from Console → Administration → Credentials | `sk-abc123...` |
| `vulnbank_base_url` | You | Domain for the load balancer — no `https://` prefix | `vulnbank.yourdomain.com` |
| `origin_pool_ip` | You | Public IP of your backend server running vuln-bank on port 5000 | `1.2.3.4` |
| `base_url` | Auto (derived) | Full API base URL — built from `xc_tenant`, **do not modify** | `https://{{xc_tenant}}.console.ves.volterra.io` |
| `xc_tenant_fullname` | Auto (Step 1) | Full internal tenant name (e.g. `mycompany-abc12345`) — auto-populated by the Get Tenant Info request, **do not set manually** | — |

---

## Step-by-Step Configuration

Run the requests in the order below. Each step depends on the previous one. Take time to read each request in the Postman collection — the descriptions, headers, and body payloads explain how the F5 XC API works. Understanding the requests, not just running them, is what makes this demo valuable.

---

### Step 1 — Get Tenant Info

**Request:** `Tenant Info → Get Tenant Info (auto-set xc_tenant_fullname)`

**Method:** `GET /api/web/namespaces`

This request lists all namespaces in your tenant. A built-in Postman test script automatically extracts the full internal tenant name (e.g. `mycompany-abc12345`) from the response and stores it in the `xc_tenant_fullname` collection variable.

> **Run this first.** All subsequent requests that create objects reference `{{xc_tenant_fullname}}` in their payloads. If this variable is not set, origin pool, app firewall, and load balancer creation will fail.

Verify after running: check the **Collection Variables** tab and confirm `xc_tenant_fullname` is populated.

---

### Step 2 — Create Namespace

**Request:** `Namespaces → Create Namespace - vuln-bank`

**Method:** `POST /api/web/namespaces`

Creates the `vuln-bank` namespace. All demo resources (health check, origin pool, firewall policy, load balancer) are created inside this namespace, isolating them from other environments in your tenant.

```json
{
  "metadata": {
    "name": "vuln-bank",
    "description": "Namespace for vuln-bank lab environment"
  },
  "spec": {}
}
```

---

### Step 3 — Create Health Check

**Request:** `Health Check → Create Health Check - tcp-monitor`

**Method:** `POST /api/config/namespaces/vuln-bank/healthchecks`

Creates a TCP health check named `tcp-monitor`. The origin pool (Step 4) uses this to continuously verify that the backend server is reachable on port 5000.

Key settings:

| Setting | Value |
|---|---|
| Type | TCP |
| Interval | 15 seconds |
| Timeout | 3 seconds |
| Unhealthy threshold | 1 failed check |
| Healthy threshold | 3 consecutive successes |

---

### Step 4 — Create Origin Pool

**Request:** `Origin Pool → Create Origin Pool - origin-vuln-bank`

**Method:** `POST /api/config/namespaces/vuln-bank/origin_pools`

Creates an origin pool named `origin-vuln-bank` that points to your backend server.

The backend IP is read from the `{{origin_pool_ip}}` collection variable — no manual editing of the request body is needed. Ensure this variable is set in the **Collection → Variables tab** before running.

Key settings:

| Setting | Value |
|---|---|
| Backend IP | Your backend server's public IP |
| Port | 5000 |
| Protocol | HTTP (no TLS to origin) |
| Health check | `tcp-monitor` (from Step 3) |

---

### Step 5 — Create App Firewall Policy

**Request:** `App Firewall Policy → Create App Firewall - policy-vuln-bank`

**Method:** `POST /api/config/namespaces/vuln-bank/app_firewalls`

Creates a WAF policy named `policy-vuln-bank`. This policy is attached to the load balancer in Step 6 and inspects all inbound HTTP requests.

Key settings:

| Setting | Value |
|---|---|
| Mode | **Blocking** — malicious requests are actively blocked |
| Detection | Default detection settings (OWASP Top 10, protocol violations, etc.) |
| Bot detection | Default bot detection rules |
| AI enhancements | Enabled — high-risk requests are automatically mitigated based on risk score |
| Response codes | All response codes allowed (for demo visibility) |

---

### Step 6 — Create HTTP Load Balancer

**Folder:** `HTTP LB`

**Method:** `POST /api/config/namespaces/vuln-bank/http_loadbalancers`

Creates the HTTPS load balancer that serves as the public entry point for the demo. This is the most comprehensive step — the LB ties together all previously created objects and enables several security features.

> **Before running:** Confirm `{{vulnbank_base_url}}` is set correctly in the collection variables (e.g. `vulnbank.yourdomain.com`).

The collection includes **two variants** of this request. Choose the one that matches your tenant's enabled features:

| Request | When to use |
|---|---|
| `Create HTTP LB - lb-vuln-bank` | Use this when **Bot Defense is not enabled** on your tenant. Configures WAF, API Discovery, API Testing, and DDoS protection only. |
| `Create HTTP LB with Bot Defense - lb-vuln-bank` | Use this when **Bot Defense is enabled** on your tenant. Adds Bot Defense on the `/login` & `/transfer` endpoints (ASIA region) with JS injection and mobile SDK detection on top of the standard configuration. |

> **Not sure?** Check your tenant's subscription in the F5 XC Console under **Administration → Tenant Settings**. If Bot Defense does not appear as an available service, use the standard variant.

#### What both variants configure

**TLS / HTTPS**
- Auto-cert TLS on port 443 (F5 XC provisions and renews the certificate automatically)
- HTTP → HTTPS redirect enabled
- HSTS enabled
- HTTP/1.1 and HTTP/2 both supported

**WAF**
- Attaches `policy-vuln-bank` (blocking mode with AI enhancements)

**API Discovery**
- Learns API endpoints from observed traffic
- API Crawler enabled — automatically crawls the app using the `franklin` account credentials to discover authenticated endpoints
- Inactive API endpoints purged after 7 days

**API Testing**
- Runs automated API security tests daily against the discovered API inventory
- Configured credentials: `admin`, `franklin`, `john` (login endpoint: `POST /login`)

**DDoS / L7 Protection**
- L7 DDoS mitigation in blocking mode
- Default RPS threshold applied

**Other**
- Client IP trust: reads `X-Forwarded-For` header for real client IP identification
- Service policies: inherited from namespace
- Malicious user detection: disabled (for demo — keeps all traffic visible in dashboards)

#### Additional settings in the Bot Defense variant only

**Bot Defense**
- Regional endpoint: Asia
- Protected endpoint: `POST /login` — classified as an authentication login flow
- JavaScript injection: inserted on all pages (after `<head>`) for browser telemetry
- JS download path: `/common.js`
- JS mode: async with caching (minimal performance impact)
- Mobile SDK identifier: detects `okhttp/4.12.0` User-Agent as the mobile app

After this request succeeds, the demo app will be accessible at `https://{{vulnbank_base_url}}`. DNS delegation to F5 XC must be in place for TLS auto-cert provisioning to complete.

> **Integrating the mobile app with F5 Bot Defense SDK?** See [F5 Bot Defense Mobile SDK — Setup Guide](bot-def-sdk.md) for the full walkthrough on fusing the SDK into the `vuln-bank-mobile` APK.

---

### Step 7 — Create Demo Users

**Folder:** `Vuln-Bank - Users Creation`

**Method:** `POST https://{{vulnbank_base_url}}/register`

Creates the standard demo user accounts on the vuln-bank backend. These accounts are used by the traffic generator scripts (`locust-legitimate.py`, `locust-attack.py`) and by the XC API Testing feature configured in Step 6.

> **Run after Step 6.** The load balancer must be up and DNS must be resolving before these requests can reach the backend.

Run both requests in this folder:

| Request | Creates |
|---|---|
| `Register User - john` | username: `john` / password: `123456` |
| `Register User - franklin` | username: `franklin` / password: `123456` |

```json
{
  "username": "john",
  "password": "123456"
}
```

> **Note:** The `admin` account is seeded automatically when vuln-bank starts — you do not need to create it manually.

> **Vulnerability note:** The `/register` endpoint is intentionally vulnerable to BOLA (Broken Object Level Authorization). This is by design — it is one of the attack surfaces that the traffic generator and XC API Testing are configured to probe.

---

## Teardown

To remove all XC resources, run the **Delete** requests in reverse order:

| Order | Request |
|---|---|
| 1 | `Delete HTTP LB - lb-vuln-bank` |
| 2 | `Delete App Firewall - policy-vuln-bank` |
| 3 | `Delete Origin Pool - origin-vuln-bank` |
| 4 | `Delete Health Check - tcp-monitor` |
| 5 | `Delete Namespace - vuln-bank` |

> Deleting the namespace last ensures no dependent objects remain. Deleting a namespace with active references will fail.

> **Note on demo users:** The `john` and `franklin` accounts created in Step 7 live in the **vuln-bank PostgreSQL database**, not in F5 XC. They are not removed by the teardown steps above. To fully reset the application, clear the database on the backend server directly (see [vuln-bank-install.md](vuln-bank-install.md)).

---

## Verification

After completing all steps, verify the setup end-to-end:

1. **Check origin pool health** — in the F5 XC Console, navigate to `vuln-bank` namespace → Origin Pools → `origin-vuln-bank`. The backend should show as healthy (green).

2. **Access the app** — open `https://{{vulnbank_base_url}}` in a browser. You should see the vuln-bank login page served over HTTPS with a valid certificate.

3. **Verify demo users** — log in with `john` / `123456` and `franklin` / `123456` to confirm both accounts were created successfully.

4. **Trigger WAF** — send a basic SQLi attempt and confirm it is blocked:
   ```bash
   curl -k "https://vulnbank.yourdomain.com/login?user=admin'--"
   ```
   Expected: `403 Forbidden` or a block page response.

5. **Check Security Events** — in the XC Console, navigate to `vuln-bank` namespace → Security → Security Events. The blocked request should appear within 1–2 minutes.

---

## References

- [F5 Distributed Cloud API Reference](https://docs.cloud.f5.com/docs-v2/api)
- [Namespace API](https://docs.cloud.f5.com/docs-v2/api/namespace)
- [Health Check API](https://docs.cloud.f5.com/docs-v2/api/healthcheck)
- [Origin Pool API](https://docs.cloud.f5.com/docs-v2/api/origin_pool)
- [App Firewall API](https://docs.cloud.f5.com/docs-v2/api/app-firewall)
- [HTTP Load Balancer API](https://docs.cloud.f5.com/docs-v2/api/views-http-loadbalancer)

---

## Quick Links

[Home Page](README.md) · [Vuln-Bank Installation](vuln-bank-install.md) · [Traffic Generator Setup](traffic-generator.md)
