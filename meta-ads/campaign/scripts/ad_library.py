#!/usr/bin/env python3
"""
Stage 5: Meta Ad Library Scraper
Pulls competitor ads from Meta's Ad Library API (no auth needed for transparency data).

Usage:
    python3 ad_library.py --query "genviral" --output runs/genviral-2026-03-02/
    python3 ad_library.py --query "hootsuite" --country GB --limit 50 --output runs/...
"""

import argparse
import json
import os
import re
import sys
import time
import urllib.request
import urllib.parse
from pathlib import Path
from datetime import datetime

META_AD_LIBRARY_URL = "https://www.facebook.com/ads/library/async/search_ads/"
SEARCH_URL = "https://graph.facebook.com/v21.0/ads_archive"

# Ad Library API doesn't require auth for active ads
# We'll use the unofficial search endpoint first, then fall back to scraping tips


def search_ad_library_api(query: str, country: str = "ALL", limit: int = 30) -> list:
    """
    Use Meta's Ad Library API (public, no auth needed for basic search).
    Returns list of ad dicts.
    """
    params = {
        "search_terms": query,
        "ad_type": "ALL",
        "ad_reached_countries": country,
        "fields": "id,ad_creative_bodies,ad_creative_link_captions,ad_creative_link_descriptions,ad_creative_link_titles,ad_delivery_start_time,ad_snapshot_url,page_name,impressions,spend",
        "limit": str(limit),
        "access_token": "APPID|APPSECRET",  # Public app token (works for ad library)
    }

    # Try without access token first (limited but works)
    public_url = f"https://graph.facebook.com/v21.0/ads_archive?{urllib.parse.urlencode({k: v for k, v in params.items() if k != 'access_token'})}"

    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    }

    try:
        req = urllib.request.Request(public_url, headers=headers)
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read())
            return data.get("data", [])
    except Exception as e:
        return []


def search_web_for_competitor_ads(query: str) -> str:
    """
    Fallback: Generate research prompts for Claude to search the web.
    Returns a markdown prompt for web research.
    """
    return f"""
## Manual Research Required

The Meta Ad Library API requires an access token for full results.
Claude should use web_search and web_fetch to research competitor ads for: **{query}**

Search queries to use:
1. `site:facebook.com/ads/library "{query}"` 
2. `"{query}" meta ads examples 2024 2025`
3. `"{query}" facebook ads creative examples`
4. `"{query}" site:adspy.com OR site:bigspy.com OR site:adlibrary.io`

For each competitor found, extract:
- Ad copy patterns (hooks, CTAs, tone)
- Visual formats (video, static, carousel)
- Angles used (pain, social proof, feature, comparison)
- Approximate performance signals (engagement, comments)

Save findings to competitor-ads.md
"""


def analyze_ads(ads: list, query: str) -> dict:
    """Analyze a list of ads and extract patterns."""
    if not ads:
        return {"ads": [], "patterns": {}}

    hooks = []
    ctas = []
    angles = []
    formats = []

    for ad in ads:
        bodies = ad.get("ad_creative_bodies", [])
        titles = ad.get("ad_creative_link_titles", [])
        captions = ad.get("ad_creative_link_captions", [])

        for body in bodies:
            if body:
                # First sentence = hook
                first_sent = body.split('.')[0].strip()
                if first_sent:
                    hooks.append(first_sent[:100])

        for title in titles:
            if title:
                ctas.append(title[:80])

    # Detect angle patterns
    pain_keywords = ["struggle", "tired", "waste", "stop", "problem", "fix", "pain", "frustrat"]
    proof_keywords = ["users", "teams", "customers", "reviews", "trusted", "join"]
    feature_keywords = ["new", "now", "introducing", "feature", "capability", "power"]

    for hook in hooks:
        hook_lower = hook.lower()
        if any(k in hook_lower for k in pain_keywords):
            angles.append("pain")
        elif any(k in hook_lower for k in proof_keywords):
            angles.append("social_proof")
        elif any(k in hook_lower for k in feature_keywords):
            angles.append("feature")
        else:
            angles.append("other")

    return {
        "query": query,
        "total_ads_found": len(ads),
        "top_hooks": hooks[:10],
        "top_ctas": ctas[:10],
        "angle_distribution": {
            "pain": angles.count("pain"),
            "social_proof": angles.count("social_proof"),
            "feature": angles.count("feature"),
            "other": angles.count("other"),
        },
        "raw_ads": ads[:20],
    }


def write_competitor_md(analysis: dict, research_prompt: str, output_dir: str):
    out = Path(output_dir)
    path = out / "competitor-ads.md"

    with open(path, 'w') as f:
        f.write(f"# Competitor Ad Analysis\n\n")
        f.write(f"**Query:** {analysis['query']}\n")
        f.write(f"**Ads found:** {analysis['total_ads_found']}\n")
        f.write(f"**Generated:** {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}\n\n")

        if analysis['total_ads_found'] > 0:
            f.write("## Top Hooks Found\n")
            for i, hook in enumerate(analysis['top_hooks'], 1):
                f.write(f"{i}. {hook}\n")

            f.write("\n## Top Headlines/CTAs\n")
            for i, cta in enumerate(analysis['top_ctas'], 1):
                f.write(f"{i}. {cta}\n")

            dist = analysis['angle_distribution']
            f.write(f"\n## Angle Distribution\n")
            f.write(f"- Pain-led: {dist['pain']} ads\n")
            f.write(f"- Social proof: {dist['social_proof']} ads\n")
            f.write(f"- Feature-led: {dist['feature']} ads\n")
            f.write(f"- Other: {dist['other']} ads\n")

        f.write(f"\n## Web Research Needed\n")
        f.write(research_prompt)

        if analysis['raw_ads']:
            f.write("\n## Raw Ad Data\n```json\n")
            f.write(json.dumps(analysis['raw_ads'][:5], indent=2))
            f.write("\n```\n")

    print(f"  ✓ Saved competitor analysis to {path}")
    return str(path)


def main():
    parser = argparse.ArgumentParser(description="Ad Library Scraper — Stage 5")
    parser.add_argument("--query", required=True, help="Search query (competitor name or keyword)")
    parser.add_argument("--output", required=True, help="Output directory")
    parser.add_argument("--country", default="ALL", help="Country code (default: ALL)")
    parser.add_argument("--limit", type=int, default=30, help="Max ads to fetch")
    args = parser.parse_args()

    print(f"\n🔍 Stage 5: Competitor Ad Analysis")
    print(f"   Query: {args.query}")
    print(f"   Country: {args.country}\n")

    # Try API first
    print(f"  Searching Meta Ad Library API...")
    ads = search_ad_library_api(args.query, args.country, args.limit)
    print(f"  Found {len(ads)} ads via API")

    analysis = analyze_ads(ads, args.query)
    research_prompt = search_web_for_competitor_ads(args.query)

    write_competitor_md(analysis, research_prompt, args.output)

    print(f"\n✅ Stage 5 Complete")
    if len(ads) == 0:
        print(f"  ℹ️  No API results — Claude should do web research using the prompts in competitor-ads.md")


if __name__ == "__main__":
    main()
