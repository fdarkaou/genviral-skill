#!/usr/bin/env python3
"""
Stage 1: Landing Page Analyzer
Scrapes URL, extracts brand identity (colors, fonts, logo), saves structured output.

Usage:
    python3 lp_analyzer.py --url https://genviral.io --output runs/genviral-2026-03-02/
"""

import argparse
import json
import os
import re
import sys
import urllib.request
import urllib.error
from datetime import datetime
from pathlib import Path

# Try to import optional deps
try:
    from html.parser import HTMLParser
except ImportError:
    pass


class BrandExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self.title = ""
        self.meta_desc = ""
        self.meta_og_title = ""
        self.meta_og_desc = ""
        self.og_image = ""
        self.logo_candidates = []
        self.css_links = []
        self.text_blocks = []
        self._in_title = False
        self._current_tag = ""
        self._current_data = []

    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)
        self._current_tag = tag

        if tag == "title":
            self._in_title = True

        elif tag == "meta":
            name = attrs_dict.get("name", "").lower()
            prop = attrs_dict.get("property", "").lower()
            content = attrs_dict.get("content", "")

            if name == "description":
                self.meta_desc = content
            elif prop == "og:title":
                self.meta_og_title = content
            elif prop == "og:description":
                self.meta_og_desc = content
            elif prop == "og:image":
                self.og_image = content

        elif tag == "link":
            rel = attrs_dict.get("rel", "")
            href = attrs_dict.get("href", "")
            if "stylesheet" in rel and href:
                self.css_links.append(href)
            if "icon" in rel or "logo" in href.lower():
                self.logo_candidates.append(href)

        elif tag == "img":
            src = attrs_dict.get("src", "")
            alt = attrs_dict.get("alt", "").lower()
            cls = attrs_dict.get("class", "").lower()
            if "logo" in alt or "logo" in cls or "logo" in src.lower():
                self.logo_candidates.append(src)

    def handle_endtag(self, tag):
        if tag == "title":
            self._in_title = False

    def handle_data(self, data):
        if self._in_title:
            self.title += data
        stripped = data.strip()
        if len(stripped) > 30:  # Only meaningful text blocks
            self.text_blocks.append(stripped)


def fetch_url(url: str, timeout: int = 15) -> str:
    """Fetch URL content with headers that don't get blocked."""
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
    }
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            charset = resp.headers.get_content_charset() or "utf-8"
            return resp.read().decode(charset, errors="replace")
    except Exception as e:
        print(f"  Warning: Could not fetch {url}: {e}", file=sys.stderr)
        return ""


def extract_css_colors(css_content: str) -> list:
    """Extract hex colors and named CSS variables from stylesheet."""
    colors = []
    # Hex colors
    hex_colors = re.findall(r'#[0-9a-fA-F]{3,8}\b', css_content)
    colors.extend(hex_colors[:20])  # Cap at 20
    # CSS variables (brand colors often use --color-primary etc)
    vars_with_colors = re.findall(r'--[\w-]+(?:-color|-primary|-secondary|-accent)[^;:]*:\s*([#\w]+)', css_content)
    colors.extend(vars_with_colors[:10])
    return list(set(colors))


def resolve_url(base: str, relative: str) -> str:
    """Resolve a relative URL against a base."""
    if relative.startswith("http"):
        return relative
    from urllib.parse import urljoin
    return urljoin(base, relative)


def analyze_lp(url: str, output_dir: str) -> dict:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    print(f"  Fetching {url}...")
    html = fetch_url(url)
    if not html:
        print("  ERROR: Could not fetch LP", file=sys.stderr)
        sys.exit(1)

    # Parse HTML
    extractor = BrandExtractor()
    try:
        extractor.feed(html)
    except Exception:
        pass  # HTMLParser errors are non-fatal

    # Extract text content (strip HTML tags)
    clean_text = re.sub(r'<[^>]+>', ' ', html)
    clean_text = re.sub(r'\s+', ' ', clean_text).strip()

    # Save raw LP text
    lp_text_path = out / "lp-content.md"
    meaningful_text = '\n\n'.join([b for b in extractor.text_blocks if len(b) > 50][:50])
    with open(lp_text_path, 'w') as f:
        f.write(f"# LP Content: {url}\n\n")
        f.write(f"**Title:** {extractor.title.strip()}\n\n")
        f.write(f"**Meta Description:** {extractor.meta_desc}\n\n")
        f.write(f"**OG Title:** {extractor.meta_og_title}\n\n")
        f.write(f"**OG Description:** {extractor.meta_og_desc}\n\n")
        f.write(f"## Key Text Blocks\n\n{meaningful_text}\n")
    print(f"  ✓ Saved LP content to {lp_text_path}")

    # Fetch first CSS file for brand colors
    colors = []
    if extractor.css_links:
        css_url = resolve_url(url, extractor.css_links[0])
        print(f"  Fetching CSS: {css_url}...")
        css_content = fetch_url(css_url, timeout=10)
        if css_content:
            colors = extract_css_colors(css_content)

    # Logo
    logo_url = ""
    if extractor.logo_candidates:
        logo_url = resolve_url(url, extractor.logo_candidates[0])
    elif extractor.og_image:
        logo_url = extractor.og_image

    # Download logo
    logo_path = ""
    if logo_url:
        logo_filename = "logo" + (os.path.splitext(logo_url)[-1] or ".png")
        logo_path = str(out / logo_filename)
        try:
            urllib.request.urlretrieve(logo_url, logo_path)
            print(f"  ✓ Downloaded logo to {logo_path}")
        except Exception as e:
            print(f"  Warning: Could not download logo: {e}", file=sys.stderr)
            logo_path = ""

    # Build brand.json
    brand = {
        "url": url,
        "title": extractor.title.strip(),
        "description": extractor.meta_desc or extractor.meta_og_desc,
        "og_title": extractor.meta_og_title,
        "colors_extracted": colors[:10],
        "primary_color": colors[0] if colors else "#000000",
        "logo_url": logo_url,
        "logo_local": logo_path,
        "og_image": extractor.og_image,
        "extracted_at": datetime.utcnow().isoformat() + "Z",
    }

    brand_path = out / "brand.json"
    with open(brand_path, 'w') as f:
        json.dump(brand, f, indent=2)
    print(f"  ✓ Saved brand identity to {brand_path}")

    return brand


def main():
    parser = argparse.ArgumentParser(description="LP Analyzer — Stage 1")
    parser.add_argument("--url", required=True, help="Landing page URL")
    parser.add_argument("--output", required=True, help="Output directory (run dir)")
    args = parser.parse_args()

    print(f"\n🔍 Stage 1: LP Analysis")
    print(f"   URL: {args.url}")
    print(f"   Output: {args.output}\n")

    brand = analyze_lp(args.url, args.output)

    print(f"\n✅ Stage 1 Complete")
    print(f"   Title: {brand['title']}")
    print(f"   Description: {brand['description'][:100]}..." if brand['description'] else "   No meta description found")
    print(f"   Colors found: {len(brand['colors_extracted'])}")
    print(f"   Logo: {'✓' if brand['logo_local'] else '✗ Not found'}")


if __name__ == "__main__":
    main()
