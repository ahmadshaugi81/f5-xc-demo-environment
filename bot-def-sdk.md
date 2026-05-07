# UNDER CONSTRUCTION!!!
# F5 Bot Defense Mobile SDK — Setup Guide (Android)

> This guide documents how to fuse the F5 Bot Defense Mobile SDK into the `vuln-bank-mobile` APK using the **F5 Mobile SDK Integrator** (no-code approach). This is a companion guide to the [vuln-bank setup guide](./README.md).

---

## 📐 Overview

### What is the F5 Bot Defense Mobile SDK?

The F5 Bot Defense Mobile SDK protects mobile applications from automated bot traffic. It embeds into your APK and collects device telemetry, then attaches cryptographic headers to outbound HTTP requests. F5 Bot Defense uses these headers to verify that requests come from a legitimate human user on a real device — not a bot or automation tool.

### What is the F5 Mobile SDK Integrator?

The Integrator is a **no-code tool** that fuses the SDK into an existing APK without modifying source code. It works by injecting the SDK library and telemetry hooks directly into the compiled APK binary.

```
Original APK (app-release.apk)
        │
        │  java -jar Integrator-Android-X.X.X.jar
        ▼
Fused APK (sdkintegrator-apk-release.apk)
  ├── Original app code
  ├── F5 Bot Defense SDK (injected)
  └── Telemetry hooks (injected into OkHttp/network layer)
```

### How It Works at Runtime

```
Android Device
  └── Fused APK
        └── OkHttp (network layer)
              └── F5 SDK (injected)
                    └── Attaches telemetry headers to every request
                              │
                              ▼
                    F5 Bot Defense (validates headers)
                              │
                              ▼
                    vuln-bank Flask backend (port 5000)
```

---

## Prerequisites

### On Your Mac (where you run the Integrator)

| Requirement | Version | Check |
|---|---|---|
| Java JDK | 17+ | `java -version` |
| F5 Integrator JAR | e.g. `Integrator-Android-7.0.0.jar` | Provided by F5 |
| F5 SDK Plugin `.dat` | e.g. `F5-XC-Mobile-SDK-Integrator-Android-plugin-4.7.0-7.dat` | Provided by F5 |
| Plugin config `.dat` | `my-plugin-config.dat` | Generated from F5 XC console |
| `app-release.apk` | Built from vuln-bank-mobile | See vuln-bank setup guide |
| `debug.keystore` | From vuln-bank-mobile Android project | See below |

### Install Java on Mac (if not installed)

```bash
java -version
```

If not installed:

```bash
brew install openjdk@17
```

