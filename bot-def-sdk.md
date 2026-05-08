# UNDER CONSTRUCTION!!!
# F5 Bot Defense Mobile SDK — Setup Guide (Android)

> This guide documents how to fuse the F5 Bot Defense Mobile SDK into the `vuln-bank-mobile` APK using the **F5 Mobile SDK Integrator** (no-code approach). This is a companion guide to [Vuln-Bank Installation](vuln-bank-install.md) and [F5 XC Configuration](xc-config.md).

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

**Understand the Keystore Details**
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

## Step 2 — Get Required Files from F5 XC Bot Defense Console

Three files are needed from the F5 XC Console. For the full step-by-step walkthrough on generating and downloading each file, refer to the [F5 Bot Defense official documentation](https://docs.cloud.f5.com/docs-v2/bot-defense/how-tos/plan-bot-defense).

| File | What it is |
|---|---|
| F5 Distributed Cloud Mobile SDK (`.dat`) | SDK binary for Android |
| Mobile base configuration file (`.dat`) | App-specific Bot Defense configuration tied to your tenant |
| F5 Distributed Cloud Mobile SDK Integrator (`.jar`) | No-code tool that fuses the SDK and configuration into your APK |

---

## Step 3 — Prepare Your Working Directory

Organize all required files in one directory on your PC for convenience.

**1. Create a working directory:**

```bash
mkdir ~/f5-integrator
cd ~/f5-integrator
```

**2. Move the downloaded APK and keystore here:**

```bash
mv ~/Downloads/app-release.apk .
mv ~/Downloads/debug.keystore .
```

**3. Copy the F5 files here too** (adjust filenames to match your versions):

```bash
cp /path/to/Integrator-Android-x.x.x.jar .
cp /path/to/F5-XC-Mobile-SDK-Integrator-Android-plugin-x.x.x-x.dat .
cp /path/to/mobile-base-config.dat .
```

---

## Step 4 — Run the F5 Mobile SDK Integrator

The integration is done in **two commands**: first generate a configuration profile, then run the Integrator to fuse the SDK into the APK.

From your working directory:

```bash
cd ~/f5-integrator
```

---

### Command 1 — Generate the Configuration Profile

```bash
python3 ./create_config.py \
  --target-os Android \
  --apiguard-init on-application-create \
  --apiguard-config ./your-base-config.json \
  --environment prod \
  --enable-logs \
  --outfile your-base-config.dat
```

> Replace `your-base-config.json` with the actual filename of the base configuration file you downloaded from the F5 XC Console (e.g. `mytechlab-vulnbank-base-config.json`). Use the same name prefix for `--outfile`.

| Parameter | Purpose |
|---|---|
| `--target-os` | Target platform — `Android` or `iOS` |
| `--apiguard-init` | SDK initialization trigger — `on-application-create` starts the SDK when the app launches |
| `--apiguard-config` | Base configuration file downloaded from F5 XC Console (`.json`) |
| `--environment` | Deployment environment — use `prod` for production |
| `--enable-logs` | Allows APIGuard logs to appear in the console |
| `--outfile` | Output filename for the generated integration profile (`.dat`) |

This produces `your-base-config.dat` — the integration profile used in Command 2.

---

### Command 2 — Fuse the SDK into the APK

```bash
java -jar Integrator-Android-7.0.0.jar \
  --plugin F5-XC-Mobile-SDK-Integrator-Android-plugin-4.7.0-7.dat \
  --plugin your-base-config.dat \
  app-release.apk \
  --output app-release-with-plugin.apk \
  --keystore debug.keystore \
  --storepass android \
  --keyname androiddebugkey \
  --keypass android
```

> Replace `your-base-config.dat` with the filename you used in `--outfile` from Command 1. Adjust the Integrator JAR and plugin `.dat` filenames to match your downloaded versions.

| Parameter | Purpose |
|---|---|
| `-jar` | F5 Distributed Cloud Mobile SDK Integrator (`.jar`) |
| `--plugin` (1st) | F5 Distributed Cloud Mobile SDK Integrator plugin binary (`.dat`) |
| `--plugin` (2nd) | Integration profile generated in Command 1 |
| (input) | Original APK to fuse |
| `--output` | Output filename for the fused APK |
| `--keystore` | Keystore file to re-sign the fused APK |
| `--storepass` | Password to open the keystore |
| `--keyname` | Alias of the signing key |
| `--keypass` | Password for the signing key |

> ⚠️ The Integrator **re-signs** the APK after fusing. You must provide the same keystore used to sign the original APK — otherwise Android will reject the fused APK due to a signature mismatch.

Verify the fused APK was created:

```bash
ls -lh sdkintegrator-apk-release.apk
```

---

## Step 5 — Install Fused APK on Android Device

Install the fused APK to your Android device or emulator to simulate traffic and testing.

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

Also check the F5 XC Bot Defense Console to verify that request traffic has been detected and is visible in the Console.

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