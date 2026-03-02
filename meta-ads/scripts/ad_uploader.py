#!/usr/bin/env python3
"""
Step 5: Ad Uploader
Takes approved copy variations (from copy_generator output) and uploads them
as new ads in Meta Ads Manager.

Flow:
  1. Read copy-{product}-latest.json for approved variations
  2. For each variation:
     a. Upload image (if provided) → get image_hash
     b. Create AdCreative with headline + body + image
     c. Create Ad (status=PAUSED by default — you review before activating)
  3. Report ad IDs created

Usage:
    python3 ad_uploader.py --product genviral --adset-id 123456789 [--image-dir ./images] [--activate]
    
    --image-dir: directory of image files (jpg/png). One per variation, named 1.jpg, 2.jpg etc.
    --activate: set ad status to ACTIVE instead of PAUSED (careful!)
    --variation-ids: comma-separated IDs from copy output to upload (default: all)

Note: Always creates ads as PAUSED first. Review in Meta Ads Manager, then activate manually
      or re-run with --activate after review.
"""

import argparse
import json
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(__file__))
from meta_api import MetaAPI, load_config

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")


def find_image(image_dir: str, variation_id: int) -> str | None:
    """Look for variation image in common formats."""
    if not image_dir:
        return None
    for ext in ["jpg", "jpeg", "png", "gif"]:
        path = os.path.join(image_dir, f"{variation_id}.{ext}")
        if os.path.exists(path):
            return path
    return None


def upload_variation(
    api: MetaAPI,
    variation: dict,
    adset_id: str,
    page_id: str,
    link_url: str,
    image_dir: str,
    status: str,
    product: str,
) -> dict:
    """Upload a single copy variation as a new ad. Returns result dict."""
    v_id = variation.get("id", "?")
    headline = variation.get("headline", "")
    body = variation.get("primary_text", "")
    cta = variation.get("cta_type", "LEARN_MORE")
    angle = variation.get("angle", "")

    result = {
        "variation_id": v_id,
        "angle": angle,
        "headline": headline,
        "status": "pending",
    }

    # Step 1: Upload image if available
    image_hash = None
    image_path = find_image(image_dir, v_id)
    if image_path:
        print(f"[uploader] Uploading image: {image_path}", file=sys.stderr)
        image_hash = api.create_ad_image(image_path)
        result["image_hash"] = image_hash
        print(f"[uploader] Image hash: {image_hash}", file=sys.stderr)

    # Step 2: Create AdCreative
    creative_name = f"{product} | {angle[:40]} | {datetime.now(timezone.utc).strftime('%Y%m%d')}"
    print(f"[uploader] Creating creative: {creative_name}", file=sys.stderr)

    creative_id = api.create_ad_creative(
        name=creative_name,
        page_id=page_id,
        headline=headline,
        body=body,
        image_hash=image_hash,
        link_url=link_url,
        cta_type=cta,
    )
    result["creative_id"] = creative_id
    print(f"[uploader] Creative created: {creative_id}", file=sys.stderr)

    # Step 3: Create Ad
    ad_name = f"{product} | {angle[:40]} | v{v_id}"
    ad_id = api.create_ad(
        name=ad_name,
        adset_id=adset_id,
        creative_id=creative_id,
        status=status,
    )
    result["ad_id"] = ad_id
    result["status"] = "created"
    result["ad_status"] = status
    print(f"[uploader] Ad created: {ad_id} (status={status})", file=sys.stderr)

    return result


def main():
    parser = argparse.ArgumentParser(description="Upload approved ad copy to Meta Ads Manager")
    parser.add_argument("--product", required=True)
    parser.add_argument("--adset-id", required=True, help="Ad Set ID to create ads in")
    parser.add_argument("--image-dir", help="Directory with images named 1.jpg, 2.jpg, etc.")
    parser.add_argument("--variation-ids", help="Comma-separated variation IDs to upload (default: all)")
    parser.add_argument("--activate", action="store_true", help="Set ad status to ACTIVE (default: PAUSED)")
    parser.add_argument("--config")
    args = parser.parse_args()

    config = load_config(args.config)
    product_cfg = config["products"][args.product]

    api = MetaAPI(
        access_token=config["access_token"],
        ad_account_id=product_cfg["ad_account_id"],
    )
    page_id = product_cfg.get("page_id")
    link_url = product_cfg.get("website_url")

    if not page_id:
        print("❌ page_id not set in config.yaml for this product", file=sys.stderr)
        sys.exit(1)

    if not link_url:
        print("❌ website_url not set in config.yaml for this product", file=sys.stderr)
        sys.exit(1)

    # Load copy variations
    copy_path = os.path.join(DATA_DIR, f"copy-{args.product}-latest.json")
    if not os.path.exists(copy_path):
        print(f"❌ No copy file found at {copy_path}. Run copy_generator.py first.", file=sys.stderr)
        sys.exit(1)

    with open(copy_path) as f:
        copy_data = json.load(f)

    variations = copy_data.get("new_variations", [])

    if args.variation_ids:
        try:
            selected_ids = {int(x.strip()) for x in args.variation_ids.split(",") if x.strip()}
        except ValueError:
            print("❌ --variation-ids must be comma-separated integers (e.g. 1,3,5)", file=sys.stderr)
            sys.exit(2)
        variations = [v for v in variations if v.get("id") in selected_ids]

    if not variations:
        print("❌ No variations to upload", file=sys.stderr)
        sys.exit(1)

    status = "ACTIVE" if args.activate else "PAUSED"
    print(f"[uploader] Uploading {len(variations)} variation(s) to adset {args.adset_id} (status={status})", file=sys.stderr)

    results = []
    for v in variations:
        try:
            result = upload_variation(
                api=api,
                variation=v,
                adset_id=args.adset_id,
                page_id=page_id,
                link_url=link_url,
                image_dir=args.image_dir,
                status=status,
                product=args.product,
            )
            results.append(result)
        except Exception as e:
            print(f"❌ Failed to upload variation {v.get('id')}: {e}", file=sys.stderr)
            results.append({"variation_id": v.get("id"), "status": "failed", "error": str(e)})

    # Output summary
    created = [r for r in results if r.get("status") == "created"]
    failed = [r for r in results if r.get("status") == "failed"]

    print(f"\n✅ {len(created)} ads created ({status})")
    for r in created:
        print(f"  • Ad {r['ad_id']} — {r['angle']}")

    if failed:
        print(f"\n❌ {len(failed)} failures:")
        for r in failed:
            print(f"  • Variation {r['variation_id']}: {r.get('error', '?')}")

    if status == "PAUSED":
        print("\n💡 Ads created as PAUSED. Review in Meta Ads Manager, then activate when ready.")
        print("   Or re-run with --activate to set ACTIVE immediately.")

    # Save
    out = {
        "product": args.product,
        "adset_id": args.adset_id,
        "uploaded_at": datetime.now(timezone.utc).isoformat(),
        "results": results,
    }
    out_path = os.path.join(DATA_DIR, f"upload-{args.product}-latest.json")
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(out, f, indent=2)
    print(f"[saved → {out_path}]", file=sys.stderr)


if __name__ == "__main__":
    main()