Or download directly from [Adoptium](https://adoptium.net/).

---

## Step 1 — Get Required Files from Ubuntu Server

You need two files from your Ubuntu server: the compiled APK and the keystore used to sign it. Download the files via Python HTTP Server (Recommended), SCP, or other preferred method.

> **Understand the Keystore Details**
> 
> <details>
> <summary>Click to expand — keystore background and credentials</summary>
> 
> The `vuln-bank-mobile` release APK is signed with the **debug keystore**. This is because the `build.gradle` release buildType references `signingConfigs.debug`:
> 
> ```groovy
> buildTypes {
>     release {
>         signingConfig signingConfigs.debug   // ← uses debug keystore for release
>         ...
>     }
> }
> ```
> 
> The keystore credentials for `vuln-bank-mobile` are:
> 
> | Parameter | Value |
> |---|---|
> | `--keystore` | `debug.keystore` (file path on your Mac) |
> | `--storepass` | `android` |
> | `--keyname` | `androiddebugkey` |
> | `--keypass` | `android` |
> 
> > **What do these mean?**
> > - **keystore** — the vault file that holds the signing key
> > - **storepass** — password to open the vault
> > - **keyname** — alias/label of the specific key inside the vault
> > - **keypass** — password for that specific key
> 
> </details>

---

## Step 3 — Prepare Your Working Directory

Organize all required files in one directory on your Mac for convenience:

```bash
mkdir ~/f5-integrator
cd ~/f5-integrator

# Move downloaded files here
mv ~/Downloads/app-release.apk .
mv ~/Downloads/debug.keystore .

# Copy F5 files here too (adjust filenames to your versions)
cp /path/to/Integrator-Android-7.0.0.jar .
cp /path/to/F5-XC-Mobile-SDK-Integrator-Android-plugin-4.7.0-7.dat .
cp /path/to/my-plugin-config.dat .
```

Verify all files are present:

```bash
ls ~/f5-integrator/
```

Expected output:
```
Integrator-Android-7.0.0.jar
F5-XC-Mobile-SDK-Integrator-Android-plugin-4.7.0-7.dat
my-plugin-config.dat
app-release.apk
debug.keystore
```

---

## Step 4 — Run the F5 Mobile SDK Integrator

From your working directory:

```bash
cd ~/f5-integrator

java -jar Integrator-Android-7.0.0.jar \
  --plugin F5-XC-Mobile-SDK-Integrator-Android-plugin-4.7.0-7.dat \
  --plugin my-plugin-config.dat \
  app-release.apk \
  --output sdkintegrator-apk-release.apk \
  --keystore debug.keystore \
  --storepass android \
  --keyname androiddebugkey \
  --keypass android
```

### Parameter Breakdown

| Parameter | Value | Purpose |
|---|---|---|
| `-jar` | `Integrator-Android-7.0.0.jar` | The Integrator tool itself |
| `--plugin` | `F5-XC-Mobile-SDK-Integrator-Android-plugin-4.7.0-7.dat` | F5 SDK plugin binary |
| `--plugin` | `my-plugin-config.dat` | Your app-specific Bot Defense config |
| (input) | `app-release.apk` | Original APK to fuse |
| `--output` | `sdkintegrator-apk-release.apk` | Output fused APK filename |
| `--keystore` | `debug.keystore` | Keystore file to re-sign the fused APK |
| `--storepass` | `android` | Password to open the keystore |
| `--keyname` | `androiddebugkey` | Alias of the signing key |
| `--keypass` | `android` | Password for the signing key |

> ⚠️ The Integrator **re-signs** the APK after fusing. You must provide the same keystore that was used to sign the original APK, otherwise the fused APK will be rejected by Android as having a mismatched signature.

### Expected Output

```
Processing app-release.apk...
Injecting F5 Bot Defense SDK...
Re-signing APK...
Output written to: sdkintegrator-apk-release.apk
Integration complete.
```

Verify the fused APK was created:

```bash
ls -lh sdkintegrator-apk-release.apk
```

---

## Step 5 — Install Fused APK on Android Device

### Option A — Install via ADB (USB)

Connect your Android device via USB, enable USB debugging, then:

```bash
adb devices   # verify device is detected
adb install sdkintegrator-apk-release.apk
```

> ⚠️ If the original APK is already installed, uninstall it first:
> ```bash
> adb uninstall com.vulnerablebank.app   # adjust package name
> ```

### Option B — Serve via HTTP and Download on Device

```bash
cd ~/f5-integrator
python3 -m http.server 8888
```

On your **Android device browser**:

```
http://YOUR_MAC_IP:8888/sdkintegrator-apk-release.apk
```

Download and install. Make sure unknown sources is enabled:

```
Settings → Security → Install Unknown Apps → Allow your browser
```

---

## Step 6 — Verify SDK Integration

After installing the fused APK, use a proxy tool (e.g. Burp Suite, mitmproxy) to inspect outbound HTTP requests from the app.

Before fusing, requests look like:

```
POST /login HTTP/1.1
Host: 192.168.1.100:5000
User-Agent: okhttp/4.12.0
Content-Type: application/json
```

After fusing with F5 SDK, requests should include additional telemetry headers:

```
POST /login HTTP/1.1
Host: 192.168.1.100:5000
User-Agent: okhttp/4.12.0
Content-Type: application/json
X-F5-BotDefense: <telemetry_token>
```

> The presence of the `X-F5-BotDefense` header (or equivalent, depending on your config) confirms the SDK is working and attaching telemetry to requests.

---

## 🔧 Troubleshooting

### ❌ `java: command not found`

**Cause:** Java is not installed on your Mac.

**Fix:**
```bash
brew install openjdk@17
# Then add to PATH:
echo 'export PATH="/opt/homebrew/opt/openjdk@17/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc
java -version
```

---

### ❌ `Keystore was tampered with, or password was incorrect`

**Cause:** Wrong `--storepass` or `--keypass` provided, or wrong keystore file.

**Fix:** Verify the keystore credentials match the ones used to sign the original APK. For `vuln-bank-mobile`:
```
--storepass android
--keyname androiddebugkey
--keypass android
```

---

### ❌ `INSTALL_FAILED_UPDATE_INCOMPATIBLE`

**Cause:** The fused APK has a different signature than the version already installed on the device.

**Fix:** Uninstall the existing app first, then install the fused APK:
```bash
adb uninstall com.vulnerablebank.app
adb install sdkintegrator-apk-release.apk
```

---

### ❌ `Plugin file not found` or `Invalid plugin`

**Cause:** Plugin `.dat` file path is wrong or file is corrupted.

**Fix:** Verify all files exist in the working directory:
```bash
ls -lh ~/f5-integrator/
```
Confirm filenames match exactly what you reference in the command — versions in filenames matter.

---

### ❌ App connects but no F5 telemetry headers visible

**Cause:** SDK fusing may not have completed properly, or the endpoint is not configured in the Bot Defense policy.

**Fix:**
- Verify the Integrator output showed `Integration complete` without errors
- Check your `my-plugin-config.dat` to ensure the correct endpoints are configured for protection
- Verify your F5 XC Bot Defense policy includes the endpoint being called

---

## 📋 Quick Reference Checklist

```
PREPARATION
[ ] Java 17+ installed on Mac
[ ] All 5 files present in working directory:
    [ ] Integrator-Android-X.X.X.jar
    [ ] F5-XC-Mobile-SDK-Integrator-Android-plugin-X.X.X.dat
    [ ] my-plugin-config.dat
    [ ] app-release.apk
    [ ] debug.keystore

FUSING
[ ] Integrator command ran without errors
[ ] sdkintegrator-apk-release.apk created in working directory

INSTALLATION
[ ] Original APK uninstalled from device (if previously installed)
[ ] Fused APK installed on device
[ ] App launches successfully
[ ] App connects to vuln-bank backend

VERIFICATION
[ ] Proxy tool captures requests from fused app
[ ] F5 telemetry headers present in outbound requests
[ ] F5 XC Bot Defense console shows mobile traffic
```

---

## 📚 References

- [F5 Distributed Cloud API Documentation](https://docs.cloud.f5.com/docs-v2/api)
- [vuln-bank Setup Guide](./README.md)
- [vuln-bank GitHub](https://github.com/Commando-X/vuln-bank)
- [vuln-bank-mobile GitHub](https://github.com/Commando-X/vuln-bank-mobile)

---

## ⚖️ License & Attribution

This guide references the original work by **Commando-X**:

- [vuln-bank](https://github.com/Commando-X/vuln-bank) — Copyright (c) Commando-X
- [vuln-bank-mobile](https://github.com/Commando-X/vuln-bank-mobile) — Copyright (c) Commando-X

Both original projects are licensed under the **MIT License**:
- [vuln-bank LICENSE](https://github.com/Commando-X/vuln-bank/blob/main/LICENSE)
- [vuln-bank-mobile LICENSE](https://github.com/Commando-X/vuln-bank-mobile/blob/main/LICENSE)

This setup guide is an independent documentation effort. All rights to the original projects remain with their respective authors.