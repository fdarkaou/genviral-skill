# Creative Formats — Nano Banana Pro Image Prompts

For each format below: replace {HOOK}, {BRAND_COLOR}, {LOGO_PATH}, {PRODUCT} with values from brand.json.

## Format 1: Comparison Table
**Best for:** Tool consolidation, price comparison, feature parity angles

```bash
uv run /usr/lib/node_modules/openclaw/skills/nano-banana-pro/scripts/generate_image.py \
  --prompt "Clean flat design comparison table ad. Left column header 'YOUR CURRENT STACK' in red/orange. Right column header '{PRODUCT}' in {BRAND_COLOR} with logo. Left column lists 3-4 separate tools with monthly prices, total in red showing e.g. '$277/mo'. Right column shows single subscription with checkmarks for each equivalent feature, price in green. White background, modern sans-serif font, 1:1 ratio. No humans. Professional but punchy." \
  --filename "runs/{RUNDIR}/{AD_SET}/image-01-comparison.png" \
  --resolution 1K
```

## Format 2: Apple Notes Style
**Best for:** Tactical tips, insider knowledge, "what I actually use" angles

```bash
uv run /usr/lib/node_modules/openclaw/skills/nano-banana-pro/scripts/generate_image.py \
  --prompt "Realistic Apple Notes screenshot as ad creative. Yellow notepad texture, handwriting-style font. Title: '{HOOK}'. Bullet points below with 3-4 key insights or tips. Slight drop shadow. Bottom: small logo watermark. Feels like a friend's personal note, not an ad. Square format." \
  --filename "runs/{RUNDIR}/{AD_SET}/image-02-apple-notes.png" \
  --resolution 1K
```

## Format 3: Quote Card (Testimonial Style)
**Best for:** Social proof, specific results, voice of customer angles

```bash
uv run /usr/lib/node_modules/openclaw/skills/nano-banana-pro/scripts/generate_image.py \
  --prompt "Bold quote card ad. Dark ({BRAND_COLOR} or near-black) background. Large quotation marks in brand accent color. Quote text: '{EXACT_QUOTE}' in white, large clean serif or modern sans font. Attribution below in smaller text. Small logo bottom right. Minimal, high contrast, editorial feel. Square 1:1." \
  --filename "runs/{RUNDIR}/{AD_SET}/image-03-quotes.png" \
  --resolution 1K
```

## Format 4: Handwriting / Chalkboard
**Best for:** Personal, behind-the-scenes, founder voice, contrarian takes

```bash
uv run /usr/lib/node_modules/openclaw/skills/nano-banana-pro/scripts/generate_image.py \
  --prompt "Dark chalkboard or kraft paper background. Handwritten text in white or chalk color: '{HOOK}'. Possibly with a quick hand-drawn sketch or underline. Feels authentic and personal. One central thought, no clutter. Optional: small doodle illustration related to the hook. Square format." \
  --filename "runs/{RUNDIR}/{AD_SET}/image-04-handwriting.png" \
  --resolution 1K
```

## Format 5: Fake iMessage Thread
**Best for:** Conversation hooks, objection handling, "ask me about X" angles

```bash
uv run /usr/lib/node_modules/openclaw/skills/nano-banana-pro/scripts/generate_image.py \
  --prompt "Realistic iPhone iMessage conversation screenshot. Clean iOS interface. 3-4 message bubbles. Blue bubbles (sender) asking about a pain point or result. Grey bubbles (recipient) giving a surprising answer that ties to the product benefit. End with a reaction or reveal. No real names. Feels like a screenshot a friend sent you. Vertical (9:16 cropped to 1:1) or square format." \
  --filename "runs/{RUNDIR}/{AD_SET}/image-05-imessage.png" \
  --resolution 1K
```

## Format 6: Notification / System Alert
**Best for:** Software results, automation wins, "while you were sleeping" angles

```bash
uv run /usr/lib/node_modules/openclaw/skills/nano-banana-pro/scripts/generate_image.py \
  --prompt "Realistic macOS or iOS notification mockup. App icon: {LOGO_PATH}. Notification title: '{PRODUCT}'. Body: '{RESULT_HOOK}' — a surprising positive result (e.g. '47 articles analyzed while you were at lunch'). Subtle drop shadow on notification card. Blurred laptop or desk background. Feels like a real screenshot. Square 1:1." \
  --filename "runs/{RUNDIR}/{AD_SET}/image-06-notification.png" \
  --resolution 1K
```

## Format 7: Before/After Split
**Best for:** Transformation angles, time savings, workflow improvement

```bash
uv run /usr/lib/node_modules/openclaw/skills/nano-banana-pro/scripts/generate_image.py \
  --prompt "Clean before/after split ad. Left half labeled 'BEFORE' with muted/red tones showing a painful situation (messy workflow, stack of tools, stressed person at desk). Right half labeled 'AFTER' in brand color with clean, simple, happy state. Bold dividing line. Text overlays on each side describing the transformation. No faces or recognizable people. Square 1:1." \
  --filename "runs/{RUNDIR}/{AD_SET}/image-07-before-after.png" \
  --resolution 1K
```

## Format 8: Bullet Stats / Social Proof Wall
**Best for:** Numbers, milestones, credibility, "join X users" angles

```bash
uv run /usr/lib/node_modules/openclaw/skills/nano-banana-pro/scripts/generate_image.py \
  --prompt "Clean dark background stats card. Brand logo top center. 3-4 large bold numbers with labels: e.g. '3,296 teams', '88K viral hooks analyzed', '6.3x average ROAS'. Each stat in large white number, smaller label below. Accent color for the numbers. Minimal, data-driven, trustworthy feel. Square 1:1." \
  --filename "runs/{RUNDIR}/{AD_SET}/image-08-stats.png" \
  --resolution 1K
```

---

## Recommended Format Mix Per Ad Set
Choose 4-5 formats per ad set. Recommended default mix:
- Always include: Comparison OR Stats (credibility anchor)
- Always include: Quote OR iMessage (social proof / conversation hook)
- Pick 2-3 from: Apple Notes, Handwriting, Notification, Before/After

## Copy.md Template

```markdown
# {AD_SET_NAME} — Ad Copy

## Angle: {ANGLE}
## Target: {AUDIENCE_DESCRIPTION}

---

## Primary Text (3 variations)

**V1 (Pain hook):**
[2-3 sentences. Lead with pain point from customer-profile.md. Twist to product. CTA.]

**V2 (Result hook):**
[Lead with specific result/transformation. Bridge to how. CTA.]

**V3 (Contrarian/Pattern interrupt):**
[Surprising take or specific data point. Brief explanation. CTA.]

---

## Headlines (5 variations)
1. 
2. 
3. 
4. 
5. 

## Descriptions (3 variations)
1. 
2. 
3. 

## CTAs
- Primary: [e.g. "Try Free"]
- Alt: [e.g. "See How It Works"]
- Alt: [e.g. "Get Started Today"]

---

## Link: {LP_URL}
```
