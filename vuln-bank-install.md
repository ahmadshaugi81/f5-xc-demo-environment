# Vuln-Bank + Vuln-Bank-Mobile — Custom Setup Guide

> This guide documents the step-by-step setup of [vuln-bank](https://github.com/Commando-X/vuln-bank) and [vuln-bank-mobile](https://github.com/Commando-X/vuln-bank-mobile) on a self-hosted Linux server, including all caveats, errors, and fixes encountered during the process.

---

## 📐 Architecture Overview

```
Your Android Device / Emulator
        │
        │  HTTP API calls (port 5000)
        ▼
Linux Server
  ├── vuln-bank (Flask API) ← port 5000
  └── PostgreSQL           ← port 5432 (internal)
```

- **vuln-bank** — the Flask backend API, runs permanently on your server
- **vuln-bank-mobile** — React Native mobile app, built on the server into a release APK, then installed on Android device
- The mobile app is purely a frontend that calls the Flask backend

---

## 🗺️ Which Setup Do You Need?

| Scenario | What You Need | Jump To |
|---|---|---|
| **Scenario A** — Backend only (web testing, API testing) | vuln-bank only | [Part 1](#part-1-backend-setup-vuln-bank) |
| **Scenario B** — Backend + Mobile app | vuln-bank + vuln-bank-mobile | [Part 1](#part-1-backend-setup-vuln-bank) + [Part 2](#part-2-mobile-app-setup-vuln-bank-mobile) |

> ⚠️ **Part 2 requires Part 1 to be completed first.** The mobile app is a frontend for the Flask backend — both must be running for the app to work.

---

## Prerequisites

### Server Requirements

| Spec | Scenario A (Backend Only) | Scenario B (Backend + Mobile) |
|---|---|---|
| **CPU** | 1 vCPU minimum | 2 vCPUs minimum ⚠️ |
| **RAM** | 2 GB minimum | 8 GB minimum ⚠️ |
| **Storage** | 5 GB free | 20 GB free |
| **OS** | Ubuntu 20.04 / 22.04 LTS | Ubuntu 20.04 / 22.04 LTS |
| **Network** | Stable internet | Stable internet |

> ⚠️ For Scenario B: Single core or less than 4GB RAM will cause Gradle to hang at `0% INITIALIZING` during the Android build.

### Software Dependencies

| Dependency | Required For | ⚠️ Caveat |
|---|---|---|
| Docker + Docker Compose | Both scenarios | Required to run vuln-bank backend |
| Node.js 18+ | Scenario B only | Ubuntu default `apt install nodejs` installs v12 — **too old**. Must install via NVM |
| Java JDK 17+ | Scenario B only | Not pre-installed. Missing JDK causes `JAVA_HOME is not set` error |
| Android SDK API 33 | Scenario B only | Not pre-installed. Missing SDK causes `SDK location not found` error |

---

# Part 1: Backend Setup (vuln-bank)

> ✅ Required for both Scenario A and Scenario B.

### Step 1 — Install Docker

```bash
sudo apt update
sudo apt install -y docker.io docker-compose
sudo systemctl enable docker
sudo systemctl start docker
sudo usermod -aG docker $USER
newgrp docker
```

### Step 2 — Clone and Run vuln-bank

```bash
git clone https://github.com/Commando-X/vuln-bank.git
cd vuln-bank
docker-compose up --build -d
```

### Step 3 — Verify Backend is Running

```bash
curl http://localhost:5000
```

You should get a response from the Flask app. If not, check Docker logs:

```bash
docker-compose logs -f
```

### Step 4 — Open Firewall Port 5000 (If needed)

```bash
sudo ufw allow 5000
sudo ufw reload
sudo ufw status
```

> Your Android device will connect to this port over the network.

---

✅ **Scenario A stops here.** The backend is running and accessible at `http://YOUR_SERVER_IP:5000`.

---

# Part 2: Mobile App Setup (vuln-bank-mobile)

> ✅ Required for Scenario B only. Make sure Part 1 is completed before proceeding.

### Step 1 — Install Node.js 18 via NVM

> ⚠️ Do NOT use `sudo apt install nodejs` — this installs Node.js v12 which is too old and will cause `node_modules/@react-native/gradle-plugin does not exist` error during the Gradle build.

```bash
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.7/install.sh | bash
source ~/.bashrc
nvm install 18
nvm use 18
node -v   # should show v18.x.x
npm -v
```

### Step 2 — Install Java JDK 17

> ⚠️ Gradle requires Java. Missing Java causes: `ERROR: JAVA_HOME is not set and no 'java' command could be found in your PATH`

```bash
sudo apt update
sudo apt install openjdk-17-jdk -y
java -version
```

Set `JAVA_HOME` permanently:

```bash
echo 'export JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64' >> ~/.bashrc
echo 'export PATH=$PATH:$JAVA_HOME/bin' >> ~/.bashrc
source ~/.bashrc
echo $JAVA_HOME   # verify
```

### Step 3 — Install Android SDK

> ⚠️ Missing Android SDK causes: `SDK location not found. Define a valid SDK location with an ANDROID_HOME environment variable`

```bash
cd ~
mkdir -p Android/sdk/cmdline-tools
wget https://dl.google.com/android/repository/commandlinetools-linux-11076708_latest.zip
unzip commandlinetools-linux-11076708_latest.zip -d Android/sdk/cmdline-tools
mv Android/sdk/cmdline-tools/cmdline-tools Android/sdk/cmdline-tools/latest
```

Set `ANDROID_HOME` permanently:

```bash
echo 'export ANDROID_HOME=$HOME/Android/sdk' >> ~/.bashrc
echo 'export PATH=$PATH:$ANDROID_HOME/cmdline-tools/latest/bin' >> ~/.bashrc
echo 'export PATH=$PATH:$ANDROID_HOME/platform-tools' >> ~/.bashrc
source ~/.bashrc
```

Install required SDK packages:

```bash
sdkmanager --licenses   # accept all licenses by typing 'y'
sdkmanager "platform-tools" "platforms;android-33" "build-tools;33.0.0"
```

### Step 4 — Clone vuln-bank-mobile and Install Dependencies

```bash
git clone https://github.com/Commando-X/vuln-bank-mobile.git
cd vuln-bank-mobile
npm install
```

> ⚠️ If `npm install` seems to complete but `node_modules/@react-native/` is missing, do a clean install:
> ```bash
> rm -rf node_modules
> rm -f package-lock.json
> npm install
> ```

Verify the critical Gradle plugin exists:

```bash
ls node_modules/@react-native/ | grep gradle
# should show: gradle-plugin
```

### Step 5 — Update API Base URL

The API endpoint is defined in `src/utils/api.ts` (not `App.tsx`):

```bash
cat src/utils/api.ts | head -3
```

Update `API_BASE` to point to your public domain that you also prepare for the F5 XC load balancer to access this apps:

```bash
sed -i "s|export const API_BASE = 'https://vulnbank.org';|export const API_BASE = 'https://YOUR_PUBLIC_DOMAIN_FOR_VULNBANK';|" src/utils/api.ts
```

Verify the change:

```bash
head -3 src/utils/api.ts
# should show: export const API_BASE = 'https://YOUR_PUBLIC_DOMAIN_FOR_VULNBANK';
```

> **Tip:** If testing with an Android emulator on the same machine as the backend, use `http://10.0.2.2:5000` — Android emulator maps `10.0.2.2` to the host machine's localhost.

### Step 6 — Verify AndroidManifest.xml (Optional)

> **Tip:** By following this guide, the application will be exposed in HTTPS service. But if you might need to modify the lab and exposed the apps in HTTP mode, then follow this step.

Confirm `android:usesCleartextTraffic="true"` is present in the `<application>` tag:

```bash
grep "usesCleartextTraffic" android/app/src/main/AndroidManifest.xml
```

Expected output:
```
android:usesCleartextTraffic="true"
```

If it's missing, add it manually:

```xml
<application
  android:usesCleartextTraffic="true"
  android:label="@string/app_name"
  ...>
```

> ⚠️ Android 9+ blocks plain HTTP traffic by default. Without this flag, the app cannot reach the Flask backend over HTTP.

### Step 8 — Build Release APK

```bash
cd ~/vuln-bank-mobile/android
./gradlew assembleRelease --no-daemon
```

> ⚠️ Use `--no-daemon` flag. Without it, Gradle daemon may hang indefinitely especially on first run.

First build takes **10–20 minutes** as Gradle downloads Android build tools, CMake, and other dependencies. Subsequent builds take 2–5 minutes.

Successful output:

```
BUILD SUCCESSFUL in Xm Xs
154 actionable tasks: 144 executed, 10 up-to-date
```

Verify APK was created:

```bash
ls -lh android/app/build/outputs/apk/release/
# should show: app-release.apk
```

### Step 9 — Install APK on Device

Serve the APK from your server via HTTP:

```bash
cd ~/vuln-bank-mobile/android/app/build/outputs/apk/release/
python3 -m http.server 8888
```

Open firewall port (if needed):

```bash
sudo ufw allow 8888
```

On your device navigate to:

```
http://YOUR_SERVER_IP:8888/app-release.apk
```

After successfully download, you may fuse this APK with **F5 Bot Defense SDK** using **F5 Mobile Integrator**, then install the output APK into emulator and Android device.


---

## 🔧 Troubleshooting

### ❌ Gradle stuck at `0% INITIALIZING` for 10+ minutes

**Cause:** Server has insufficient RAM (less than 4GB). Gradle daemon runs out of memory before the build starts.

**Fix:** Upgrade server to minimum 2 vCPU / 8GB RAM. Alternatively add swap space:

```bash
sudo fallocate -l 4G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
```

---

### ❌ `ERROR: JAVA_HOME is not set`

**Cause:** Java JDK is not installed.

**Fix:** Install JDK 17 and set `JAVA_HOME` — see [Step 3 of Part 2](#step-3--install-java-jdk-17).

---

### ❌ `node_modules/@react-native/gradle-plugin does not exist`

**Cause:** Node.js version is too old (v12 installed via `apt`) or `npm install` did not complete properly.

**Fix:** Install Node.js 18 via NVM — see [Step 2 of Part 2](#step-2--install-nodejs-18-via-nvm). Then do a clean install:

```bash
rm -rf node_modules
rm -f package-lock.json
npm install
```

---

### ❌ `SDK location not found`

**Cause:** Android SDK is not installed or `ANDROID_HOME` environment variable is not set.

**Fix:** Install Android SDK and set `ANDROID_HOME` — see [Step 4 of Part 2](#step-4--install-android-sdk).

---

### ❌ `apt update` failing with `400 Bad Request`

**Cause:** Broken nginx/app-protect repository entries in `/etc/apt/sources.list.d/` are blocking package installation.

**Fix:**

```bash
sudo mv /etc/apt/sources.list.d/nginx.list /etc/apt/sources.list.d/nginx.list.bak 2>/dev/null || true
sudo mv /etc/apt/sources.list.d/app-protect.list /etc/apt/sources.list.d/app-protect.list.bak 2>/dev/null || true
sudo apt-get clean
sudo apt-get update
```

---

### ❌ App cannot connect to backend

| Cause | Fix |
|---|---|
| Wrong IP in `API_BASE` | Re-check `src/utils/api.ts` — confirm IP matches your server |
| Port 5000 not open | Run `sudo ufw allow 5000 && sudo ufw reload` |
| Backend not running | Run `docker-compose ps` inside `vuln-bank/` directory |
| HTTP blocked by Android | Confirm `android:usesCleartextTraffic="true"` in `AndroidManifest.xml` |

---

## 📋 Quick Reference Checklist

```
SCENARIO A — BACKEND ONLY
[ ] Docker installed
[ ] vuln-bank cloned and running via docker-compose
[ ] Port 5000 open in firewall
[ ] curl http://localhost:5000 returns response

SCENARIO B — ADD MOBILE ON TOP OF SCENARIO A
[ ] Broken APT repos disabled (if applicable)
[ ] Node.js 18 installed via NVM
[ ] Java JDK 17 installed + JAVA_HOME set
[ ] Android SDK installed + ANDROID_HOME set
[ ] npm install completed without errors
[ ] node_modules/@react-native/gradle-plugin exists
[ ] API_BASE updated in src/utils/api.ts
[ ] android:usesCleartextTraffic="true" in AndroidManifest.xml
[ ] ./gradlew assembleRelease --no-daemon → BUILD SUCCESSFUL
[ ] app-release.apk exists in build/outputs/apk/release/
[ ] APK served via python3 -m http.server 8888
[ ] Unknown sources enabled on Android device
[ ] APK downloaded and installed on device
[ ] App connects to backend successfully
```

---

## 📚 References

- [vuln-bank GitHub](https://github.com/Commando-X/vuln-bank)
- [vuln-bank-mobile GitHub](https://github.com/Commando-X/vuln-bank-mobile)
- [NVM Installation](https://github.com/nvm-sh/nvm)
- [Android SDK Command Line Tools](https://developer.android.com/studio#command-tools)

---

## ⚖️ License & Attribution

This guide is based on the original work by **Commando-X**:

- [vuln-bank](https://github.com/Commando-X/vuln-bank) — Copyright (c) Commando-X
- [vuln-bank-mobile](https://github.com/Commando-X/vuln-bank-mobile) — Copyright (c) Commando-X

Both original projects are licensed under the **MIT License**:
- [vuln-bank LICENSE](https://github.com/Commando-X/vuln-bank/blob/main/LICENSE)
- [vuln-bank-mobile LICENSE](https://github.com/Commando-X/vuln-bank-mobile/blob/main/LICENSE)

This setup guide is an independent documentation effort and does not modify or redistribute the original source code. All rights to the original projects remain with their respective authors.