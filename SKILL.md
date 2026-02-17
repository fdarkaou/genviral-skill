---
name: genviral
description: Complete genviral Partner API automation. Create and schedule posts (video + slideshow) across TikTok, Instagram, and any supported platform. Includes slideshow generation, file uploads, template/pack management, analytics, and full content pipeline automation.
homepage: https://github.com/fdarkaou/genviral-skill
metadata:
  openclaw:
    emoji: "🎬"
    requires:
      bins: ["curl", "jq", "bash"]
---

# genviral Partner API Skill

> **TL;DR for agents:** This skill wraps genviral's Partner API into 42+ bash commands covering all documented endpoints. Core workflow: `get-pack` (fetch images + AI metadata) > **analyze images** (use metadata descriptions/keywords + vision tool for readability) > `generate` with `pinned_images` (assign images to slides) > `render` (produce images) > **visually review rendered slides** (hard gate) > `create-post` (publish). Auth via `GENVIRAL_API_KEY` env var. Config in `defaults.yaml`. **Critical: use `pinned_images` in `slide_config` to control which image goes on which slide. Pack images include AI metadata (description, keywords) for smarter selection. Use vision tools for readability assessment of rendered output.** Product context in `context/`. Hook library in `hooks/`. Track results in `performance/`.

Complete automation for genviral's Partner API. Create video posts, AI-generated slideshows, manage templates and image packs, track analytics, and schedule content across any platform genviral supports (TikTok, Instagram, etc.).

This skill provides a full CLI wrapper around the Partner API with commands for every endpoint, plus higher-level workflows for content creation, performance tracking, and strategy optimization.

## What This Skill Does

- **Multi-Platform Posting:** Create posts for TikTok, Instagram, or any connected account (video OR slideshow, multiple accounts per post)
- **File Management:** Upload videos/images to genviral's CDN with presigned URL flow
- **AI Slideshow Generation:** Generate photo carousels from prompts, render them to images
- **Template System:** Create reusable slideshow templates, convert winning slideshows to templates
- **Pack Management:** Manage image packs (backgrounds for slideshows)
- **Analytics:** Get summary KPIs, post-level metrics, manage tracked accounts, trigger refreshes
- **Content Pipeline:** Full automation from prompt to posted draft
- **Performance Tracking:** Log posts, track metrics, learn from results
- **Hook Library:** Maintain and evolve a library of proven content hooks

## How It Works

The core workflow is:

1. **Generate or upload media** (slideshow from prompt, or upload your own video/images)
2. **Create a post** targeting one or more accounts
3. **Schedule or publish** (immediately or at a specific time)
4. **Track performance** via analytics endpoints
5. **Learn and optimize** (promote winning hooks, retire underperformers)

The skill handles the full automation. For TikTok slideshow posts, it can optionally save as drafts so you add trending audio before publishing (music selection requires human judgment for best results).

## First-Time Setup

If this is a fresh install, read `setup.md` and walk your human through onboarding conversationally:

1. Set API key and verify it works
2. List accounts and pick which ones to post to
3. Discuss image strategy (existing packs, create new ones, generate per post, or mix)
4. Optionally set up product context and brand voice together

No hardcoded defaults needed. The agent should ask the user what they prefer and adapt. Everything done through this skill shows up in the Genviral dashboard, so the user always has full visibility and control.

All configuration lives in `defaults.yaml`. Secrets are loaded from environment variables.

## File Structure

```
genviral/
  SKILL.md                  # This file (comprehensive API reference + strategy)
  setup.md                  # Onboarding guide (conversational, 5 phases)
  defaults.yaml               # API config, defaults, schedule settings

  context/
    product.md              # Product description, value props, target audience
    brand-voice.md          # Tone, style, do's and don'ts
    niche-research.md       # Platform research for the niche

  hooks/
    library.json            # Hook instances (grows over time, tracks performance)
    formulas.md             # Hook formula patterns and psychology

  content/
    scratchpad.md           # Working content plan, ideas, drafts in progress
    calendar.json           # Content calendar (upcoming planned posts)

  performance/
    log.json                # Post performance tracking (views, likes, shares)
    hook-tracker.json       # Hook and CTA tracking with metrics (the feedback loop)
    insights.md             # Agent's learnings from performance data
    weekly-review.md        # Weekly review template and process
    competitor-insights.md  # Findings from competitor research (generated per product)

  references/
    competitor-research.md  # How to research competitors before creating content
    analytics-loop.md       # Full analytics feedback loop process and weekly review

  scripts/
    genviral.sh             # Main API wrapper script (all commands)

  prompts/
    slideshow.md            # Prompt templates for slideshow generation
    hooks.md                # Prompt templates for hook brainstorming
```

## Script Reference

All commands use the wrapper script:

```bash
/path/to/genviral/scripts/genviral.sh <command> [options]
```

The script requires `GENVIRAL_API_KEY` as an environment variable. It loads defaults from `defaults.yaml`.

---

## Account & File Commands

### accounts
List connected BYO and hosted accounts in your scope. Use this to discover account IDs for posting.

```bash
genviral.sh accounts
genviral.sh accounts --json
```

Returns:
- Account ID (use in --accounts for create-post)
- Platform (tiktok, instagram, etc.)
- Type (byo or hosted)
- Username, display name, status

### upload
Upload a file to genviral's CDN using the presigned URL flow. Returns a CDN URL you can use in posts.

```bash
genviral.sh upload --file video.mp4 --content-type video/mp4
genviral.sh upload --file slide1.jpg --content-type image/jpeg --filename "slide1.jpg"
```

Supported content types:
- Videos: `video/mp4`, `video/quicktime`, `video/x-msvideo`, `video/webm`, `video/x-m4v`
- Images: `image/jpeg`, `image/png`, `image/gif`, `image/webp`, `image/heic`, `image/heif`

Returns the CDN URL (use in create-post).

### list-files
List files uploaded via the Partner API.

