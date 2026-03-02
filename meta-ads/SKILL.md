---
name: meta-ads
description: "Autonomous Meta Ads manager AND campaign builder. Two modes: (1) Daily ops - monitor campaigns, auto-pause bleeders, shift budget to winners, generate copy, deliver morning brief. (2) /meta-campaign - 8-stage campaign builder that takes a landing page URL and produces upload-ready ad creatives (images via Genviral Studio + copy) for 4-5 ad sets. Use when asked to build new Meta ad campaigns or check Meta Ads performance."
---

# Meta Ads Skill

An [OpenClaw](https://openclaw.ai) skill for autonomous Meta Ads management and campaign building.

**Companion skill:** [genviral-skill](https://github.com/fdarkaou/genviral-skill) — image generation in Stage 7 uses the [Genviral Studio API](https://genviral.io).

---

## Two Modes

### Mode 1: Daily Ops
Automated monitoring, optimization, copy generation, morning brief.

```bash
bash scripts/run_all.sh genviral          # full pipeline
bash scripts/run_all.sh --dry-run         # no mutations
python3 scripts/health_check.py --product genviral --days 7
python3 scripts/auto_optimize.py --product genviral --dry-run
python3 scripts/copy_generator.py --product genviral --count 5
```

### Mode 2: /meta-campaign — Campaign Builder

8-stage workflow: **URL → research → strategy → creatives → upload**

Images generated via **[Genviral Studio API](https://genviral.io)** (`google/nano-banana-2` by default).

```bash
# Full campaign (interactive)
python3 campaign/scripts/orchestrate.py --url https://yourproduct.com --product my-product

# Generate creatives after strategy approval
python3 campaign/scripts/generate_creatives.py --rundir campaign/runs/my-product-2026-03-02/ --all

# Single ad set
python3 campaign/scripts/generate_creatives.py \
  --rundir campaign/runs/my-product-2026-03-02/ \
  --ad-set ad-set-01-comparison

# Use higher quality model
python3 campaign/scripts/generate_creatives.py \
  --rundir campaign/runs/my-product-2026-03-02/ --all --pro

# Upload to Meta
python3 campaign/scripts/upload_to_meta.py \
  --rundir campaign/runs/my-product-2026-03-02/ --product my-product
```

---

## The 8 Stages

| # | Stage | Mode | What happens |
|---|-------|------|--------------|
| 1 | LP Analysis | Auto | Scrapes landing page, extracts brand identity |
| 2 | Deep Interview | Human | 5 strategic questions about your product + audience |
| 3 | Customer Roleplay | Opus sub-agent | AI becomes the ideal buyer — writes first-person pain, language, fears |
| 4 | Market Research | Opus sub-agent (parallel) | Reddit + forum language mining, competitor review patterns |
| 5 | Competitor Analysis | Auto | Meta Ad Library patterns |
| 6 | Campaign Strategy | **Approval gate** | 4-5 scored angles + ad set architecture |
| 7 | Creative Generation | **Approval gate** | Images via Genviral Studio + copy per ad set |
| 8 | Upload | **Approval gate** | Upload to Meta Ads Manager, all ads paused by default |

---

## Ad Creative Formats (Stage 7)

8 formats generated per ad set via Genviral's AI image models:

| Format | File | Best for |
|--------|------|----------|
| Comparison table | `image-01-comparison.png` | Tool consolidation, pricing angles |
| Apple Notes style | `image-02-apple-notes.png` | Tips, insider knowledge |
| Quote card | `image-03-quotes.png` | Testimonials, social proof |
| Handwriting | `image-04-handwriting.png` | Founder voice, contrarian takes |
| Notification mockup | `image-05-notification.png` | Automation wins, "while you slept" |
| iMessage thread | `image-06-imessage.png` | Conversation hooks |
| Stats wall | `image-07-stats.png` | Credibility, numbers |
| Before/after | `image-08-before-after.png` | Transformation angles |

---

## Setup

### 1. Meta Graph API token

```bash
cp config.example.yaml config.yaml
# Edit config.yaml — add your access_token and product details
```

Get a token: `business.facebook.com → Settings → System Users → Generate Token`
Required permissions: `ads_management`, `ads_read`, `pages_manage_ads`, `business_management`

### 2. Genviral API key (for image generation)

```bash
export GENVIRAL_API_KEY="your_key_here"
```

Get a key at [genviral.io](https://genviral.io). Uses Studio credits.
Models: `google/nano-banana-2` (default, 1 credit) · `google/nano-banana-pro` (2 credits, `--pro` flag)

### 3. Install deps

```bash
pip3 install pyyaml
```

### 4. Test

```bash
python3 scripts/health_check.py --product my-product
python3 campaign/scripts/lp_analyzer.py --url https://yourproduct.com --output /tmp/test/
python3 campaign/scripts/generate_creatives.py --rundir /tmp/test/ --ad-set ad-set-01 --dry-run
```

---

## File Structure

```
meta-ads-skill/
  SKILL.md                      ← This file (OpenClaw skill descriptor)
  config.example.yaml           ← Template — copy to config.yaml (gitignored)
  config.yaml                   ← YOUR config (gitignored, never commit)

  scripts/                      ← Daily ops
    meta_api.py                 ← Meta Graph API wrapper
    health_check.py             ← Campaign health (5 key questions)
    auto_optimize.py            ← Auto-pause bleeders, scale winners
    copy_generator.py           ← Generate copy variations from top performers
    ad_uploader.py              ← Upload ads to Meta
    morning_brief.py            ← Compile + send morning brief
    run_all.sh                  ← Full pipeline runner

  campaign/                     ← /meta-campaign builder
    scripts/
      orchestrate.py            ← Main entry point
      lp_analyzer.py            ← Stage 1: LP scraping + brand extraction
      ad_library.py             ← Stage 5: Meta Ad Library research
      generate_creatives.py     ← Stage 7: Image gen via Genviral Studio
      upload_to_meta.py         ← Stage 8: Upload creatives to Meta
    references/
      stage-prompts.md          ← Opus sub-agent prompts (stages 3+4)
      creative-formats.md       ← Image format templates + copy.md template
      genviral-config.md        ← Example product config (customize for yours)

  campaign/runs/                ← YOUR campaign output (gitignored)
  data/                         ← YOUR campaign data/history (gitignored)
```

---

## Keeping Your Local Copy in Sync

This repo uses a **public code / private data** split. Your campaign runs and config are gitignored and stay local.

```bash
# Pull latest skill updates without touching your data
git pull origin main

# Your campaign/runs/, data/, and config.yaml are safe — they're gitignored
```

---

## Related

- [genviral-skill](https://github.com/fdarkaou/genviral-skill) — full Genviral Partner API skill (scheduling, analytics, content pipeline, Studio image/video gen)
- [Genviral](https://genviral.io) — the platform powering image generation in Stage 7
- [OpenClaw](https://openclaw.ai) — the agent runtime this skill is built for
