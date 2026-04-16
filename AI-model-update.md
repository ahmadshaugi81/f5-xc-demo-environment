# AI Model Configuration Guide 🤖

This guide covers how to configure and update the AI Customer Support agent in Vulnerable Bank, including switching between providers, using free tiers, and troubleshooting common errors.

---

## Overview

The AI agent in Vulnerable Bank (`ai_agent_deepseek.py`) supports any OpenAI-compatible API. By default it points to DeepSeek's API, but it can be redirected to any compatible provider by changing just **two values**:

| Setting | Location | Default |
|---|---|---|
| `self.api_url` | `ai_agent_deepseek.py` line ~37 | `https://api.deepseek.com/chat/completions` |
| `self.model` | `ai_agent_deepseek.py` line ~38 | `deepseek-chat` |
| API Key | `docker-compose.yml` environment | `DEEPSEEK_API_KEY` |

---

## Option 1: DeepSeek (Official API)

### Getting an API Key

1. Sign up at [platform.deepseek.com](https://platform.deepseek.com)
2. Go to **API Keys** → **Create Key**
3. New accounts receive **5 million free tokens**, valid for **30 days**
4. After the trial, the API is pay-as-you-go — no ongoing free tier

> ⚠️ After the 30-day trial expires, API calls return a `402 Insufficient Balance` error and the agent falls back to mock responses.

### Configuration

**`ai_agent_deepseek.py`**
```python
self.api_url = "https://api.deepseek.com/chat/completions"
self.model   = "deepseek-chat"
```

**`docker-compose.yml`**
```yaml
environment:
  - DEEPSEEK_API_KEY=sk-your-deepseek-key-here
```

---

## Option 2: OpenRouter (Recommended — Ongoing Free Tier)

OpenRouter is an API gateway that provides access to multiple AI models through a single endpoint. It maintains a genuine free tier with no expiry, making it the better long-term option for this lab.

### Getting an API Key

1. Sign up at [openrouter.ai](https://openrouter.ai)
2. Go to **Settings → Keys → Create Key**
3. Copy the key (format: `sk-or-...`)

### Configuration

**`ai_agent_deepseek.py`** — change two lines in `__init__`:
```python
self.api_url = "https://openrouter.ai/api/v1/chat/completions"
self.model   = "openrouter/free"   # auto-selects available free model
```

**`docker-compose.yml`** — replace the key value (keep the same variable name):
```yaml
environment:
  - DEEPSEEK_API_KEY=sk-or-your-openrouter-key-here
```

### Choosing a Model

You can pin a specific model instead of `openrouter/free`. Here are recommended options:

| Model ID | Notes |
|---|---|
| `openrouter/free` | **Recommended** — auto-selects any available free model |
| `google/gemma-4-31b-it:free` | Google Gemma 4, reliable free option |
| `meta-llama/llama-3.3-70b-instruct:free` | Meta Llama, strong general capability |
| `nvidia/nemotron-3-super-120b-a12b:free` | NVIDIA, 1M token context |

> 💡 Using `openrouter/free` is the most resilient choice — if one model is rate-limited or unavailable, OpenRouter automatically falls back to another free model.

> ⚠️ Free model availability changes over time. Always verify current free models at [openrouter.ai/collections/free-models](https://openrouter.ai/collections/free-models).

---

## Applying Changes

After editing `ai_agent_deepseek.py` and/or `docker-compose.yml`, rebuild the container:

```bash
cd ~/vuln-bank
sudo docker-compose down
sudo docker-compose up --build -d
```

> ⚠️ `docker-compose restart` is **not** sufficient — it does not re-read environment variables. Always use `down` + `up --build`.

### Verifying the Key is Loaded

```bash
sudo docker exec -it $(sudo docker ps -qf "name=web") env | grep DEEPSEEK
```

Expected output:
```
DEEPSEEK_API_KEY=sk-or-xxxxxxxxxxxx
```

If nothing is returned, the key is not being passed into the container. Double-check the `environment:` block in `docker-compose.yml`.

---

## Common Errors & Fixes

### `402 Insufficient Balance`
```
DeepSeek API error: 402 - {"error":{"message":"Insufficient Balance"}}
```
**Cause:** DeepSeek 30-day free trial has expired, or account has no balance.
**Fix:** Top up at [platform.deepseek.com](https://platform.deepseek.com), or switch to OpenRouter (see Option 2).

---

### `404 No endpoints found`
```
DeepSeek API error: 404 - {"error":{"message":"No endpoints found for <model>"}}
```
**Cause:** The model ID no longer exists or has been deprecated on the provider.
**Fix:** Update `self.model` to a currently available model. Check [openrouter.ai/collections/free-models](https://openrouter.ai/collections/free-models) for the latest list.

---

### `429 Rate Limited`
```
DeepSeek API error: 429 - {"error":{"message":"Provider returned error","code":429}}
```
**Cause:** The specific free model is temporarily rate-limited upstream.
**Fix:** Switch to `openrouter/free` to avoid this — it automatically routes around rate-limited models.

---

### Mock response returned (no API error shown)
The agent is in **mock mode**, meaning the API key is not reaching the container.
**Fix:** Ensure `DEEPSEEK_API_KEY` is set in `docker-compose.yml` under the `web` service `environment` block, then do a full `down` + `up --build`.

---

## How It Works Internally

The key method in `ai_agent_deepseek.py` is `_call_deepseek_api()`. It:

1. Checks if `DEEPSEEK_API_KEY` is set — falls back to mock if not
2. Sends a `POST` request to `self.api_url` with `Authorization: Bearer <key>`
3. Uses the standard OpenAI-compatible chat completions payload
4. Returns the LLM response, or an error string (which triggers mock fallback)

Because the payload format is OpenAI-compatible, **any provider that supports the OpenAI API spec** works as a drop-in replacement by just changing `self.api_url` and `self.model`.
