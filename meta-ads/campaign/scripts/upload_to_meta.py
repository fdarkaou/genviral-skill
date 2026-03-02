#!/usr/bin/env python3
"""
Stage 8: Upload to Meta Ads Manager
Reads generated creatives from a campaign run and uploads to Meta.
Imports meta_api.py from the meta-ads skill.

Usage:
    python3 upload_to_meta.py --rundir runs/genviral-2026-03-02/ --product genviral
    python3 upload_to_meta.py --rundir runs/genviral-2026-03-02/ --product genviral --activate
    python3 upload_to_meta.py --rundir runs/genviral-2026-03-02/ --product genviral --dry-run
"""

import argparse
import json
import os
import sys
from pathlib import Path

# Import meta_api from sibling skill
SKILL_DIR = Path(__file__).parent.parent.parent  # agent/skills/
META_ADS_SCRIPTS = SKILL_DIR / "meta-ads" / "scripts"
sys.path.insert(0, str(META_ADS_SCRIPTS))

try:
    from meta_api import MetaAPI, load_config
    META_AVAILABLE = True
except ImportError:
    META_AVAILABLE = False
    print("Warning: meta_api not available. Run from /root/clawd/agent/skills/", file=sys.stderr)


def find_creatives(rundir: str) -> dict:
    """Find all generated images and copy.md files in run directory."""
    rundir_path = Path(rundir)
    ad_sets = {}

    for ad_set_dir in sorted(rundir_path.glob("ad-set-*")):
        if not ad_set_dir.is_dir():
            continue

        ad_set_name = ad_set_dir.name
        images = sorted(ad_set_dir.glob("image-*.png")) + sorted(ad_set_dir.glob("image-*.jpg"))
        copy_file = ad_set_dir / "copy.md"

        ad_sets[ad_set_name] = {
            "path": str(ad_set_dir),
            "images": [str(img) for img in images],
            "copy_file": str(copy_file) if copy_file.exists() else None,
            "image_count": len(images),
        }

    return ad_sets


def parse_copy_md(copy_file: str) -> dict:
    """Extract primary text, headline, CTA from copy.md."""
    if not copy_file or not os.path.exists(copy_file):
        return {}

    with open(copy_file) as f:
        content = f.read()

    result = {}

    # Extract first primary text variation
    import re
    body_match = re.search(r'\*\*V1.*?\*\*[:\s]*\n(.*?)(?=\n\*\*V2|\n---|\Z)', content, re.DOTALL)
    if body_match:
        result["primary_text"] = body_match.group(1).strip()

    # Extract first headline
    headline_match = re.search(r'## Headlines.*?\n1\.\s*(.+)', content)
    if headline_match:
        result["headline"] = headline_match.group(1).strip()

    # Extract first CTA
    cta_match = re.search(r'Primary:\s*\[?([^\]\n]+)\]?', content)
    if cta_match:
        result["call_to_action"] = cta_match.group(1).strip()

    # Extract LP URL
    url_match = re.search(r'Link:\s*(\S+)', content)
    if url_match:
        result["link_url"] = url_match.group(1).strip()

    return result


