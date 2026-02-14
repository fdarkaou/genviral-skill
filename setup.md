# Quick Setup Guide

Get up and running with genviral in 3 steps. This skill works for TikTok, Instagram, or any platform genviral supports.

## Step 1: Set Your API Key

Get your API key from https://www.genviral.io (API Keys page), then set it:

```bash
export GENVIRAL_API_KEY="your_public_id.your_secret"
```

Or add it to `~/.config/env/global.env` to persist across sessions.

## Step 2: Find Your Accounts

List all your connected accounts (BYO + hosted):

```bash
genviral.sh accounts
```

Copy the account IDs you want to use. You can target multiple accounts per post.

## Step 3: Pick a Default Image Pack

List available image packs:

```bash
genviral.sh list-packs
```

Pick one that fits your niche and copy its ID.

## Configure Defaults

Edit `config.yaml` and set:

```yaml
content:
  default_pack_id: "PASTE_PACK_ID_HERE"

posting:
  default_account_ids: "ACCOUNT_ID_1,ACCOUNT_ID_2"  # comma-separated
```

Save the file.

## Test It

Run a quick test:

```bash
genviral.sh generate --prompt "Test slideshow: 3 productivity tips" --pack-id YOUR_PACK_ID
```

If you get a slideshow ID back, you are ready to go!

## What's Next?

Now you can:

- **Create video posts:** `genviral.sh create-post --caption "..." --media-type video --media-url "https://..." --accounts "id1,id2"`
- **Create slideshow posts:** Generate a slideshow, render it, then post it
- **Upload files:** `genviral.sh upload --file video.mp4 --content-type video/mp4`
- **Full pipeline:** `genviral.sh full-pipeline --prompt "..." --caption "..."`

For TikTok/Instagram strategy, hook formulas, and content planning, read `SKILL.md`.

## Optional: Product Context & Hooks

The agent can help you create product context files and hook libraries for automated content creation. Just ask!

Files the agent can create for you:
- `context/product.md` - Your product description and value props
- `context/brand-voice.md` - Your tone and style guide
- `hooks/library.json` - Pre-generated hook library for your niche
- `content/calendar.json` - Planned content schedule

These are optional but make ongoing content creation way easier.
