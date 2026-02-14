# Genviral Skill

An [OpenClaw](https://openclaw.ai) skill for the [Genviral](https://genviral.io) Partner API.

It generates slideshows, posts them to TikTok/Instagram, tracks what performs, and adjusts its strategy based on real data. Every cycle makes the next one better.

## How It Works

The skill runs a closed loop:

1. **Generate** slideshows from a prompt + image pack
2. **Review** each slide visually before anything gets posted
3. **Post** to connected accounts (TikTok, Instagram, whatever Genviral supports)
4. **Track** performance through analytics endpoints
5. **Learn** what hooks, formats, and timing actually work
6. **Adapt** strategy weights, retire underperformers, double down on winners

It keeps a performance log, distills insights, and rewrites its own strategy over time. The longer it runs, the better it gets.

## Quick Start

```bash
# Set your API key
export GENVIRAL_API_KEY="your_public_id.your_secret"

# See what accounts you have
./scripts/genviral.sh accounts

# Generate a slideshow
./scripts/genviral.sh generate --prompt "5 morning habits that changed my life" --pack-id PACK_ID

# Render and post it
./scripts/genviral.sh render --id SLIDESHOW_ID
./scripts/genviral.sh create-post --caption "Caption here" --media-type slideshow --media-urls "url1,url2,..." --accounts ACCOUNT_ID

# Check how it performed
./scripts/genviral.sh analytics-summary --range 30d
```

## Installation

Clone into your OpenClaw skills directory:

```bash
cd /path/to/your/workspace/agent/skills
git clone https://github.com/fdarkaou/genviral-skill.git genviral
```

Requires: `bash` 4+, `curl`, `jq`, and a [Genviral](https://genviral.io) account with Partner API access.

## What's Inside

```
genviral/
  SKILL.md              # Full agent instructions (start here)
  scripts/genviral.sh   # 42+ commands wrapping every API endpoint
  config.yaml           # Configuration
  setup.md              # 3-step onboarding

  context/              # Product and brand context (agent fills these in)
  hooks/                # Hook formulas + growing library of tested hooks
  content/              # Scratchpad, calendar, drafts
  performance/          # Post log, insights, weekly reviews
  prompts/              # Slideshow and hook prompt templates
```

## Commands

| Category | What |
|----------|------|
| **Accounts** | List connected accounts, upload files |
| **Slideshows** | Generate, render, review, update, regenerate slides, duplicate, delete |
| **Posts** | Create, update, retry failed, list, delete |
| **Packs** | CRUD for image packs + image management |
| **Templates** | CRUD for slideshow templates, convert from existing slideshows |
| **Analytics** | Summary stats, post metrics, target management, refresh tracking, workspace suggestions |

`genviral.sh help` for the full list.

## The Self-Improving Part

The skill doesn't just post content. It builds a feedback loop:

- **Hook formulas** have weights. High performers get used more, duds get retired.
- **Performance log** tracks every post with 24h/48h/7d metrics.
- **Weekly reviews** distill patterns into actionable insights.
- **Strategy adapts** automatically based on what the data says.

Even without API analytics, the agent tracks its own output and learns from manual feedback. With analytics endpoints, it closes the loop entirely.

## Links

- [Genviral](https://genviral.io)
- [OpenClaw](https://openclaw.ai)
- [Partner API docs](https://genviral.io/docs)

## License

MIT
