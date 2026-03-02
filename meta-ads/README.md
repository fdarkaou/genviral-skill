# meta-ads-skill

An [OpenClaw](https://openclaw.ai) skill for autonomous Meta (Facebook/Instagram) Ads management and AI-powered campaign building.

> **Companion skill:** [genviral-skill](https://github.com/fdarkaou/genviral-skill) — image generation in Stage 7 uses the [Genviral Studio API](https://genviral.io).

---

## What it does

Two modes in one skill:

### 1. Daily Ops
Set it and forget it. Runs every morning:
- Health check — 5 key campaign questions
- Auto-pause ad sets bleeding over 2.5x target CPA for 48h+
- Auto-scale winners under 80% target CPA
- Generate copy variations from your top performers
- Upload new ads (paused by default)
- Deliver a morning brief to Telegram

### 2. /meta-campaign — Campaign Builder
Give it a URL. Get upload-ready ad creatives in return.

Inspired by [Gael Breton's workflow](https://x.com/GaelBreton) — £3K spend → $19K return, every ad built by AI in 30 minutes.

**The 8 stages:**

| # | Stage | Mode | What happens |
|---|-------|------|--------------|
| 1 | LP Analysis | Auto | Scrapes your landing page, extracts brand identity |
| 2 | Deep Interview | Human | 5 strategic questions about your product + audience |
| 3 | Customer Roleplay | Opus sub-agent | AI becomes your ideal buyer — writes first-person pain, language, fears |
| 4 | Market Research | Opus sub-agent (parallel) | Reddit + forum mining, real customer language |
| 5 | Competitor Analysis | Auto | Meta Ad Library pattern extraction |
| 6 | Campaign Strategy | **Approval gate** | 4-5 scored angles + ad set architecture |
| 7 | Creative Generation | **Approval gate** | Images via Genviral Studio + copy per ad set |
| 8 | Upload | **Approval gate** | Push to Meta Ads Manager (all paused, you activate) |

**8 ad creative formats generated per ad set:**
- Comparison table (your stack vs the tool)
- Apple Notes style
- Quote / testimonial card
- Handwriting / founder voice
- Notification mockup
- iMessage thread
- Stats wall
- Before / after

---

## Setup

### Requirements
- Python 3.8+
- `pyyaml`: `pip3 install pyyaml`
- A Meta Ads account with a System User token
- A [Genviral](https://genviral.io) account (for image generation)

### 1. Configure Meta

```bash
cp config.example.yaml config.yaml
```

Edit `config.yaml`:
- `access_token` — Meta Graph API System User token
  - Get it: `business.facebook.com → Settings → System Users → Generate Token`
  - Permissions needed: `ads_management`, `ads_read`, `pages_manage_ads`, `business_management`
- Add your product(s) with ad account ID, page ID, pixel ID

### 2. Configure Genviral (image generation)

```bash
export GENVIRAL_API_KEY="your_genviral_api_key"
```

Get your key at [genviral.io](https://genviral.io). Image generation uses Studio credits.

Models available:
- `google/nano-banana-2` — default (1 credit, fast)
- `google/nano-banana-pro` — higher quality (`--pro` flag, 2 credits)

---

## Usage

### Daily ops

```bash
# Full pipeline (health + optimize + copy + brief)
bash scripts/run_all.sh my-product

# Individual steps
python3 scripts/health_check.py --product my-product --days 7
python3 scripts/auto_optimize.py --product my-product --dry-run
python3 scripts/copy_generator.py --product my-product --count 5
```

### Campaign builder

```bash
# Start a new campaign
python3 campaign/scripts/orchestrate.py --url https://yourproduct.com --product my-product

# After Stage 6 approval — generate all creatives
python3 campaign/scripts/generate_creatives.py \
  --rundir campaign/runs/my-product-2026-03-02/ --all

# Single ad set
python3 campaign/scripts/generate_creatives.py \
  --rundir campaign/runs/my-product-2026-03-02/ \
  --ad-set ad-set-01-comparison

# Specific formats only
python3 campaign/scripts/generate_creatives.py \
  --rundir campaign/runs/my-product-2026-03-02/ --all \
  --formats comparison,stats,quotes

# Upload to Meta (all ads created as PAUSED)
python3 campaign/scripts/upload_to_meta.py \
  --rundir campaign/runs/my-product-2026-03-02/ --product my-product
```

---

## File structure

```
meta-ads-skill/
  SKILL.md                      ← OpenClaw skill descriptor
  README.md                     ← This file
  config.example.yaml           ← Template — copy to config.yaml
  config.yaml                   ← Your config (gitignored — never commit)

  scripts/                      ← Daily ops
    meta_api.py                 ← Meta Graph API wrapper (v21.0)
    health_check.py             ← 5 key campaign health questions
    auto_optimize.py            ← Auto-pause bleeders, scale winners
    copy_generator.py           ← Generate copy from top performers
    ad_uploader.py              ← Upload ads to Meta
    morning_brief.py            ← Compile + send Telegram brief
    run_all.sh                  ← Full pipeline runner

  campaign/                     ← /meta-campaign builder
    scripts/
      orchestrate.py            ← Main entry point
      lp_analyzer.py            ← Stage 1: LP scraping + brand extraction
      ad_library.py             ← Stage 5: Meta Ad Library research
      generate_creatives.py     ← Stage 7: Image gen via Genviral Studio
      upload_to_meta.py         ← Stage 8: Upload creatives
    references/
      stage-prompts.md          ← Opus sub-agent prompts (stages 3+4)
      creative-formats.md       ← Image format templates
      genviral-config.md        ← Example product config

  campaign/runs/                ← Your campaign output (gitignored)
  data/                         ← Your campaign history (gitignored)
```

---

## Keeping your local copy in sync

Public code and private data are separated by `.gitignore`. Pull updates safely:

```bash
git pull origin main
# config.yaml, campaign/runs/, data/ — all untouched
```

---

## Auto-optimizer thresholds

| Signal | Threshold | Action |
|--------|-----------|--------|
| Frequency | ≥ 3.5 | Auto-pause ad set |
| CPA vs target | > 2.5x for 48h | Auto-pause ad set |
| CPA vs target | < 80% of target | Recommend scaling |
| Min spend | < $10 | Skip — not enough data |

---

## Related

- [genviral-skill](https://github.com/fdarkaou/genviral-skill) — full Genviral Partner API skill
- [Genviral](https://genviral.io) — powers image generation in Stage 7
- [OpenClaw](https://openclaw.ai) — the agent runtime this runs on

---

## License

MIT