```bash
genviral.sh list-files
genviral.sh list-files --type video --limit 20 --offset 0
genviral.sh list-files --type image --context ai-studio,media-upload
genviral.sh list-files --context all  # include all contexts
genviral.sh list-files --json
```

`--type` accepts: `image` or `video`.

---

## Post Commands

### create-post
Create a post (video OR slideshow) targeting one or more accounts. This is the core posting command.

**Video post:**

```bash
genviral.sh create-post \
  --caption "Your caption with #hashtags" \
  --media-type video \
  --media-url "https://cdn.genviral.com/your-video.mp4" \
  --accounts "account_id_1,account_id_2" \
  --scheduled-at "2025-03-01T15:00:00Z"
```

**Slideshow post:**

```bash
genviral.sh create-post \
  --caption "Your caption" \
  --media-type slideshow \
  --media-urls "url1,url2,url3,url4,url5,url6" \
  --accounts "account_id_1" \
  --music-url "https://www.tiktok.com/@user/video/1234567890"
```

**TikTok-specific settings** (only when ALL accounts are TikTok BYO):

```bash
genviral.sh create-post \
  --caption "Caption" \
  --media-type slideshow \
  --media-urls "url1,url2,url3,url4,url5,url6" \
  --accounts "tiktok_account_id" \
  --tiktok-title "Optional title" \
  --tiktok-description "Optional description" \
  --tiktok-post-mode "MEDIA_UPLOAD" \
  --tiktok-privacy "SELF_ONLY" \
  --tiktok-disable-comment \
  --tiktok-disable-duet \
  --tiktok-disable-stitch \
  --auto-add-music true \
  --is-commercial false \
  --is-branded-content false \
  --user-consent true \
  --is-your-brand false
```

Boolean TikTok toggles support both forms:
- `--tiktok-disable-comment` (sets `true`)
- `--tiktok-disable-comment false` (explicit false)

Same behavior applies to: `--tiktok-disable-duet`, `--tiktok-disable-stitch`, `--auto-add-music`, `--is-commercial`, `--is-branded-content`, `--user-consent`, `--is-your-brand`.

TikTok `post_mode` options:
- `DIRECT_POST` - publish immediately (default)
- `MEDIA_UPLOAD` - save to TikTok drafts inbox (only supported for slideshow media)

TikTok `privacy_level` options:
- `PUBLIC_TO_EVERYONE` (default)
- `MUTUAL_FOLLOW_FRIENDS`
- `FOLLOWER_OF_CREATOR`
- `SELF_ONLY` (draft mode)

**Scheduling:**

- Omit `--scheduled-at` or set it within 30 seconds of now: post is queued for immediate publish (status: `pending`)
- Provide future ISO timestamp: post is scheduled (status: `scheduled`)
- `--scheduled-at` must be ISO 8601 with timezone offset (example: `2026-02-14T19:47:00Z`)

`--music-url` must point to a TikTok URL.

**Multi-account posting:**

You can target up to 10 accounts per post. Mix TikTok, Instagram, etc. Music is only supported when ALL accounts support it (currently TikTok only). TikTok-specific settings only work when ALL accounts are TikTok BYO.

### update-post
Update an existing post (only editable if status is draft, pending, scheduled, retry, or failed).

```bash
genviral.sh update-post \
  --id POST_ID \
  --caption "Updated caption" \
  --media-type video \
  --media-url "https://new-video.mp4" \
  --accounts "new_account_id_1,new_account_id_2" \
  --scheduled-at "2025-03-15T18:00:00Z"
```

Clear operations:
- Remove music: `--music-url null`
- Clear scheduled time: `--clear-scheduled-at`
- Clear all TikTok settings: `--clear-tiktok`

Validation notes:
- `--scheduled-at` must be ISO 8601 with timezone offset (example: `2026-02-14T19:47:00Z`)
- `--music-url` must be a TikTok URL (unless using `null` to clear)
- TikTok boolean toggles support both flag form (`--auto-add-music`) and explicit values (`--auto-add-music false`)

### retry-posts
Retry failed or partial posts.

```bash
genviral.sh retry-posts --post-ids "post_id_1,post_id_2"
genviral.sh retry-posts --post-ids "post_id_1" --account-ids "account_id_1"
```

Limits:
- `post_ids`: 1-20 IDs
- `account_ids`: 1-10 IDs

### list-posts
List posts with optional filters.

```bash
genviral.sh list-posts
genviral.sh list-posts --status scheduled --limit 20
genviral.sh list-posts --since "2025-02-01T00:00:00Z" --until "2025-02-28T23:59:59Z"
genviral.sh list-posts --json
```

`--since` and `--until` must be ISO 8601 datetimes with timezone offset.

Status filters: `draft`, `pending`, `scheduled`, `posted`, `failed`, `partial`, `retry`

### get-post
Get details for a specific post.

```bash
genviral.sh get-post --id POST_ID
```

### delete-posts (alias: `delete-post`)
Bulk delete posts by IDs.

```bash
genviral.sh delete-posts --ids "post_id_1,post_id_2,post_id_3"
# equivalent option name
genviral.sh delete-posts --post-ids "post_id_1,post_id_2,post_id_3"
# command alias
genviral.sh delete-post --ids "post_id_1,post_id_2"
```

Limit: up to 50 IDs per request.

