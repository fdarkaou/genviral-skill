# genviral Skill

An [OpenClaw](https://openclaw.ai) skill for automating content creation with the [genviral](https://genviral.io) Partner API. Built for AI agents.

Generate slideshows, manage image packs, post to TikTok/Instagram, and run an autonomous content pipeline that learns and improves over time.

## What It Does

- **32 CLI commands** wrapping every Partner API endpoint
- **Full content pipeline**: generate slideshows from prompts, render to images, review, iterate, post
- **Multi-platform**: TikTok, Instagram, any platform genviral supports
- **Self-improving**: built-in learning loop that tracks performance and optimizes strategy
- **Agent-first**: SKILL.md is written for AI agents to read and immediately understand

## Quick Start

```bash
# 1. Set your API key
export GENVIRAL_API_KEY="your_public_id.your_secret"

# 2. List your connected accounts
./scripts/genviral.sh accounts

# 3. List available image packs
./scripts/genviral.sh list-packs

# 4. Generate a slideshow
./scripts/genviral.sh generate --prompt "5 morning habits that changed my life" --pack-id PACK_ID

# 5. Render it
./scripts/genviral.sh render --id SLIDESHOW_ID

# 6. Post it
./scripts/genviral.sh create-post --caption "Caption here" --media-type slideshow --media-urls "url1,url2,..." --accounts ACCOUNT_ID
```

## Installation

### OpenClaw

Copy this skill into your OpenClaw skills directory:

```bash
cp -r genviral-skill /path/to/your/workspace/agent/skills/genviral
```

Or clone directly:

```bash
cd /path/to/your/workspace/agent/skills
git clone https://github.com/fdarkaou/genviral-skill.git genviral
```

### Requirements

- `bash` 4+
- `curl`
- `jq`
- A genviral account with Partner API access
- An API key from https://www.genviral.io (API Keys page)

## For AI Agents

Read `SKILL.md`. It contains everything: command reference, content strategy, hook formulas, the self-improvement loop, platform best practices, and quality checklists.

The skill is designed so an agent can:
1. Read SKILL.md once
2. Set up the product context files
3. Start generating, posting, and iterating autonomously

## File Structure

```
genviral/
  SKILL.md              # Complete agent instructions (start here)
  README.md             # This file (human overview)
  setup.md              # 3-step onboarding guide
  config.yaml           # Configuration template

  scripts/
    genviral.sh         # CLI wrapper (32 commands, all Partner API endpoints)

  context/              # Product and brand context (agent-populated)
    product.md          # What the product does, who it serves
    brand-voice.md      # Tone, style, rules
    niche-research.md   # Platform research

  hooks/                # Hook system for content creation
    formulas.md         # 5 hook formula patterns with psychology
    library.json        # Hook instances (grows over time)

  content/              # Content planning
    scratchpad.md       # Ideas and drafts in progress
    calendar.json       # Scheduled content plan

  performance/          # Learning and optimization
    log.json            # Post performance tracking
    insights.md         # Distilled learnings
    weekly-review.md    # Weekly review template

  prompts/              # Prompt templates for API calls
    slideshow.md        # 6 slideshow prompt templates
    hooks.md            # Hook brainstorming prompts
```

## Commands

| Category | Commands |
|----------|----------|
| **Accounts** | `accounts`, `upload`, `list-files` |
| **Posts** | `create-post`, `update-post`, `retry-posts`, `list-posts`, `get-post`, `delete-posts` |
| **Slideshows** | `generate`, `render`, `review`, `update`, `regenerate-slide`, `duplicate`, `delete`, `list-slideshows` |
| **Packs** | `list-packs`, `get-pack`, `create-pack`, `update-pack`, `delete-pack`, `add-pack-image`, `delete-pack-image` |
| **Templates** | `list-templates`, `get-template`, `create-template`, `update-template`, `delete-template`, `create-template-from-slideshow` |
| **Pipeline** | `full-pipeline`, `post-draft` |

Run `genviral.sh help` for full usage.

## The Learning Loop

The skill tracks everything it posts and uses the data to improve:

1. **Generate** content using hook formulas and product context
2. **Review** each slide visually before posting
3. **Post** to target accounts
4. **Track** performance at 24h, 48h, 7d intervals
5. **Analyze** what worked and what didn't
6. **Adapt** strategy weights, retire underperformers, double down on winners

Even without analytics API access, the agent tracks its own output and learns from manual feedback.

## API Coverage

This skill wraps genviral's Partner API v1 (`https://www.genviral.io/api/partner/v1`). Full endpoint coverage:

- Accounts (GET)
- File uploads (POST presigned + PUT)
- Posts (CRUD + retry + bulk delete)
- Slideshows (generate, render, update, regenerate slide, duplicate, delete, list)
- Image packs (CRUD + image management)
- Templates (CRUD + convert from slideshow)

## License

MIT
