#!/usr/bin/env python3
"""
Step 4: Ad Copy Generator
Analyzes your top-performing ads (by CPA/ROAS), extracts the patterns
(hooks, angles, CTAs), then generates N new variations using Claude.

Usage:
    python3 copy_generator.py --product genviral [--count 5] [--config config.yaml]

Output:
    Prints generated ad variations + writes to data/copy-{product}-latest.json
"""

import argparse
import json
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(__file__))
from meta_api import MetaAPI, load_config

DEFAULT_COUNT = 5
MIN_SPEND_FOR_ANALYSIS = 20.0  # Only analyze ads with meaningful spend


def get_top_performers(api: MetaAPI, action_type: str, limit: int = 10) -> list:
    """Pull ad-level insights, sort by CPA ascending, return top performers with creative data."""
    ad_insights = api.get_insights(
        level="ad",
        date_preset="last_30d",
        action_type=action_type,
    )

    # Filter: must have spend and at least 1 conversion
    qualified = [
        r for r in ad_insights
        if r["spend"] >= MIN_SPEND_FOR_ANALYSIS and r.get("target_action_count", 0) >= 1
    ]

    if not qualified:
        # Fall back to CTR-based ranking if no conversions yet
        qualified = [r for r in ad_insights if r["spend"] >= MIN_SPEND_FOR_ANALYSIS]
        qualified.sort(key=lambda x: x.get("ctr", 0), reverse=True)
    else:
        qualified.sort(key=lambda x: x.get("target_cpa") or float("inf"))

    return qualified[:limit]


def enrich_with_creatives(api: MetaAPI, top_ads: list) -> list:
    """Pull creative data (headline, body, CTA) for each top ad."""
    enriched = []
    ads_data = api.get_ads()

    ad_lookup = {ad["id"]: ad for ad in ads_data}

    for row in top_ads:
        ad_id = row.get("ad_id")
        ad = ad_lookup.get(ad_id, {})
        creative = ad.get("creative", {})

        enriched.append({
            "ad_id": ad_id,
            "ad_name": row.get("ad_name", "?"),
            "spend": row["spend"],
            "cpa": row.get("target_cpa"),
            "conversions": row.get("target_action_count", 0),
            "ctr": row.get("ctr", 0),
            "frequency": row.get("frequency", 0),
            "creative": {
                "headline": creative.get("title", ""),
                "body": creative.get("body", ""),
                "cta": creative.get("call_to_action_type", ""),
                "image_url": creative.get("image_url", ""),
            },
        })

    return enriched


def analyze_patterns(top_ads: list) -> dict:
    """Extract patterns from top performers for the Claude prompt."""
    hooks = []
    bodies = []
    ctas = set()

    for ad in top_ads:
        c = ad["creative"]
        if c["headline"]:
            hooks.append(c["headline"])
        if c["body"]:
            bodies.append(c["body"])
        if c["cta"]:
            ctas.add(c["cta"])

    return {
        "hooks": hooks,
        "bodies": bodies,
        "ctas": list(ctas),
        "top_3_summary": [
            {
                "headline": ad["creative"]["headline"],
                "body": ad["creative"]["body"][:200] if ad["creative"]["body"] else "",
                "cpa": ad["cpa"],
                "ctr": ad["ctr"],
                "conversions": ad["conversions"],
            }
            for ad in top_ads[:3]
        ],
    }


