#!/usr/bin/env python3
"""
Stage 7: Creative Generator
Generates ad images using Genviral's Studio API (studio-generate-image).

Requires: GENVIRAL_API_KEY env var set
Model: google/nano-banana-pro (2 credits) or google/nano-banana-2 (1 credit)

Usage:
    python3 generate_creatives.py --rundir runs/genviral-2026-03-02/ --ad-set ad-set-01-comparison
    python3 generate_creatives.py --rundir runs/genviral-2026-03-02/ --all
    python3 generate_creatives.py --rundir runs/genviral-2026-03-02/ --all --model google/nano-banana-2
    python3 generate_creatives.py --rundir runs/genviral-2026-03-02/ --dry-run
"""

import argparse
import json
import os
import re
import subprocess
import sys
import urllib.request
from pathlib import Path

# Path to genviral CLI script — resolves to sibling skill
SKILL_ROOT = Path(__file__).parent.parent.parent.parent  # agent/skills/
GENVIRAL_SCRIPT = SKILL_ROOT / "genviral" / "scripts" / "genviral.sh"

DEFAULT_MODEL = "google/nano-banana-2"   # default: equal quality to pro, faster + cheaper
PRO_MODEL = "google/nano-banana-pro"     # higher quality option (2 credits)

# Image format definitions
IMAGE_FORMATS = {
    "comparison": {
        "filename": "image-01-comparison.png",
        "aspect_ratio": "1:1",
        "prompt_template": (
            "Clean flat design ad creative for {product}. Comparison table. "
            "Left column header 'YOUR STACK' in red/coral. Right column header '{product}' "
            "in {color}. Left column: 3-4 separate tools with monthly costs each, bold red "
            "total showing high cumulative price. Right column: same features as checkmarks, "
            "single clean price in green. White background, modern sans-serif typography. "
            "No humans, no photography. Professional, conversion-focused layout. 1:1 square."
        ),
    },
    "apple-notes": {
        "filename": "image-02-apple-notes.png",
        "aspect_ratio": "1:1",
        "prompt_template": (
            "Realistic Apple Notes app screenshot used as ad creative. Yellow-cream notepad "
            "texture, handwriting-style font. Title line: '{hook}'. 3-4 bullet points with "
            "insider tips or insights about {product_context}. Small drop shadow, minimal "
            "UI chrome. Feels like a screenshot a friend sent. No logos overlaid. Square 1:1."
        ),
    },
    "quotes": {
        "filename": "image-03-quotes.png",
        "aspect_ratio": "1:1",
        "prompt_template": (
            "Bold editorial quote card. Deep {color} background (dark, rich tone). "
            "Large decorative quotation marks in bright accent color. "
            "Quote text: '{quote}' in clean large white sans-serif font. "
            "Minimal attribution text below. High contrast, magazine editorial look. "
            "No clutter. Square 1:1."
        ),
    },
    "handwriting": {
        "filename": "image-04-handwriting.png",
        "aspect_ratio": "1:1",
        "prompt_template": (
            "Dark textured background (chalkboard, kraft paper, or dark linen). "
            "Authentic handwritten white text: '{hook}'. "
            "One central thought — no decorative borders, no heavy branding. "
            "Optional tiny hand-drawn sketch or underline for emphasis. "
            "Personal, raw, founder-voice aesthetic. Square 1:1."
        ),
    },
    "notification": {
        "filename": "image-05-notification.png",
        "aspect_ratio": "1:1",
        "prompt_template": (
            "Realistic macOS desktop notification mockup as ad creative. "
            "App notification card floating over a blurred desk/laptop background. "
            "App name: '{product}'. Notification title: 'New result'. "
            "Body text: '{hook}'. Subtle drop shadow. Looks like a genuine screenshot. "
            "No fake UI embellishments. Square 1:1."
        ),
    },
    "imessage": {
        "filename": "image-06-imessage.png",
        "aspect_ratio": "9:16",
        "prompt_template": (
            "Realistic iPhone iMessage conversation screenshot as ad. "
            "Standard iOS blue/grey chat bubbles. 3-4 messages: "
            "someone asking about a pain point, friend responding with a surprising result "
            "from using {product}. Ends on a reveal or 'how?' cliffhanger. "
            "No real names. iOS status bar at top. Authentic screenshot look. Vertical 9:16."
        ),
    },
    "stats": {
        "filename": "image-07-stats.png",
        "aspect_ratio": "1:1",
        "prompt_template": (
            "Dark background credibility stats card. "
            "{product} branding at top. "
            "3-4 large bold white metric numbers with smaller descriptive labels: "
            "e.g. user counts, speed metrics, results data. "
            "Accent {color} on the numbers. Clean, data-forward, trustworthy. "
            "Minimal design, no stock photos. Square 1:1."
        ),
    },
    "before-after": {
        "filename": "image-08-before-after.png",
        "aspect_ratio": "1:1",
        "prompt_template": (
            "Clean split-panel before/after ad. Left half: 'BEFORE' label, muted red/grey "
            "tones, illustrating a chaotic or manual workflow (stacked tools, cluttered screen, "
            "stressed look). Right half: 'AFTER' label in {color}, clean minimal interface, "
            "simple and calm. Bold dividing line. Text annotations on each side. "
            "No realistic human faces. Square 1:1."
        ),
    },
}