Returns structured delete results including:
- `deletedIds`
- `blockedStatuses` (posts that can't be deleted due to status)
- `skipped`
- `errors`

---

## Slideshow Commands

### generate | generate-slideshow
Generate a slideshow from a prompt (AI mode), or build it manually with explicit slide config (`--skip-ai`).

```bash
# AI mode (default)
genviral.sh generate \
  --prompt "Your hook and content prompt" \
  --pack-id PACK_ID \
  --slides 5 \
  --type educational \
  --aspect-ratio 4:5 \
  --style tiktok \
  --language en \
  --font-size small \
  --text-width narrow \
  --product-id PRODUCT_ID

# Manual/mixed mode with slide_config
genviral.sh generate \
  --skip-ai \
  --slide-config-file slide-config.json

# Pass slide_config inline
genviral.sh generate \
  --skip-ai \
  --slide-config-json '{"total_slides":2,"slide_types":["image_pack","custom_image"],...}'
```

Options (`POST /slideshows/generate`):
- `--prompt` -> `prompt` (required unless `--skip-ai true` or `--product-id` is provided)
- `--product-id` -> `product_id` (UUID, optional)
- `--pack-id` -> `pack_id` (UUID, optional global image pack)
- `--slides` -> `slide_count` (`1-10`, default `5`)
- `--type` -> `slideshow_type` (`educational` or `personal`)
- `--aspect-ratio` -> `aspect_ratio` (`9:16`, `4:5`, `1:1`)
- `--language` -> `language` (2-32 chars, for example `en`, `es`, `fr`)
- `--style` / `--text-preset` -> `advanced_settings.text_preset` (string)
- `--font-size` -> `advanced_settings.font_size` (`default` or `small`)
- `--text-width` -> `advanced_settings.text_width` (`default` or `narrow`)
- `--skip-ai` -> `skip_ai` (bool)
- `--slide-config-json` / `--slide-config` -> `slide_config` (inline JSON)
- `--slide-config-file` -> `slide_config` (JSON file)

`slide_config` supports:
- `total_slides` (1-10)
- `slide_types` (exact length = `total_slides`, each `image_pack` or `custom_image`)
- `custom_images` map: `{"index": {"image_url", "image_id", "image_name?"}}` (required for each `custom_image` slide)
- `pinned_images` map: `{"index": "https://..."}`
- `slide_texts` map: `{"index": "text"}`
- `slide_text_elements` map: `{"index": [{"content", "x", "y", "id?", "font_size?", "width?"}]}`
- `pack_assignments` map: `{"index": "pack_uuid"}` (only for `image_pack` slides)

Validation rules you must respect:
- All slide-config map keys must be numeric 0-based indices in range.
- `slide_types.length` must equal `total_slides`.
- Every `image_pack` slide must resolve a pack via global `pack_id` or per-slide `pack_assignments[index]`.
- Every `custom_image` slide must have `custom_images[index]`.

### render | render-slideshow
Render a slideshow to images via Remotion.

```bash
genviral.sh render --id SLIDESHOW_ID
```

Returns:
- Updated slideshow with rendered image URLs
- Status: `rendered`

### review | get-slideshow
Get full slideshow details for review. Shows slide text, status, rendered URLs.

```bash
genviral.sh review --id SLIDESHOW_ID
genviral.sh review --id SLIDESHOW_ID --json
genviral.sh get-slideshow --id SLIDESHOW_ID  # alias
```

### update | update-slideshow
Update slideshow fields, settings, or slides. Re-render after updating slides.

```bash
# Update title
genviral.sh update --id SLIDESHOW_ID --title "New Title"

# Update status
genviral.sh update --id SLIDESHOW_ID --status draft

# Update settings
genviral.sh update --id SLIDESHOW_ID --settings-json '{"aspect_ratio":"9:16","advanced_settings":{"text_width":"narrow"}}'

# Update slides (full replacement)
genviral.sh update --id SLIDESHOW_ID --slides '[{"image_url":"...","text_elements":[{"content":"..."}]}]'

# Load slides from file
genviral.sh update --id SLIDESHOW_ID --slides-file slides.json

# Update product_id or clear it
genviral.sh update --id SLIDESHOW_ID --product-id NEW_PRODUCT_ID
genviral.sh update --id SLIDESHOW_ID --clear-product-id
```

Options:
- `--title` - Update title
- `--status` - `draft` or `rendered`
- `--slideshow-type` - `educational` or `personal`
- `--product-id` - Link to product
- `--clear-product-id` - Detach product
- `--settings-json` / `--settings-file` - Partial settings patch (`image_pack_id`, `aspect_ratio`, `slideshow_type`, `advanced_settings`, `pack_assignments`)
- `--slides` / `--slides-file` - Full slides array replacement

### Text Styles, Fonts, and Formatting (Slideshow)

Use this as your source of truth when styling text overlays.

**Global generation controls (`advanced_settings`):**
- `font_size`: `default` or `small`
- `text_width`: `default` (wide) or `narrow`
- `text_preset`: style preset string (see presets below)

**Text presets (renderer-supported):**
- `tiktok` - White text with strong black outline/stroke, optimized for hook readability
- `inverted` - Black text on a white text box (best when the background is busy)
- `shadow` - White text with heavy shadow for separation from background
- `white` - Plain white text, minimal styling
- `black` - Plain black text, minimal styling
- `snapchat` - White text on translucent black background bar (UI/editor supports it)

**Partner API note:** `PATCH /slideshows/{id}` `slides[].text_elements[].style_preset` currently validates: `tiktok`, `inverted`, `shadow`, `white`, `black`.

**Font options available in slideshow editor constants:**
- TikTok Display (default)
- Anton
- Arial
- Bebas Neue
- Bitcount
- Cinzel
- Della
- Eagle Lake
- Georgia
- Helvetica
- Inter
- Open Sans
- Oswald
- Playwrite
- Poppins
- Roboto
- Russo One
- TikTok Sans
- Times New Roman

Apply font per text element using `slides[].text_elements[].font_family` in `update --slides` payload.

**Per-text-element formatting fields (`slides[].text_elements[]`):**
- `content`, `x`, `y`
- `font_size`, `width`, `height`
- `style_preset`, `font_family`
- `background_color`, `text_color`, `border_radius` (especially useful for `inverted`)
- `editable`

**Other slide-level visual controls (`slides[]`):**
- `grid_images` + `grid_type` (`2x2`, `1+2`, `vertical`, `horizontal`)
- `background_filters` (`brightness`, `contrast`, `saturation`, `hue`, `blur`, `grayscale`, `sepia`, `invert`, `drop_shadow`, `opacity`)
- `image_overlays` (`id`, `image_url`, `x`, `y`, `width`, `height`, `rotation`, `opacity`)

### regenerate-slide
Regenerate AI text for a single slide (0-indexed).

```bash
genviral.sh regenerate-slide --id SLIDESHOW_ID --index 2
genviral.sh regenerate-slide --id SLIDESHOW_ID --index 2 --instruction "Make this shorter and more punchy"
```

Constraints:
- `--index` must be a non-negative integer
- `--instruction` max length: 500 characters

### duplicate | duplicate-slideshow
Clone an existing slideshow as a new draft.

```bash
genviral.sh duplicate --id SLIDESHOW_ID
```

### delete | delete-slideshow
Delete a slideshow.

```bash
genviral.sh delete --id SLIDESHOW_ID
```

### list-slideshows
List slideshows with filtering and pagination.

```bash
genviral.sh list-slideshows
genviral.sh list-slideshows --status rendered --search "hook" --limit 20 --offset 0
genviral.sh list-slideshows --json
```

---

## Pack Commands

Packs are collections of background images used in slideshows.

### list-packs
List available image packs.

```bash
genviral.sh list-packs
genviral.sh list-packs --search motivation --include-public false
genviral.sh list-packs --limit 20 --offset 0 --json
```

**`--search` is metadata-aware:** It matches across pack names AND AI image metadata (descriptions + keywords). So `--search "gym workout"` finds packs containing images tagged with those terms, even if the pack name is something generic.

`list-packs --json` returns pack summaries including:
- `id`
- `name`
- `image_count`
- `preview_image_url`
- `is_public`
- `created_at`

### get-pack
Get a single pack with the full ordered image list (what you need for slide-by-slide image selection).

```bash
genviral.sh get-pack --id PACK_ID
```

`get-pack` returns:
- `id`, `name`, `image_count`, `is_public`, `created_at`
- `images[]` ordered by creation time, each with:
  - `id`
  - `url`
  - `metadata` — AI-generated enrichment (populated asynchronously after image is added):
    - `status`: `pending` | `processing` | `completed` | `failed`
    - `description`: One-sentence description of the image content (null if not yet processed)
    - `keywords`: Array of lowercase search-friendly keywords (subject, mood, style, use-cases)
    - `model`: AI model used for analysis (e.g. `gpt-4.1-nano`)
    - `generated_at`: ISO timestamp when metadata was generated
    - `error`: Error message if processing failed (null on success)

**Example image with metadata:**
```json
{
  "id": "22222222-2222-2222-2222-222222222222",
  "url": "https://cdn.example.com/packs/motivation/01.jpg",
  "metadata": {
    "status": "completed",
    "description": "Woman lifting dumbbells in a bright, minimal gym environment.",
    "keywords": ["fitness", "workout", "strength", "gym", "motivation", "healthy lifestyle"],
    "model": "gpt-4.1-nano",
    "generated_at": "2026-02-17T11:02:00.000Z",
    "error": null
  }
}
```

### Smart Image Selection From Packs (MANDATORY)

**Do not skip this.** If you just pass `--pack-id` to `generate` without `pinned_images`, the server picks background images randomly from the pack. That produces incoherent slideshows. You MUST select images deliberately and pin them to specific slides.

#### Step-by-step (required every time a pack is used):

**1. Fetch pack images with metadata:**
```bash
genviral.sh get-pack --id PACK_ID
```
Collect every `images[].url` and `images[].metadata` from the response. Each image includes AI-generated metadata with `description` (what the image shows) and `keywords` (searchable tags).

**2. Use metadata to understand and shortlist images:**
Read each image's `metadata.description` and `metadata.keywords` to understand what it shows without needing to fetch every image visually. This is your primary selection tool:
- Match images to slide topics by description/keywords
- Filter out irrelevant images quickly
- If metadata `status` is `pending` or `failed`, the description won't be available — use vision tool for those

**When to use the vision/image tool additionally:**
- When metadata is unavailable (status not `completed`)
- When you need to assess **readability** (clean space for text, contrast, visual complexity) — metadata describes content but not layout suitability
- When the metadata description is ambiguous and you need a closer look
- For rendered slide review (always — see step 9 in pipeline)

Example vision call for readability assessment:
```
image(image="https://images.unsplash.com/photo-xxx?w=1080&q=80",
      prompt="Assess for slideshow text overlay: Where is clean space? How busy/detailed is the background? What text color/style would be most readable?")
```

**3. Plan your slides first, then match images:**
Before picking images, know your slide content:
- Slide 0: Hook text
- Slide 1: Problem/setup
- Slide 2: Discovery/shift
- Slide 3: Feature/proof
- Slide 4: CTA

For each slide, pick the image that best fits. Consider:
- **Topic match:** Does the image's description/keywords relate to the slide's message?
- **Text readability:** Will text be readable over this background? (Use vision tool if unsure)
- **Visual variety:** Avoid using near-identical images across slides
- **CTA slides** benefit from cleaner, less busy backgrounds

Use your judgment. There's no rigid formula — the right image depends on the specific content, the pack's images, and what looks good together.

**4. Build `pinned_images` and pass to generate:**
Once you've mapped images to slides, use `pinned_images` in `slide_config` so the server uses YOUR chosen images, not random ones:

```bash
genviral.sh generate \
  --prompt "Your slideshow prompt here" \
  --pack-id PACK_ID \
  --slides 5 \
  --type educational \
  --slide-config-json '{
    "total_slides": 5,
    "slide_types": ["image_pack","image_pack","image_pack","image_pack","image_pack"],
    "pinned_images": {
      "0": "https://images.unsplash.com/photo-HOOK-IMAGE?w=1080&q=80",
      "1": "https://images.unsplash.com/photo-PROBLEM-IMAGE?w=1080&q=80",
      "2": "https://images.unsplash.com/photo-DISCOVERY-IMAGE?w=1080&q=80",
      "3": "https://images.unsplash.com/photo-FEATURE-IMAGE?w=1080&q=80",
      "4": "https://images.unsplash.com/photo-CTA-IMAGE?w=1080&q=80"
    }
  }'
```

**Without `pinned_images`, your visual inspection is wasted** because the server will ignore your image preferences and pick randomly from the pack.

#### Quick reference: what NOT to do
```bash
# BAD: server picks random images, visual inspection was pointless
genviral.sh generate --prompt "..." --pack-id PACK_ID --slides 5

# GOOD: you control which image goes on which slide
genviral.sh generate --prompt "..." --pack-id PACK_ID --slides 5 \
  --slide-config-json '{"total_slides":5,"slide_types":["image_pack","image_pack","image_pack","image_pack","image_pack"],"pinned_images":{"0":"URL_0","1":"URL_1","2":"URL_2","3":"URL_3","4":"URL_4"}}'
```

#### Alternative: `custom_images` approach
Instead of `pinned_images` with `image_pack` type, you can use `custom_image` type with `custom_images` to directly assign URLs:
```json
{
  "total_slides": 5,
  "slide_types": ["custom_image","custom_image","custom_image","custom_image","custom_image"],
  "custom_images": {
    "0": {"image_url": "https://...", "image_name": "hook-bg"},
    "1": {"image_url": "https://...", "image_name": "problem-bg"}
  },
  "slide_texts": {
    "0": "your hook text here",
    "1": "your problem text here"
  }
}
```
Use `custom_images` with `--skip-ai` when you want full manual control over both images AND text. Use `pinned_images` with AI generation when you want the AI to write text but you control the images.

#### Choosing text styles (THINK, DON'T FOLLOW A TABLE)

Different backgrounds call for different text styles. Do NOT use the same style on every slide, and do NOT follow rigid rules. Use your judgment based on what you see.

**Available styles and what they do:**
- `tiktok` — White text with strong black outline/stroke. The "default" TikTok look.
- `inverted` — Black text on a white box. High contrast, cuts through anything.
- `shadow` — White text with heavy drop shadow. Subtle separation from background.
- `white` — Plain white text, minimal styling.
- `black` — Plain black text, minimal styling.
- `snapchat` — White text on a translucent dark bar.

**What to consider when choosing:**
- How busy/detailed is the background? (metadata keywords can hint at this; vision tool confirms)
- What's the dominant color/brightness of the area where text lands?
- Does the slide have a clear zone for text, or is the whole image complex?
- What's the overall aesthetic of the slideshow? Consistency matters, but readability matters more.

**You have full control per slide.** Set `style_preset` per text element using `slides[].text_elements[].style_preset` in the `update-slideshow` command. Mix styles across slides when it makes sense.

**You can also adjust the background itself** with `background_filters` via `update-slideshow`:
- `brightness`, `contrast`, `saturation`, `blur`, `opacity`, etc.
- Example: darken a busy image (`{"brightness": 0.5}`) or blur it (`{"blur": 2}`) to make text pop
- These can be combined and tuned per slide

**The goal is readability.** If text is hard to read at a glance, fix it — change the style, adjust the background, or pick a different image. There's no single "correct" style; the correct one is whatever makes the slide look good and the text instantly readable.

### create-pack
Create a new pack.

```bash
genviral.sh create-pack --name "My Pack"
genviral.sh create-pack --name "Public Pack" --is-public
# explicit boolean also supported
genviral.sh create-pack --name "Private Pack" --is-public false
```

### update-pack
Update pack name or visibility.

```bash
genviral.sh update-pack --id PACK_ID --name "New Name"
genviral.sh update-pack --id PACK_ID --is-public true
```

### delete-pack
Delete a pack.

```bash
genviral.sh delete-pack --id PACK_ID
```

### add-pack-image
Add an image to a pack. The response includes initial metadata status (`pending`) while AI enrichment (description, keywords) runs asynchronously in the background.

```bash
genviral.sh add-pack-image --pack-id PACK_ID --image-url "https://cdn.example.com/image.jpg"
genviral.sh add-pack-image --pack-id PACK_ID --image-url "https://cdn.example.com/image.jpg" --file-name "hero-1.jpg"
```

After adding, metadata will be auto-generated. Re-fetch the pack later to get completed metadata.

### delete-pack-image
Remove an image from a pack.

```bash
genviral.sh delete-pack-image --pack-id PACK_ID --image-id IMAGE_ID
```

---

## Template Commands

Templates are reusable slideshow structures. Convert winning slideshows into templates for faster iteration.

### list-templates
List templates visible in your scope.

```bash
genviral.sh list-templates
genviral.sh list-templates --search hooks --limit 20 --offset 0
genviral.sh list-templates --json
```

### get-template
Get a single template.

```bash
genviral.sh get-template --id TEMPLATE_ID
```

### create-template
Create a template from a validated template config object.

```bash
# File input
genviral.sh create-template \
  --name "My Template" \
  --description "Description" \
  --visibility private \
  --config-file template-config.json

# Inline JSON input
genviral.sh create-template \
  --name "My Template" \
  --visibility workspace \
  --config-json '{"version":1,"structure":{"slides":[]},"content":{},"visuals":{}}'
```

Config must be valid JSON matching the template config v1 schema.
Use exactly one of:
- `--config-file <path>`
- `--config-json '<json>'`

### update-template
Update template fields.

```bash
genviral.sh update-template --id TEMPLATE_ID --name "New Name"
genviral.sh update-template --id TEMPLATE_ID --visibility workspace
genviral.sh update-template --id TEMPLATE_ID --config-file new-config.json
genviral.sh update-template --id TEMPLATE_ID --config-json '{"version":1,"structure":{"slides":[]},"content":{},"visuals":{}}'
genviral.sh update-template --id TEMPLATE_ID --clear-description
```

Config input: use one of `--config-file` or `--config-json`.

### delete-template
Delete a template.

```bash
genviral.sh delete-template --id TEMPLATE_ID
```

### create-template-from-slideshow
Convert an existing slideshow into a reusable template.

```bash
genviral.sh create-template-from-slideshow \
  --slideshow-id SLIDESHOW_ID \
  --name "Winning Format" \
  --description "Built from high-performing slideshow" \
  --visibility workspace \
  --preserve-text
```

`--preserve-text` supports both forms:
- `--preserve-text` (sets true)
- `--preserve-text true|false`

---

## Analytics Commands

Analytics endpoints provide KPIs, post metrics, and tracked account management.

### analytics-summary (alias: `get-analytics-summary`)
Get analytics summary with KPIs, trends, and content mix.

```bash
genviral.sh analytics-summary
genviral.sh analytics-summary --range 30d
genviral.sh analytics-summary --start 2026-01-01 --end 2026-01-31
genviral.sh analytics-summary --platforms tiktok,instagram
genviral.sh analytics-summary --accounts TARGET_ID_1,TARGET_ID_2
genviral.sh analytics-summary --json
```

Options:
- `--range` - Date preset: `14d`, `30d`, `90d`, `1y`, `all`
- `--start` / `--end` - Custom date range (YYYY-MM-DD), must use both together
- `--platforms` - Comma-separated platform filter
- `--accounts` - Comma-separated analytics target IDs

Returns:
- `kpis` - publishedVideos, activeAccounts, views, likes, comments, shares, saves, engagementRate (with deltas)
- `interactionSeries` - Daily interactions
- `engagementSeries` - Daily engagement rate
- `postingHeatmap` - Daily post counts
- `postingStreak` - Consecutive posting days
- `contentMix` - Posts by platform

### analytics-posts (alias: `list-analytics-posts`)
List post-level analytics with sorting and pagination.

```bash
genviral.sh analytics-posts
genviral.sh analytics-posts --range 90d --sort-by views --sort-order desc --limit 25
genviral.sh analytics-posts --start 2026-01-01 --end 2026-01-31 --platforms tiktok
genviral.sh analytics-posts --json
```

Options:
- `--range` - Date preset: `14d`, `30d`, `90d`, `1y`, `all`
- `--start` / `--end` - Custom date range
- `--platforms` - Platform filter
- `--accounts` - Target ID filter
- `--sort-by` - `published_at`, `views`, `likes`, `comments`, `shares`
- `--sort-order` - `asc` or `desc`
- `--limit` - Page size (max 100)
- `--offset` - Pagination offset

### analytics-targets
List tracked analytics accounts.

```bash
genviral.sh analytics-targets
genviral.sh analytics-targets --json
```

### analytics-target-create
Add a new tracked account.

```bash
genviral.sh analytics-target-create --platform tiktok --identifier @brand
genviral.sh analytics-target-create --platform instagram --identifier @brand --alias "Brand HQ"
```

Options:
- `--platform` - `tiktok`, `instagram`, or `youtube` (required)
- `--identifier` - Account handle (required)
- `--alias` - Display name override

### analytics-target
Get details for a single analytics target.

```bash
genviral.sh analytics-target --id TARGET_ID
```

### analytics-target-update
Update an analytics target.

```bash
genviral.sh analytics-target-update --id TARGET_ID --display-name "New Name"
genviral.sh analytics-target-update --id TARGET_ID --favorite true
genviral.sh analytics-target-update --id TARGET_ID --clear-display-name
genviral.sh analytics-target-update --id TARGET_ID --refresh-policy-json '{"freeDailyRefresh":true}'
genviral.sh analytics-target-update --id TARGET_ID --clear-refresh-policy
```

### analytics-target-delete
Delete an analytics target.

```bash
genviral.sh analytics-target-delete --id TARGET_ID
```

### analytics-target-refresh
Trigger a refresh for an analytics target.

```bash
genviral.sh analytics-target-refresh --id TARGET_ID
```

Returns:
- Refresh ID and status
- `wasFree` - Whether free refresh window was used

### analytics-refresh | get-analytics-refresh
Check refresh status.

```bash
genviral.sh analytics-refresh --id REFRESH_ID
```

Returns:
- `status` - `pending`, `processing`, `completed`, or `failed`
- `credits_used`, `free_refresh_used`
- `started_at`, `completed_at`
- `error` (if failed)

### analytics-workspace-suggestions (alias: `get-analytics-workspace-suggestions`)
List other workspace/personal scopes with tracked accounts.

```bash
genviral.sh analytics-workspace-suggestions
genviral.sh get-analytics-workspace-suggestions
genviral.sh analytics-workspace-suggestions --json
```

---

## Legacy Pipeline Commands

These are TikTok-focused convenience commands from the original skill.

### post-draft
Post a rendered slideshow as a draft (TikTok-focused).

```bash
genviral.sh post-draft \
  --id SLIDESHOW_ID \
  --caption "Your caption with #hashtags" \
  --account-ids "account_id_1"
```

Always forces TikTok draft-safe settings: `privacy_level=SELF_ONLY` and `post_mode=MEDIA_UPLOAD`.

### full-pipeline
End-to-end: generate -> render -> review -> post draft.

```bash
genviral.sh full-pipeline \
  --prompt "Your hook and content prompt" \
  --caption "Caption with #hashtags" \
  --pack-id PACK_ID \
  --slides 5 \
  --type educational \
  --style tiktok \
  --account-ids ACC_ID
```

Use `--skip-post` to stop after rendering (useful for review before posting).

---

## Content Creation Pipeline

This is the recommended workflow for producing posts.

### For Slideshow Posts

1. **Hook Selection:** Read `hooks/library.json` and pick a hook. Rotate through categories.

2. **Pack Discovery:** Run `list-packs` to find candidate packs, then `get-pack --id ...` to fetch the full `images[]` array with URLs.

3. **Analyze Pack Images (MANDATORY - DO NOT SKIP):**
   Read each image's AI metadata (`description`, `keywords`) from the `get-pack` response. This tells you what each image shows. For images where you need to assess readability (clean space for text overlay, background complexity), use a vision/image tool. See "Smart Image Selection From Packs" section above for details.

4. **Map Images to Slides:** Plan your 5 slides (hook, problem, shift, feature, CTA), then assign the best-matching image to each slide based on metadata + visual analysis. Build a `pinned_images` map: `{"0": "url_for_hook", "1": "url_for_problem", ...}`.

5. **Prompt Assembly:** Use the selected hook and chosen visual direction to build a full slideshow prompt. Reference `prompts/slideshow.md`.

6. **Generate Slideshow WITH Pinned Images:** Run `generate` with your prompt, pack ID, AND `--slide-config-json` containing `pinned_images`. This ensures the server uses YOUR chosen images instead of picking randomly. Example:
   ```bash
   genviral.sh generate \
     --prompt "Your prompt" \
     --pack-id PACK_ID \
     --slides 5 \
     --slide-config-json '{"total_slides":5,"slide_types":["image_pack","image_pack","image_pack","image_pack","image_pack"],"pinned_images":{"0":"URL_0","1":"URL_1","2":"URL_2","3":"URL_3","4":"URL_4"}}'
   ```
   **Never call generate with just `--pack-id` and no `pinned_images`.** That lets the server pick random images, making your visual inspection pointless.

7. **Review Slide Text:** Check each slide for clarity, readability, and flow. Update or regenerate weak slides.

8. **Render:** Run `render` to generate final images.

9. **Visual Review + Fix Loop (MANDATORY — DO NOT SKIP THE FIX):**
   Visually inspect EVERY rendered slide using a vision/image-analysis tool. For each slide, check:
   - (a) Is text readable at a glance? Can you read it in under 2 seconds?
   - (b) Does the background match your intent?
   - (c) Any text overflow or clipping?

   **If ANY slide fails readability: you MUST fix it before moving on.** Do not just report "needs fixing." Actually fix it:
   ```bash
   # Fix: update the slide's style_preset, background_filters, or image — then re-render
   genviral.sh update --id SLIDESHOW_ID --slides '[...slides with adjusted style_preset, filters, etc...]'
   genviral.sh render --id SLIDESHOW_ID
   ```
   Options: change `style_preset`, add `background_filters` (darken, blur), swap the image, adjust text positioning. Pick whatever makes it readable.
   Then visually review the fixed slides again. Repeat until ALL slides pass.

   **You are NOT allowed to proceed to step 10 until every slide is readable.** This is a hard gate, not a suggestion.

10. **Post:** Use `create-post` with media-type slideshow, or use legacy `post-draft` for TikTok drafts.

11. **Log the Post (MANDATORY):** Immediately after posting, append an entry to `content/post-log.md` with: date, time (UTC), post ID, type (slideshow/video), hook/caption snippet, status (posted/scheduled/draft), and which pack was used. This is the single source of truth for all content output. If the file doesn't exist, create it with the header format. Never skip this step.

12. **Tag in Hook Tracker (MANDATORY):** Immediately after logging the post, add an entry to `performance/hook-tracker.json` with the hook text, hook category, CTA text, CTA type, pack ID, post ID, slideshow ID, platform, account ID, and posted timestamp. Set `status` to `posted`. Leave all `metrics` fields as `null` until analytics data is available. This is how you build the feedback loop. No tracking = no learning.

    Hook categories: `person-conflict`, `relatable-pain`, `educational`, `pov`, `before-after`, `feature-spotlight`
    CTA types: `link-in-bio`, `search-app-store`, `app-name-only`, `soft-cta`, `no-cta`

13. **Performance Check (periodic -- run at 48h and 7d after posting):** Pull analytics for recent posts and update `hook-tracker.json` with real numbers.

    ```bash
    genviral.sh analytics-posts --range 7d --sort-by views --sort-order desc --json
    ```

    For each post in the results, find its entry in `hook-tracker.json` by `post_id`, update the `metrics` block with current views, likes, comments, shares, saves, and set `last_checked` to now. Set `status` to `tracking`. See `references/analytics-loop.md` for the full cross-reference process.

14. **Weekly Review (every Monday):** Pull the last 7 days of analytics, apply the diagnostic framework, categorize each hook into `double_down / keep_rotating / testing / dropped`, and write a brief summary in `performance/weekly-review.md`. See `references/analytics-loop.md` for the full review process and decision rules.

### For Video Posts

1. **Source Video:** Upload via `upload` command or reference existing CDN URL.

2. **Write Caption:** Follow brand voice, include relevant hashtags.

3. **Create Post:** Run `create-post` with media-type video.

4. **Track Performance:** Check analytics.

---

## Performance Feedback Loop

Post. Track. Learn. Adjust. Repeat. This is the only way content improves over time.

The genviral skill has full analytics built in. The missing piece is the discipline to actually use it. This section explains the full loop.

### The Core Files

- `performance/hook-tracker.json` - tracks every post's hook, CTA, and metrics
- `performance/competitor-insights.md` - niche research and competitor analysis
- `performance/weekly-review.md` - weekly review notes
- `references/analytics-loop.md` - full analytics reference and review process

### After Every Post: Tag It

Every post goes into `performance/hook-tracker.json` immediately after posting. The entry structure:

```json
{
  "post_id": "...",
  "slideshow_id": "...",
  "hook_text": "...",
  "hook_category": "person-conflict|relatable-pain|educational|pov|before-after|feature-spotlight",
  "cta_text": "...",
  "cta_type": "link-in-bio|search-app-store|app-name-only|soft-cta|no-cta",
  "pack_id": "...",
  "template_id": null,
  "posted_at": "2026-02-17T10:00:00Z",
  "platform": "tiktok|instagram",
  "account_id": "...",
  "metrics": {
    "views": null,
    "likes": null,
    "comments": null,
    "shares": null,
    "saves": null,
    "last_checked": null
  },
  "status": "posted"
}
```

If you skip this, the data is gone. You will never know which hooks worked because you never tracked which hooks you used.

### At 48h and 7d: Pull Metrics

```bash
genviral.sh analytics-posts --range 7d --sort-by views --sort-order desc --json
```

Match each post to its hook-tracker entry by `post_id`. Fill in views, likes, comments, shares, saves. Set `last_checked` to now. Set `status` to `tracking`.

### The Diagnostic Framework

Once you have views and engagement rate (likes + comments + shares + saves / views), apply this:

**High views + High engagement rate:** Hook and content both work. SCALE. Make 3 variations of this hook immediately. Move to `rules.double_down`.

**High views + Low engagement rate:** Hook stops the scroll. Content or CTA fails to convert. Keep the hook, fix the content arc or swap the CTA type. Investigate whether a different CTA type changes engagement.

**Low views + High engagement rate:** Content resonates with people who see it. Hook is not stopping the scroll. Rework the hook -- make it more direct, more emotionally charged, or more pattern-interrupting. Content structure is worth keeping.

**Low views + Low engagement rate:** Nothing is working. Drop this angle. Try something radically different. Do not keep iterating on a dead end.

### Decision Rules

| Views | Action |
|-------|--------|
| 50K+ | Double down. 3 variations now. Add to `rules.double_down`. |
| 10K - 50K | Keep in rotation. Improve gradually. Add to `rules.keep_rotating`. |
| 1K - 10K | Test one more variation. Add to `rules.testing`. |
| Under 1K, twice | Drop it. Add to `rules.dropped`. |

"Twice" means two separate posts with the same hook category or hook type both failed. One bad post can be a distribution issue. Two is a pattern.

### Weekly Review

Every Monday, run the review:

1. Pull `analytics-summary --range 7d` for the overview
2. Pull `analytics-posts --range 7d --sort-by views --sort-order desc` for per-post data
3. Update hook-tracker with fresh metrics
4. Categorize each recent post (double_down / keep_rotating / testing / dropped)
5. Check `hook_categories` aggregates: which category has the highest `avg_views`?
6. Check `cta_performance`: which CTA type has the best `avg_engagement_rate`?
7. Decide next week's content focus based on data, not intuition
8. Write a brief summary in `performance/weekly-review.md`

After 4+ weeks of data, patterns become clear. Before that, keep posting a variety of hook categories to build the sample size.

See `references/analytics-loop.md` for the full process, including the weekly review template.

---

## CTA Testing Framework

CTAs are not random. They are a variable you can test systematically.

### CTA Types

| Type | Example | When to Use |
|------|---------|-------------|
| `link-in-bio` | "Link in bio to try for free" | When you want traffic to a URL |
| `search-app-store` | "Search [App Name] on the App Store" | When the app is the product |
| `app-name-only` | Just say the app name at the end | Soft brand awareness, no friction |
| `soft-cta` | "Worth checking out" or "Changed everything for me" | When hard CTAs feel off for the content |
| `no-cta` | Nothing -- content ends naturally | For brand-building content or when CTA would kill the vibe |

### How to Rotate CTAs Systematically

Do not pick CTAs randomly. Rotate them with intent:

1. Start by trying each CTA type 2-3 times across different posts
2. Track each use in `performance/hook-tracker.json` under `cta_type`
3. After 10+ posts, check `cta_performance` in hook-tracker: which type has the highest `avg_engagement_rate`?
4. Shift weight toward the winner. If `search-app-store` consistently outperforms `link-in-bio`, use it more.
5. Keep testing the others occasionally. What works can change as the account grows.

### Pairing CTAs with Hook Categories

Not all CTAs work equally well with all hook types. Track these combinations in hook-tracker.

As you accumulate data, look for patterns like:
- "Relatable-pain hooks with soft CTAs get higher engagement than relatable-pain hooks with link-in-bio"
- "Feature-spotlight hooks with search-app-store CTAs convert better than with no-cta"

After 20+ posts across categories, you will have enough data to make these calls with confidence. Until then, vary and track.

### The Goal

Identify the CTA type that converts best for each hook category. This maximizes the value of every piece of content you produce.

---

## Platform Best Practices

### TikTok

**Slide Count:** 5-6 slides is the sweet spot.

**Aspect Ratio:** `9:16` for fullscreen, `4:5` for feed.

**Text Readability:** One idea per slide. 8-16 words max. Avoid text in bottom 20% (UI overlap).

**Narrative Structure (5-slide arc):**
1. Hook (stop the scroll)
2. Problem detail
3. Shift (introduce the solution)
4. Feature/proof
5. CTA

### Instagram

**Slide Count:** 5-10 slides for carousel posts.

**Aspect Ratio:**
- Reels: 9:16
- Feed posts: 4:5 or 1:1

---

## API Error Codes

Common Partner API error patterns:

- `401 unauthorized` - API key missing, malformed, or invalid
- `402 subscription_required` - workspace/account needs an active subscription
- `403 tier_not_allowed` - current plan tier does not include the attempted capability
- `422 invalid_payload` - request shape or enum values are invalid
- `429 rate_limited` - too many requests in a short window

---

## Troubleshooting

**"GENVIRAL_API_KEY is required"**
Export the environment variable: `export GENVIRAL_API_KEY="your_public_id.your_secret"`

**"No rendered image URLs found"**
The slideshow has not been rendered yet. Run `render` first.

**API returns 401, 402, or 403**
- `401`: verify API key format (`public_id.secret`) and token validity
- `402 subscription_required`: activate or upgrade subscription
- `403 tier_not_allowed`: your tier does not permit that feature

**Render takes too long**
Each slide takes 2-5 seconds. For 5 slides, expect up to 25 seconds.

---

## Notes

- **Multi-platform support:** Works with any platform genviral supports (TikTok, Instagram, etc.)
- **Content types:** Supports both video posts and slideshow (photo carousel) posts
- **Hosted vs BYO accounts:** Works with both hosted and BYO accounts
- **Scheduling:** Posts can be scheduled for future publish or queued for immediate posting
- **Draft mode:** For TikTok slideshow posts, use `post_mode: MEDIA_UPLOAD` to save to drafts inbox
- **Template system:** Convert winning slideshows to templates for faster iteration
- **Analytics:** Full analytics support for tracking performance across accounts
- **Never use em-dashes** in any generated content