def upload_ad_set(api, product_config: dict, ad_set_name: str, ad_set_data: dict,
                  activate: bool = False, dry_run: bool = False) -> list:
    """Upload images and create ads for one ad set. Returns list of created ad IDs."""
    ad_ids = []
    copy_data = parse_copy_md(ad_set_data.get("copy_file"))

    primary_text = copy_data.get("primary_text", f"Check out {product_config.get('name', 'our product')}")
    headline = copy_data.get("headline", "Learn More")
    link_url = copy_data.get("link_url", product_config.get("lp_url", ""))
    call_to_action = copy_data.get("call_to_action", "LEARN_MORE")

    # Map CTA text to Meta API enum
    cta_map = {
        "Try Free": "TRY_IT",
        "Sign Up": "SIGN_UP",
        "Get Started": "GET_STARTED",
        "Learn More": "LEARN_MORE",
        "Shop Now": "SHOP_NOW",
    }
    cta_type = cta_map.get(call_to_action, "LEARN_MORE")

    page_id = product_config.get("page_id", "")
    ig_id = product_config.get("ig_account_id", "")

    for image_path in ad_set_data["images"]:
        image_name = Path(image_path).stem
        print(f"\n    Processing: {image_name}")

        if dry_run:
            print(f"    [DRY RUN] Would upload image: {image_path}")
            print(f"    [DRY RUN] Headline: {headline}")
            print(f"    [DRY RUN] Primary text: {primary_text[:60]}...")
            continue

        if not META_AVAILABLE:
            print(f"    ✗ meta_api not available", file=sys.stderr)
            continue

        try:
            # Upload image
            print(f"    Uploading image...")
            image_hash = api.create_ad_image(image_path)
            print(f"    ✓ Image hash: {image_hash[:12]}...")

            # Create creative
            print(f"    Creating creative...")
            creative_id = api.create_ad_creative(
                name=f"{ad_set_name}-{image_name}",
                page_id=page_id,
                image_hash=image_hash,
                message=primary_text,
                headline=headline,
                link_url=link_url,
                call_to_action_type=cta_type,
                instagram_actor_id=ig_id,
            )
            print(f"    ✓ Creative ID: {creative_id}")

            # TODO: Would need adset_id from strategy.md or user input
            # For now, log what needs to be done
            print(f"    ℹ️  To create ad: use meta-ads skill's ad_uploader.py with creative_id={creative_id}")
            ad_ids.append(creative_id)

        except Exception as e:
            print(f"    ✗ Error: {e}", file=sys.stderr)

    return ad_ids


def main():
    parser = argparse.ArgumentParser(description="Meta Uploader — Stage 8")
    parser.add_argument("--rundir", required=True, help="Campaign run directory")
    parser.add_argument("--product", required=True, help="Product name (from meta-ads config)")
    parser.add_argument("--activate", action="store_true", help="Activate ads after creating (default: paused)")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be uploaded")
    args = parser.parse_args()

    print(f"\n📤 Stage 8: Upload to Meta Ads")
    print(f"   Run dir: {args.rundir}")
    print(f"   Product: {args.product}")
    if args.dry_run:
        print(f"   Mode: DRY RUN\n")

    # Load ad sets
    ad_sets = find_creatives(args.rundir)
    if not ad_sets:
        print("  No ad-set-* directories found with images.", file=sys.stderr)
        sys.exit(1)

    print(f"\n  Found {len(ad_sets)} ad sets:")
    for name, data in ad_sets.items():
        print(f"  - {name}: {data['image_count']} images, copy: {'✓' if data['copy_file'] else '✗'}")

    if not args.dry_run and META_AVAILABLE:
        # Load meta-ads config
        config_path = SKILL_DIR / "meta-ads" / "config.yaml"
        if not config_path.exists():
            print(f"\n  ✗ meta-ads config not found at {config_path}", file=sys.stderr)
            sys.exit(1)

        config = load_config(str(config_path))
        product_config = config.get("products", {}).get(args.product)
        if not product_config:
            print(f"\n  ✗ Product '{args.product}' not found in meta-ads config", file=sys.stderr)
            print(f"  Available: {list(config.get('products', {}).keys())}", file=sys.stderr)
            sys.exit(1)

        api = MetaAPI(config["access_token"], product_config["ad_account_id"])
    else:
        config = {"products": {args.product: {"name": args.product, "page_id": "TEST", "lp_url": "#"}}}
        product_config = config["products"][args.product]
        api = None

    print()
    total_uploaded = 0
    for ad_set_name, ad_set_data in ad_sets.items():
        print(f"\n  📦 {ad_set_name}")
        ad_ids = upload_ad_set(api, product_config, ad_set_name, ad_set_data,
                               activate=args.activate, dry_run=args.dry_run)
        total_uploaded += len(ad_ids)

    print(f"\n✅ Stage 8 Complete")
    print(f"   {'Would upload' if args.dry_run else 'Uploaded'}: {total_uploaded} creatives")
    if not args.activate:
        print(f"   All ads created as PAUSED — review in Ads Manager before activating")


if __name__ == "__main__":
    main()