def generate_copy_with_claude(patterns: dict, product_cfg: dict, count: int) -> list:
    """
    Call Claude API to generate new ad copy variations.
    Uses the same token infrastructure (ANTHROPIC_API_KEY from env).
    """
    import urllib.request
    import urllib.error

    api_key = os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("CLAUDE_API_KEY")
    if not api_key:
        # Try to load from openclaw config
        config_path = os.path.expanduser("~/.openclaw/openclaw.json")
        if os.path.exists(config_path):
            with open(config_path) as f:
                oc = json.load(f)
            api_key = oc.get("anthropicApiKey") or oc.get("apiKey")

    if not api_key:
        raise RuntimeError("No ANTHROPIC_API_KEY found. Set it in env or ~/.openclaw/openclaw.json")

    product_name = product_cfg.get("name", "our product")
    product_desc = product_cfg.get("description", "")
    target_audience = product_cfg.get("target_audience", "")
    unique_value = product_cfg.get("unique_value_prop", "")
    cta_type = product_cfg.get("default_cta", "LEARN_MORE")

    top_3_formatted = json.dumps(patterns["top_3_summary"], indent=2)
    hooks_list = "\n".join(f"  - {h}" for h in patterns["hooks"][:10])
    bodies_list = "\n".join(f"  - {b[:100]}..." for b in patterns["bodies"][:5] if b)

    prompt = f"""You are an expert Facebook/Instagram ad copywriter. Your job is to generate new ad variations based on what's already working.

PRODUCT: {product_name}
DESCRIPTION: {product_desc}
TARGET AUDIENCE: {target_audience}
UNIQUE VALUE PROP: {unique_value}

TOP PERFORMING ADS (sorted by CPA ascending = best first):
{top_3_formatted}

WINNING HOOKS USED:
{hooks_list}

WINNING BODY COPY SAMPLES:
{bodies_list}

TASK: Generate {count} new ad copy variations that could outperform the current best. Each variation should:
1. Use a different angle or hook style from the winners
2. Keep the proven elements that make them work (urgency, specificity, social proof)
3. Be appropriate for Facebook/Instagram feed placement
4. Have a clear CTA: {cta_type}

For each variation output EXACTLY this JSON format:
{{
  "id": 1,
  "angle": "brief description of the angle/approach",
  "headline": "...",
  "primary_text": "...",
  "cta_type": "{cta_type}",
  "why_it_might_win": "brief explanation"
}}

Output a JSON array of {count} objects. No markdown, no explanation, just the array."""

    body = json.dumps({
        "model": "claude-sonnet-4-5-20250514",
        "max_tokens": 2000,
        "messages": [{"role": "user", "content": prompt}],
    }).encode()

    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=body,
        method="POST",
        headers={
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
    )

    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read())
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Claude API HTTP {e.code}: {body}") from e
    except urllib.error.URLError as e:
        raise RuntimeError(f"Claude API network error: {e}") from e

    content = data.get("content", [])
    if not content or "text" not in content[0]:
        raise RuntimeError(f"Unexpected Claude response shape: {json.dumps(data)[:300]}")

    raw_text = content[0]["text"].strip()

    # Strip markdown code blocks if present
    if raw_text.startswith("```"):
        parts = raw_text.split("```")
        raw_text = parts[1] if len(parts) > 1 else raw_text
        raw_text = raw_text.lstrip()
        if raw_text.startswith("json"):
            raw_text = raw_text[4:].lstrip()

    try:
        return json.loads(raw_text)
    except json.JSONDecodeError as e:
        raise RuntimeError(f"Claude returned non-JSON: {raw_text[:300]}") from e


def main():
    parser = argparse.ArgumentParser(description="Generate ad copy variations from top performers")
    parser.add_argument("--product", required=True)
    parser.add_argument("--count", type=int, default=DEFAULT_COUNT)
    parser.add_argument("--config")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    config = load_config(args.config)
    product_cfg = config["products"][args.product]
    api = MetaAPI(
        access_token=config["access_token"],
        ad_account_id=product_cfg["ad_account_id"],
    )
    action_type = product_cfg.get("action_type", "purchase")

    print(f"[copy-gen] Fetching top performers for {args.product}…", file=sys.stderr)
    top_ads = get_top_performers(api, action_type)

    if not top_ads:
        print("⚠️  No qualifying ads found. Run more spend first.", file=sys.stderr)
        sys.exit(1)

    print(f"[copy-gen] Enriching {len(top_ads)} ads with creative data…", file=sys.stderr)
    enriched = enrich_with_creatives(api, top_ads)
    patterns = analyze_patterns(enriched)

    print(f"[copy-gen] Generating {args.count} new variations with Claude…", file=sys.stderr)
    variations = generate_copy_with_claude(patterns, product_cfg, args.count)

    result = {
        "product": args.product,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "top_performers": enriched[:3],
        "patterns_extracted": patterns,
        "new_variations": variations,
    }

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(f"\n✍️  {args.count} New Ad Copy Variations — {args.product.upper()}\n")
        for v in variations:
            print(f"━━━ Variation {v.get('id', '?')} — {v.get('angle', '')} ━━━")
            print(f"📢 Headline: {v.get('headline', '')}")
            print(f"📝 Body:\n{v.get('primary_text', '')}")
            print(f"🔘 CTA: {v.get('cta_type', '')}")
            print(f"💡 Why it might win: {v.get('why_it_might_win', '')}")
            print()

    # Save
    data_dir = os.path.join(os.path.dirname(__file__), "..", "data")
    os.makedirs(data_dir, exist_ok=True)
    out_path = os.path.join(data_dir, f"copy-{args.product}-latest.json")
    with open(out_path, "w") as f:
        json.dump(result, f, indent=2)
    print(f"[saved → {out_path}]", file=sys.stderr)


if __name__ == "__main__":
    main()
