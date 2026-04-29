#!/usr/bin/env python3
"""
Stage 8: Full Upload to Meta Ads Manager
Creates campaign → ad sets → uploads images → creates creatives → creates ads.
All PAUSED by default.

Usage:
    python3 upload_to_meta.py --rundir runs/genviral-2026-03-02/ --product genviral
    python3 upload_to_meta.py --rundir runs/genviral-2026-03-02/ --product genviral --dry-run
    python3 upload_to_meta.py --rundir runs/genviral-2026-03-02/ --product genviral --campaign-id 123  # skip campaign creation
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent          # campaign/scripts/
SKILL_DIR = SCRIPT_DIR.parent.parent.parent            # agent/skills/
META_ADS_SCRIPTS = SCRIPT_DIR.parent.parent / "scripts"  # meta-ads/scripts/
sys.path.insert(0, str(META_ADS_SCRIPTS))

from meta_api import MetaAPI, load_config


def find_ad_sets(rundir: str) -> dict:
    """Find all ad-set-* dirs with images and copy."""
    rundir_path = Path(rundir)
    ad_sets = {}
    for d in sorted(rundir_path.glob("ad-set-*")):
        if not d.is_dir():
            continue
        images = sorted(list(d.glob("image-*.png")) + list(d.glob("image-*.jpg")))
        copy_file = d / "copy.md"
        brief_file = d / "ad-set-brief.md"
        ad_sets[d.name] = {
            "path": str(d),
            "images": [str(img) for img in images],
            "copy_file": str(copy_file) if copy_file.exists() else None,
            "brief_file": str(brief_file) if brief_file.exists() else None,
            "image_count": len(images),
        }
    return ad_sets


def parse_copy_md(copy_file: str) -> dict:
    """Extract primary texts, headlines, descriptions, CTA from copy.md."""
    if not copy_file or not os.path.exists(copy_file):
        return {}
    with open(copy_file) as f:
        content = f.read()

    result = {}

    # Extract all 3 primary text variations
    primary_texts = []
    for i, label in enumerate(["V1", "V2", "V3"], 1):
        pattern = rf'\*\*{label}.*?\*\*[:\s]*\n(.*?)(?=\n\*\*V\d|\n---|\n##|\Z)'
        match = re.search(pattern, content, re.DOTALL)
        if match:
            primary_texts.append(match.group(1).strip())
    result["primary_texts"] = primary_texts or ["Check out our product"]

    # Extract headlines
    headlines = []
    hl_section = re.search(r'## Headlines.*?\n((?:\d+\..*\n?)+)', content)
    if hl_section:
        for line in hl_section.group(1).strip().split("\n"):
            hl = re.sub(r'^\d+\.\s*', '', line).strip()
            if hl:
                headlines.append(hl)
    result["headlines"] = headlines or ["Learn More"]

    # Extract descriptions
    descriptions = []
    desc_section = re.search(r'## Descriptions.*?\n((?:\d+\..*\n?)+)', content)
    if desc_section:
        for line in desc_section.group(1).strip().split("\n"):
            desc = re.sub(r'^\d+\.\s*', '', line).strip()
            if desc:
                descriptions.append(desc)
    result["descriptions"] = descriptions

    # CTA
    cta_match = re.search(r'Primary:\s*(.+)', content)
    if cta_match:
        result["cta_text"] = cta_match.group(1).strip()

    # Link
    url_match = re.search(r'Link:\s*(\S+)', content)
    if url_match:
        result["link_url"] = url_match.group(1).strip()

    return result


CTA_MAP = {
    "Start Free Trial": "SIGN_UP",
    "Try Free": "SIGN_UP",
    "Sign Up": "SIGN_UP",
    "Get Started": "GET_STARTED",
    "See How It Works": "LEARN_MORE",
    "Try Genviral Free": "SIGN_UP",
    "See It In Action": "LEARN_MORE",
    "Fix Your Reach": "LEARN_MORE",
    "Try AI Studio Free": "SIGN_UP",
    "See the Workflow": "LEARN_MORE",
    "Join 3,296 Businesses": "SIGN_UP",
    "Learn More": "LEARN_MORE",
}


def main():
    parser = argparse.ArgumentParser(description="Stage 8: Full Upload to Meta")
    parser.add_argument("--rundir", required=True, help="Campaign run directory")
    parser.add_argument("--product", required=True, help="Product name from config")
    parser.add_argument("--campaign-id", help="Existing campaign ID (skip creation)")
    parser.add_argument("--campaign-name", default=None, help="Campaign name")
    parser.add_argument("--daily-budget", type=float, default=50.0, help="Daily budget in account currency (default: 50)")
    parser.add_argument("--objective", default="OUTCOME_SALES", help="Campaign objective")
    parser.add_argument("--custom-event", default="PURCHASE", help="Pixel custom event type")
    parser.add_argument("--countries", default="US,CA,GB,AU,NZ,AE,SG", help="Comma-separated country codes")
    parser.add_argument("--age-min", type=int, default=18)
    parser.add_argument("--age-max", type=int, default=65)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    print(f"\n📤 Stage 8: Full Upload to Meta Ads")
    print(f"   Run dir: {args.rundir}")
    print(f"   Product: {args.product}")
    print(f"   Budget: €{args.daily_budget}/day CBO")
    if args.dry_run:
        print(f"   Mode: DRY RUN\n")

    # Load config
    config_path = SKILL_DIR / "meta-ads" / "config.yaml"
    config = load_config(str(config_path))
    product_config = config.get("products", {}).get(args.product)
    if not product_config:
        print(f"  ✗ Product '{args.product}' not found in config", file=sys.stderr)
        sys.exit(1)

    api = MetaAPI(config["access_token"], product_config["ad_account_id"])

    # Find ad sets
    ad_sets = find_ad_sets(args.rundir)
    if not ad_sets:
        print("  ✗ No ad-set-* directories found.", file=sys.stderr)
        sys.exit(1)

    print(f"   Ad sets found: {len(ad_sets)}")
    for name, data in ad_sets.items():
        print(f"     - {name}: {data['image_count']} images, copy: {'✓' if data['copy_file'] else '✗'}")

    page_id = product_config.get("page_id", "")
    pixel_id = product_config.get("pixel_id", "")
    link_url = product_config.get("lp_url", "https://genviral.io")
    ig_id = product_config.get("ig_account_id", "")

    countries = [c.strip() for c in args.countries.split(",")]
    budget_cents = int(args.daily_budget * 100)

    # ── Step 1: Create Campaign ──
    campaign_name = args.campaign_name or f"GV/2026/Q1/ACQ"
    campaign_id = args.campaign_id

    if not campaign_id:
        if args.dry_run:
            print(f"\n  [DRY RUN] Would create campaign: {campaign_name}")
            campaign_id = "DRY_RUN_CAMPAIGN"
        else:
            print(f"\n  Creating campaign: {campaign_name}")
            campaign_id = api.create_campaign(
                name=campaign_name,
                objective=args.objective,
                status="PAUSED",
                daily_budget_cents=budget_cents,
                bid_strategy="LOWEST_COST_WITHOUT_CAP",
            )
            print(f"  ✓ Campaign ID: {campaign_id}")
    else:
        print(f"\n  Using existing campaign: {campaign_id}")

    # ── Step 2: Create Ad Sets + Ads ──
    targeting = {
        "age_min": args.age_min,
        "age_max": args.age_max,
        "geo_locations": {
            "countries": countries,
            "location_types": ["home", "recent"],
        },
        "targeting_automation": {
            "advantage_audience": 1,
        },
    }

    promoted_object = {
        "pixel_id": pixel_id,
        "custom_event_type": args.custom_event,
    }

    total_ads = 0
    results = {}

    for ad_set_name, ad_set_data in ad_sets.items():
        copy_data = parse_copy_md(ad_set_data.get("copy_file"))
        primary_texts = copy_data.get("primary_texts", [""])
        headlines = copy_data.get("headlines", ["Learn More"])
        descriptions = copy_data.get("descriptions", [])
        cta_text = copy_data.get("cta_text", "Learn More")
        cta_type = CTA_MAP.get(cta_text, "LEARN_MORE")
        ad_link_url = copy_data.get("link_url", link_url)

        # Clean ad set name for Meta (e.g. "ad-set-01-tool-consolidation" → "GV/Q1/ToolStack")
        short_names = {
            "ad-set-01-tool-consolidation": "GV/Q1/ToolStack",
            "ad-set-02-volume": "GV/Q1/Volume",
            "ad-set-03-ai-creation": "GV/Q1/AICreate",
            "ad-set-04-anti-shadowban": "GV/Q1/NoShadow",
            "ad-set-05-social-proof": "GV/Q1/Proof",
        }
        meta_adset_name = short_names.get(ad_set_name, ad_set_name)

        print(f"\n  📦 {meta_adset_name}")

        # Create ad set (no individual budget — CBO distributes)
        if args.dry_run:
            print(f"    [DRY RUN] Would create ad set: {meta_adset_name}")
            adset_id = f"DRY_RUN_{ad_set_name}"
        else:
            adset_id = api.create_adset(
                name=meta_adset_name,
                campaign_id=campaign_id,
                optimization_goal="OFFSITE_CONVERSIONS",
                billing_event="IMPRESSIONS",
                bid_strategy="LOWEST_COST_WITHOUT_CAP",
                targeting=targeting,
                promoted_object=promoted_object,
                status="PAUSED",
            )
            print(f"    ✓ Ad Set ID: {adset_id}")

        # Create ads (one per image)
        ad_ids = []
        for i, image_path in enumerate(ad_set_data["images"]):
            image_name = Path(image_path).stem
            # Rotate through copy variations
            primary_text = primary_texts[i % len(primary_texts)]
            headline = headlines[i % len(headlines)]
            description = descriptions[i % len(descriptions)] if descriptions else None

            ad_name = f"{meta_adset_name}/{image_name}"
            print(f"    📄 {ad_name}")

            if args.dry_run:
                print(f"       [DRY RUN] Image: {Path(image_path).name}")
                print(f"       [DRY RUN] Headline: {headline}")
                print(f"       [DRY RUN] Body: {primary_text[:60]}...")
                total_ads += 1
                continue

            # Upload image
            print(f"       Uploading image...")
            image_hash = api.create_ad_image(image_path)
            print(f"       ✓ Hash: {image_hash[:16]}...")

            # Create creative
            print(f"       Creating creative...")
            creative_id = api.create_ad_creative(
                name=ad_name,
                page_id=page_id,
                image_hash=image_hash,
                headline=headline,
                body=primary_text,
                link_url=ad_link_url,
                cta_type=cta_type,
                description=description,
            )
            print(f"       ✓ Creative: {creative_id}")

            # Create ad
            print(f"       Creating ad...")
            ad_id = api.create_ad(
                name=ad_name,
                adset_id=adset_id,
                creative_id=creative_id,
                status="PAUSED",
            )
            print(f"       ✓ Ad: {ad_id}")
            ad_ids.append(ad_id)
            total_ads += 1

        results[ad_set_name] = {
            "adset_id": adset_id,
            "ad_ids": ad_ids,
        }

    # ── Summary ──
    print(f"\n{'=' * 50}")
    print(f"✅ Stage 8 Complete")
    print(f"   Campaign: {campaign_id}")
    print(f"   Ad Sets: {len(results)}")
    print(f"   Total Ads: {total_ads}")
    print(f"   Status: ALL PAUSED")
    print(f"\n   Review in Meta Ads Manager, then activate.")

    # Save result manifest
    manifest = {
        "campaign_id": campaign_id,
        "product": args.product,
        "ad_sets": results,
        "total_ads": total_ads,
    }
    manifest_path = Path(args.rundir) / "upload-manifest.json"
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)
    print(f"   Manifest: {manifest_path}")


if __name__ == "__main__":
    main()
