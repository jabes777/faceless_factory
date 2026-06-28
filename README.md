# 🏭 Faceless Factory — Full-Automation YouTube Pipeline

[![GitHub stars](https://img.shields.io/github/stars/jabes777/faceless_factory?style=flat-square)](https://github.com/jabes777/faceless_factory/stargazers)
[![Last commit](https://img.shields.io/github/last-commit/jabes777/faceless_factory?style=flat-square)](https://github.com/jabes777/faceless_factory/commits/main)
[![Python 3.9+](https://img.shields.io/badge/python-3.9%2B-blue?style=flat-square)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green?style=flat-square)](LICENSE)

A runnable, niche-agnostic pipeline that turns a **topic** into a complete, **monetization-compliant** faceless-YouTube video package: original script → narration audio → visual storyboard + render plan → CTR thumbnail spec → SEO metadata → upload payload.

Built from the strategy distilled in [`../Faceless_AI_YouTube_50_Channels_Analysis_And_Blueprint.md`](../Faceless_AI_YouTube_50_Channels_Analysis_And_Blueprint.md). Pre-configured for the recommended channel **"Dinero con Propósito"** (Spanish finance + faith), but you change one file (`config.json`) to run any niche/language.

> **Designed around YouTube's July-2025 "inauthentic content" policy.** It is *not* a spam-mill. Every episode pulls a **materially different** topic, a built-in `compliance_gate` scores unique substance, and an **AI-disclosure** flag is set on upload. AI does ~90% of the labor; you keep the original creative spine.

---

## ⚡ Quickstart (runs today, zero API keys, zero installs)

```bash
cd faceless_factory
python3 run.py                       # one video from the next topic in topics.txt
python3 run.py "tu tema aquí"        # one video from your own topic
python3 run.py --batch 5             # five videos (advances the topic queue)
```

In **dry-run** (no keys) it generates a structured script, **real Spanish audio via macOS `say`**, the full storyboard, render plans, thumbnail spec, metadata, and the exact upload payload — so you can inspect a complete `output/<slug>/` package immediately.

### What each run writes to `output/<slug>/`
| File | Stage | What it is |
|---|---|---|
| `script.txt` | 1 | Narration script (hook → body → CTA) |
| `voiceover.aiff`/`.mp3` + `.ssml` | 2 | Narration audio + SSML for any TTS |
| `storyboard.json` | 3 | Per-shot stock queries, image prompts, captions, durations |
| `render_shotstack.json` + `render_ffmpeg.sh` | 4 | Cloud render JSON **and** local ffmpeg recipe |
| `thumbnail_spec.json` | 5 | Image prompt + text-overlay layout (A/B variants) |
| `metadata.json` | 6 | Title, description, tags, chapters, pinned comment, AI disclosure |
| `upload_payload.json` | 7 | Exact YouTube Data API insert body |
| `manifest.json` | — | Run summary incl. compliance score + timings |

---

## 🚀 Going live (swap dry-run for real APIs)

1. `cp .env.example .env` and fill the keys you have. The pipeline auto-upgrades each stage when its key is present — no code changes.
   - **Script:** `ANTHROPIC_API_KEY` (Claude) *or* `OPENAI_API_KEY`.
   - **Voice:** `ELEVENLABS_API_KEY` + set `voice.voice_id` in `config.json`.
   - **Visuals:** `PEXELS_API_KEY` / `PIXABAY_API_KEY` to fetch real b-roll.
   - **Render:** install `ffmpeg` (`brew install ffmpeg`) for local, *or* set `SHOTSTACK_API_KEY` for cloud.
2. `pip install -r requirements.txt` (only needed for live mode).
3. **YouTube upload:** create an OAuth *desktop* client in Google Cloud, enable **YouTube Data API v3**, download `client_secret.json` into this folder, then `python run.py auth` once → produces `token.json`.
4. Run normally. With keys + `token.json` + a rendered `final.mp4`, stage 7 uploads automatically (defaults to `privacy_status: private` so you approve before going public).

---

## 🔁 Full automation (set-and-forget)

- **Cron (fully local):** see [`automation/schedule.crontab`](automation/schedule.crontab) — daily build + Sunday batch.
- **n8n (recommended):** import [`automation/n8n_workflow.json`](automation/n8n_workflow.json) — Schedule → run pipeline → Shotstack render → YouTube upload → Slack notify. Keep a manual approval node before publish if you want a human in the loop.

---

## 🎛️ Configure your channel — edit `config.json`

Everything is data-driven: `channel` (name/niche/audience/format/length/cadence), `voice`, `script.model`, `visuals`, `assemble`, `seo`, `upload`, and `compliance` thresholds. To launch a **second** channel in another niche, copy this folder, edit `config.json` + `topics.txt`, done.

`topics.txt` is your content queue — **keep every line materially distinct** (that's the compliance moat). The pipeline pops the next unused topic and records used ones in `output/.used_topics`.

---

## 🗺️ Pipeline map

```
topic ─▶ ideas (titles+angle) ─▶ script (Claude/GPT | dry) ─▶ compliance_gate
      ─▶ voice (ElevenLabs | say) ─▶ visuals (storyboard) ─▶ assemble (Shotstack/ffmpeg plan)
      ─▶ thumbnail (spec) ─▶ metadata (SEO) ─▶ upload (YouTube API) ─▶ manifest.json
```

Each stage is an independent module in `core/` — fork any one without touching the rest.