def run_genviral_cmd(args_list: list, timeout: int = 120) -> dict:
    """Run a genviral.sh command and return parsed result."""
    if not GENVIRAL_SCRIPT.exists():
        return {"ok": False, "error": f"genviral.sh not found at {GENVIRAL_SCRIPT}"}

    env = os.environ.copy()  # inherits GENVIRAL_API_KEY
    cmd = ["bash", str(GENVIRAL_SCRIPT)] + args_list

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, env=env)
        output = result.stdout + result.stderr

        # genviral.sh outputs "OK: ..." on success
        if result.returncode == 0 or "OK:" in output:
            # Extract output URL if present
            url_match = re.search(r'https?://\S+\.(?:png|jpg|jpeg|webp)', output)
            return {
                "ok": True,
                "output_url": url_match.group(0) if url_match else None,
                "raw": output,
            }
        else:
            return {"ok": False, "error": output[:500], "raw": output}

    except subprocess.TimeoutExpired:
        return {"ok": False, "error": f"Timeout after {timeout}s"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def download_image(url: str, dest_path: str) -> bool:
    """Download generated image from genviral CDN to local path."""
    # Use curl with -L (follow redirects) — more reliable than urllib for CDN URLs
    try:
        result = subprocess.run(
            ["curl", "-sL", "-o", dest_path, url],
            capture_output=True, timeout=60
        )
        if result.returncode == 0 and Path(dest_path).exists() and Path(dest_path).stat().st_size > 1000:
            return True
        # Fallback: urllib
        urllib.request.urlretrieve(url, dest_path)
        return True
    except Exception as e:
        print(f"    ✗ Download failed: {e}", file=sys.stderr)
        return False


def load_brand(rundir: str) -> dict:
    brand_path = Path(rundir) / "brand.json"
    if brand_path.exists():
        with open(brand_path) as f:
            return json.load(f)
    return {"og_title": "Product", "primary_color": "#6B46C1", "url": ""}


def build_prompt(format_key: str, brand: dict, ad_set_context: dict) -> str:
    template = IMAGE_FORMATS[format_key]["prompt_template"]

    # Extract clean product name from og_title (strip emoji/suffixes)
    og_title = brand.get("og_title") or brand.get("title") or "this product"
    product = og_title.split("–")[0].split("-")[0].split("|")[0].strip()

    color = brand.get("primary_color", "#6B46C1")
    if color == "#000000":
        color = "deep purple"  # Better for prompts than pure black

    hook = ad_set_context.get("hook", f"The smarter way to {product.lower()}")
    quote = ad_set_context.get("quote", f"{product} completely changed how our team creates content")
    product_context = ad_set_context.get("product_context", brand.get("description", product))

    return template.format(
        product=product,
        color=color,
        hook=hook,
        quote=quote,
        product_context=product_context[:150] if product_context else product,
    )


def generate_image(prompt: str, output_path: str, model: str,
                   aspect_ratio: str = "1:1", dry_run: bool = False) -> bool:
    if dry_run:
        print(f"      [DRY RUN] {Path(output_path).name}")
        print(f"      Model: {model} | AR: {aspect_ratio}")
        print(f"      Prompt: {prompt[:90]}...")
        return True

    if not os.getenv("GENVIRAL_API_KEY"):
        print(f"      ✗ GENVIRAL_API_KEY not set", file=sys.stderr)
        return False

    cmd_args = [
        "studio-generate-image",
        "--model-id", model,
        "--prompt", prompt,
        "--aspect-ratio", aspect_ratio,
        "--output-format", "png",
        "--json",
    ]

    result = run_genviral_cmd(cmd_args, timeout=90)

    if result["ok"] and result.get("output_url"):
        # Download to local path
        if download_image(result["output_url"], output_path):
            size_kb = Path(output_path).stat().st_size // 1024
            print(f"      ✓ {Path(output_path).name} ({size_kb}KB)")
            return True
        else:
            # Save URL reference at least
            ref_path = output_path + ".url"
            with open(ref_path, "w") as f:
                f.write(result["output_url"])
            print(f"      ⚠ Saved URL ref: {ref_path}")
            return True
    else:
        err = result.get("error", "Unknown error")
        print(f"      ✗ {Path(output_path).name}: {err[:120]}", file=sys.stderr)
        return False


def load_ad_set_context(ad_set_dir: Path) -> dict:
    """Extract hook, quote, context from ad-set-brief.md if present."""
    context = {}
    brief_path = ad_set_dir / "ad-set-brief.md"
    if brief_path.exists():
        with open(brief_path) as f:
            content = f.read()
        hook_match = re.search(r'(?i)(?:hook|headline)[:\s]+(.+)', content)
        if hook_match:
            context["hook"] = hook_match.group(1).strip()
        quote_match = re.search(r'(?i)quote[:\s]+(.+)', content)
        if quote_match:
            context["quote"] = quote_match.group(1).strip()

    # Default hook from ad-set folder name (e.g. "ad-set-01-broken-score" → "broken score")
    if "hook" not in context:
        name_parts = ad_set_dir.name.split("-")
        angle = " ".join(name_parts[2:]) if len(name_parts) > 2 else ad_set_dir.name
        context["hook"] = f"The {angle} problem nobody talks about"

    return context


def generate_for_ad_set(rundir: str, ad_set_name: str, brand: dict, model: str,
                        formats: list = None, dry_run: bool = False) -> int:
    ad_set_dir = Path(rundir) / ad_set_name
    ad_set_dir.mkdir(parents=True, exist_ok=True)

    if not formats:
        formats = ["comparison", "apple-notes", "quotes", "handwriting", "notification", "stats"]

    context = load_ad_set_context(ad_set_dir)

    print(f"\n  📦 {ad_set_name}")
    print(f"     Hook: {context['hook']}")

    generated = 0
    for fmt in formats:
        if fmt not in IMAGE_FORMATS:
            print(f"     ⚠ Unknown format '{fmt}', skipping", file=sys.stderr)
            continue

        fmt_config = IMAGE_FORMATS[fmt]
        output_path = str(ad_set_dir / fmt_config["filename"])
        aspect_ratio = fmt_config.get("aspect_ratio", "1:1")
        prompt = build_prompt(fmt, brand, context)

        if generate_image(prompt, output_path, model, aspect_ratio, dry_run):
            generated += 1

    print(f"     → {generated}/{len(formats)} images {'would be ' if dry_run else ''}generated")
    return generated


def main():
    parser = argparse.ArgumentParser(description="Creative Generator — Stage 7 (Genviral Studio)")
    parser.add_argument("--rundir", required=True, help="Campaign run directory")
    parser.add_argument("--ad-set", help="Specific ad set name")
    parser.add_argument("--all", action="store_true", help="Generate for all ad sets")
    parser.add_argument("--formats", help="Comma-separated: comparison,apple-notes,quotes,handwriting,notification,imessage,stats,before-after")
    parser.add_argument("--model", default=DEFAULT_MODEL, help=f"Genviral model ID (default: {DEFAULT_MODEL})")
    parser.add_argument("--pro", action="store_true", help=f"Use higher quality model ({PRO_MODEL})")
    parser.add_argument("--dry-run", action="store_true", help="Show prompts without generating")
    args = parser.parse_args()

    model = PRO_MODEL if args.pro else args.model
    formats = args.formats.split(",") if args.formats else None

    print(f"\n🎨 Stage 7: Creative Generation (Genviral Studio)")
    print(f"   Run dir: {args.rundir}")
    print(f"   Model: {model}")
    if args.dry_run:
        print(f"   Mode: DRY RUN")

    brand = load_brand(args.rundir)
    product = (brand.get("og_title") or "Product").split("–")[0].strip()
    print(f"   Brand: {product}")
    print(f"   Color: {brand.get('primary_color', 'N/A')}\n")

    if args.ad_set:
        generate_for_ad_set(args.rundir, args.ad_set, brand, model, formats, args.dry_run)

    elif args.all:
        rundir_path = Path(args.rundir)
        ad_sets = sorted([d.name for d in rundir_path.iterdir()
                          if d.is_dir() and d.name.startswith("ad-set-")])
        if not ad_sets:
            print("  No ad-set-* directories found. Run Stage 6 first.")
            sys.exit(1)
        print(f"  Found {len(ad_sets)} ad sets\n")
        total = sum(generate_for_ad_set(args.rundir, a, brand, model, formats, args.dry_run)
                    for a in ad_sets)
        print(f"\n✅ Total images: {total}")

    else:
        print("  Specify --ad-set NAME or --all")
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
