# Genviral Skill

An agent skill for the [Genviral](https://genviral.io) Partner API — works with any coding agent that reads `SKILL.md` and can run shell commands.

Compatible with [Claude Code](https://docs.anthropic.com/en/docs/claude-code), [Codex](https://openai.com/codex), [Cursor](https://cursor.com), [OpenClaw](https://openclaw.ai), Hermes, and other agent runtimes.

Generates slideshows, posts them across platforms, tracks what performs, and adjusts strategy based on real data. Every cycle makes the next one better.

## Supported Platforms

| Platform | Posting | Analytics | Notes |
|----------|---------|-----------|-------|
| **TikTok** | Yes | Yes | Video and slideshow. BYO or hosted. TikTok settings are top-level `tiktok` on create (BYO only for TikTok-specific fields). |
| **Instagram** | Yes | Yes | Feed/reel (`post_type: post`) or story. Use `settings.instagram` or `settings.instagram-standalone`. |
| **YouTube** | Yes | Yes | Video posts with `settings.youtube` (title, visibility, tags, etc.). |
| **Facebook** | Yes | - | Posts with optional `settings.facebook.url` link attachment. |
| **Pinterest** | Yes | - | Image/slideshow pins; top-level `pinterest.board_id` required (no account default). |
| **LinkedIn** | Yes | - | Posts and image carousels via `settings.linkedin` or `settings.linkedin-page`. |
| **X / Twitter** | Yes | - | Video or text-only (`media: null` when account supports `text_only`). `settings.x` or `settings.twitter`. |
| **Bluesky** | Yes | - | `settings.bluesky: {}` or omit. |

Not every account supports every content type. Run `genviral accounts` and read each account's `capabilities` before posting.

Analytics (performance tracking, post metrics, account insights) is available for TikTok, Instagram, and YouTube only.

For raw `POST /posts` JSON and provider field tables, use the canonical docs — do not rely on skill-local copies of the full API spec:

- [llms.txt](https://docs.genviral.io/llms.txt) — agent doc index
- [Create Post](https://docs.genviral.io/api-reference/create-post) — request body and `settings.*` / `tiktok` / `pinterest` shapes

## How It Works

The skill runs a closed loop:

1. **Generate** slideshows from a prompt + image pack (with deliberate image selection — no random picks)
2. **Review** every slide visually before anything gets posted (hard gate)
3. **Post** to connected accounts across any supported platform
4. **Track** performance through analytics endpoints
5. **Learn** what hooks, formats, and timing actually work
6. **Adapt** strategy weights, retire underperformers, double down on winners

## Quick Start

```bash
# Install the npm CLI (once)
npm install -g @genviral/cli

# Set your API key
export GENVIRAL_API_KEY="your_public_id.your_secret"

# See what accounts you have
genviral accounts

# Pull niche intelligence in one call
genviral trend-brief --keyword "indie hacker" --range 7d --limit 10

# List image packs
genviral list-packs

# Generate a slideshow (always pin images — see docs/api/packs.md)
genviral generate \
  --prompt "5 morning habits that changed my life" \
  --pack-id PACK_ID \
  --slides 5 \
  --slide-config-json '{"total_slides":5,"slide_types":["image_pack","image_pack","image_pack","image_pack","image_pack"],"pinned_images":{"0":"URL_0","1":"URL_1","2":"URL_2","3":"URL_3","4":"URL_4"}}'

# Render and post
genviral render --id SLIDESHOW_ID
genviral create-post \
  --caption "Caption with #hashtags" \
  --media-type slideshow \
  --media-urls "url1,url2,url3,url4,url5" \
  --accounts ACCOUNT_ID

# Copy an existing TikTok slideshow into an editable draft
genviral copy-tiktok-preview --url "https://www.tiktok.com/@creator/photo/7499123456789012345"
genviral copy-tiktok-import \
  --url "https://www.tiktok.com/@creator/photo/7499123456789012345" \
  --preview-id PREVIEW_UUID \
  --pack-id PACK_UUID

# Generate a "similar but new" variation using Studio + NanoBanana
genviral studio-generate-image \
  --model-id "google/nano-banana-2" \
  --image-urls "https://source-slide-url.jpg" \
  --prompt "Create a new original ad image inspired by this slide, aligned with PRODUCT_CONTEXT."

# Check performance
genviral analytics-summary --range 30d
```

Analytics identity rule:
- `analyticsId` is the analytics-row ID (`id` is kept as a legacy alias)
- `platformPostId` is the platform-native post/video ID
- `genviralPostId` is the originating Genviral post ID
- `externalId` is the originating Partner API `external_id`

For BYO TikTok drafts (`post_mode=MEDIA_UPLOAD`), the initial TikTok draft/inbox `publish_id` is not the final public TikTok video ID. Use `genviralPostId` or `externalId` to correlate analytics back to created posts.

For Studio video generation, call `genviral studio-models --mode video`
before relying on speech-specific flags. Today `--speech-text`, `--voice-id`,
and `--audio-url` are only exposed for explicit talking/lipsync models;
prompt-driven models like Sora/Veo are prompt-only, so put any desired dialogue
directly inside `--prompt`.

## Installation

Clone the repo, then install it wherever your agent loads skills from:

| Agent | Typical path |
| --- | --- |
| Claude Code | `~/.claude/skills/` or `.claude/skills/` |
| Codex | `~/.codex/skills/` or `.codex/skills/` |
| Cursor | `~/.cursor/skills/` or `.cursor/skills/` |
| OpenClaw | your workspace `skills/` directory |
| Other (Hermes, custom runners) | your agent's skills directory |

```bash
git clone https://github.com/fdarkaou/genviral-skill.git genviral
```

Point your agent at the `genviral/` folder. `SKILL.md` is the entry point; `docs/` holds the detailed workflows.

Requires: Node.js 20.19+ or 22.12+ and a [Genviral](https://genviral.io) account with Partner API access.

## What's Inside

```
genviral/
  SKILL.md                  # Kernel: agent entry point, routing table, non-negotiable rules
  README.md                 # This file
  setup.md                  # Conversational onboarding guide
  defaults.yaml             # API config and defaults (no secrets here)

  docs/
    api/
      accounts-files.md     # accounts, upload, list-files
      posts.md              # create-post, update-post, retry, list, get, delete
      slideshows.md         # generate/render/update + TikTok copy preview/import + text styles
      packs.md              # pack CRUD + mandatory smart image selection workflow
      templates.md          # template CRUD, create-from-slideshow
      analytics.md          # analytics summary, posts, targets, refresh
      pipeline.md           # full content pipeline, performance loop, CTA testing
      errors.md             # error codes and troubleshooting

  workspace/                # Your instance data — never overwritten by updates
    content/
      scratchpad.md         # Working content plan and drafts
      calendar.json         # Upcoming planned posts
    context/
      product.md            # Product description, value props, target audience
      brand-voice.md        # Tone, style, do's and don'ts
      niche-research.md     # Platform research for the niche
    hooks/
      library.json          # Hook instances with performance data
      formulas.md           # Hook formula patterns and psychology
    performance/
      log.json              # Canonical post record (single source of truth)
      hook-tracker.json     # Hook and CTA tracking with metrics
      insights.md           # Agent learnings from performance data
      weekly-review.md      # Weekly review notes
      competitor-insights.md

  references/
    analytics-loop.md       # Full analytics feedback loop and weekly review process
    competitor-research.md  # How to research competitors

  prompts/
    slideshow.md            # Prompt templates for slideshow generation
    hooks.md                # Prompt templates for hook brainstorming

  scripts/
    genviral.sh             # Optional wrapper that delegates to the npm CLI and sets GENVIRAL_CONFIG
    update-skill.sh         # Self-updater (keeps skill files current, never touches workspace/)
```

## Commands

| Category | Commands |
|----------|----------|
| **Accounts & Files** | `accounts`, `upload`, `list-files` |
| **Influencers** | `list-influencers`, `get-influencer` |
| **Posts** | `create-post`, `update-post`, `retry-posts`, `list-posts`, `get-post`, `delete-posts` |
| **Slideshows** | `generate`, `render`, `review`, `update`, `regenerate-slide`, `duplicate`, `delete`, `list-slideshows`, `copy-tiktok-preview`, `copy-tiktok-import` |
| **Packs** | `list-packs`, `get-pack`, `create-pack`, `update-pack`, `delete-pack`, `add-pack-image`, `delete-pack-image` |
| **Templates** | `list-templates`, `get-template`, `create-template`, `update-template`, `delete-template`, `create-template-from-slideshow` |
| **Analytics & Trends** | `analytics-summary`, `analytics-posts`, `analytics-targets`, `analytics-target-create`, `analytics-target-refresh`, `analytics-refresh`, `analytics-workspace-suggestions`, `trend-brief` |

The `@genviral/cli` npm package publishes the `genviral` and `genviral-cli` binaries. Use `genviral help` for the full command list.

From the skill directory, `./scripts/genviral.sh <command> [options]` is available only as a convenience wrapper. It does not implement commands itself; it forwards to the npm `genviral` binary and points `GENVIRAL_CONFIG` at this skill's `defaults.yaml` when that variable is not already set.

## Auto-Updates

The skill can update itself without touching your data:

```bash
bash scripts/update-skill.sh           # check + apply if updates available
bash scripts/update-skill.sh --dry-run # preview only, no changes
bash scripts/update-skill.sh --force   # force re-apply even if already current
```

**Skill-owned (updated automatically):** `README.md`, `SKILL.md`, `scripts/`, `docs/` (all subdirs)

**User-owned (never touched):** `workspace/` — your product context, hooks, performance logs, and content data are always preserved.

## The Self-Improving Loop

The skill builds a feedback loop over time:

- **After every post:** log to `workspace/performance/log.json` + tag the hook in `hook-tracker.json`
- **At 48h and 7d:** pull analytics, fill in real metrics per post
- **Every Monday:** review last 7 days, categorize hooks (double down / keep rotating / testing / dropped), update strategy
- **Ongoing:** high performers get used more, dead angles get retired

After 4+ weeks the patterns become clear enough to make data-driven decisions about hooks, CTA types, and post timing.

## Included: Meta Ads Skill

This repo includes the [meta-ads-skill](https://github.com/fdarkaou/meta-ads-skill) in the `meta-ads/` directory — an autonomous Meta (Facebook/Instagram) Ads manager and 8-stage AI campaign builder.

It uses Genviral's Studio API for ad creative generation. See [`meta-ads/README.md`](meta-ads/README.md) for setup.

Also available standalone: [fdarkaou/meta-ads-skill](https://github.com/fdarkaou/meta-ads-skill)

## Links

- [Genviral](https://genviral.io)
- [Partner API docs](https://docs.genviral.io) — canonical REST reference alongside `@genviral/cli`
- [llms.txt](https://docs.genviral.io/llms.txt) — full doc index for agents
- [Create Post](https://docs.genviral.io/api-reference/create-post) — `POST /posts` payload reference
- [meta-ads-skill](https://github.com/fdarkaou/meta-ads-skill) — standalone repo

## License

MIT
