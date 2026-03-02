#!/usr/bin/env python3
"""
Meta Campaign Orchestrator
Manages the 8-stage workflow: creates run directory, tracks progress, handles stage execution.

Usage:
    python3 orchestrate.py --url https://genviral.io --product genviral
    python3 orchestrate.py --url https://genviral.io --from-stage 6
    python3 orchestrate.py --url https://genviral.io --dry-run
"""

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

SCRIPTS_DIR = Path(__file__).parent
SKILL_DIR = SCRIPTS_DIR.parent

STAGES = [
    {"id": 1, "name": "Brief & LP Analysis", "auto": True},
    {"id": 2, "name": "Deep Interview", "auto": False},  # Human
    {"id": 3, "name": "Customer Roleplay (Opus)", "auto": True},
    {"id": 4, "name": "Market Research (Opus)", "auto": True},
    {"id": 5, "name": "Competitive Analysis", "auto": True},
    {"id": 6, "name": "Campaign Strategy", "auto": False, "approval": True},
    {"id": 7, "name": "Creative Generation", "auto": True, "approval": True},
    {"id": 8, "name": "Final Delivery", "auto": True, "approval": True},
]


def create_run_dir(product: str) -> str:
    date = datetime.utcnow().strftime("%Y-%m-%d")
    run_dir = SKILL_DIR.parent / "runs" / f"{product}-{date}"
    # Handle multiple runs per day
    suffix = 0
    while run_dir.exists() and suffix < 10:
        suffix += 1
        run_dir = SKILL_DIR.parent / "runs" / f"{product}-{date}-{suffix}"
    run_dir.mkdir(parents=True, exist_ok=True)
    return str(run_dir)


def save_progress(run_dir: str, stage: int, status: str, data: dict = None):
    progress_file = Path(run_dir) / "progress.json"
    progress = {}
    if progress_file.exists():
        with open(progress_file) as f:
            progress = json.load(f)

    progress[f"stage_{stage}"] = {
        "status": status,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        **(data or {}),
    }
    with open(progress_file, "w") as f:
        json.dump(progress, f, indent=2)


def load_progress(run_dir: str) -> dict:
    progress_file = Path(run_dir) / "progress.json"
    if not progress_file.exists():
        return {}
    with open(progress_file) as f:
        return json.load(f)


def run_stage_1(run_dir: str, url: str, dry_run: bool = False) -> bool:
    print(f"\n{'='*60}")
    print(f"STAGE 1: Brief & LP Analysis")
    print(f"{'='*60}")

    if dry_run:
        print(f"  [DRY RUN] Would analyze: {url}")
        return True

    cmd = [sys.executable, str(SCRIPTS_DIR / "lp_analyzer.py"), "--url", url, "--output", run_dir]
    result = subprocess.run(cmd, capture_output=False)
    success = result.returncode == 0
    save_progress(run_dir, 1, "done" if success else "failed", {"url": url})
    return success


def run_stage_5(run_dir: str, query: str, dry_run: bool = False) -> bool:
    print(f"\n{'='*60}")
    print(f"STAGE 5: Competitive Analysis")
    print(f"{'='*60}")
    print(f"  Searching for competitor ads: '{query}'")

    if dry_run:
        print(f"  [DRY RUN] Would search Meta Ad Library for: {query}")
        return True

    cmd = [sys.executable, str(SCRIPTS_DIR / "ad_library.py"), "--query", query, "--output", run_dir]
    result = subprocess.run(cmd, capture_output=False)
    success = result.returncode == 0
    save_progress(run_dir, 5, "done" if success else "failed")
    return success


def print_stage_header(stage_num: int, stage_name: str):
    print(f"\n{'='*60}")
    print(f"STAGE {stage_num}: {stage_name}")
    print(f"{'='*60}")


def print_handoff_instructions(run_dir: str, product: str):
    """Print instructions for Claude Code to take over the complex stages."""
    print(f"""
{'='*60}
HANDOFF TO CLAUDE (Atlas)
{'='*60}
Run directory: {run_dir}

The following stages require Claude's reasoning:

STAGE 2 — Deep Interview:
  Ask Fekri these 5 questions (one at a time), save answers to {run_dir}/interview.md

STAGE 3+4 — Parallel Opus Research:
  Read references/stage-prompts.md for exact prompts
  Launch both as parallel Task sub-agents (both write to {run_dir}/)

STAGE 6 — Campaign Strategy:
  Read: brand.json, interview.md, customer-profile.md, market-research.md, competitor-ads.md
  Write: strategy.md with 4-5 scored angles
  Present to Fekri → wait for approval

STAGE 7 — Creative Generation:
  Run: python3 scripts/generate_creatives.py --rundir {run_dir} --all
  OR generate per ad set:
  python3 scripts/generate_creatives.py --rundir {run_dir} --ad-set ad-set-01-NAME

STAGE 8 — Upload (after approval):
  python3 scripts/upload_to_meta.py --rundir {run_dir} --product {product}
""")


def main():
    parser = argparse.ArgumentParser(description="Meta Campaign Orchestrator")
    parser.add_argument("--url", required=True, help="Landing page URL")
    parser.add_argument("--product", default="genviral", help="Product name (default: genviral)")
    parser.add_argument("--from-stage", type=int, default=1, help="Resume from stage N")
    parser.add_argument("--dry-run", action="store_true", help="No mutations, show what would happen")
    args = parser.parse_args()

    print(f"""
╔══════════════════════════════════════════════════════════╗
║          META CAMPAIGN BUILDER — /meta-campaign          ║
╚══════════════════════════════════════════════════════════╝
  URL: {args.url}
  Product: {args.product}
  Starting from: Stage {args.from_stage}
  Mode: {'DRY RUN' if args.dry_run else 'LIVE'}
""")

    # Create or find run directory
    if args.from_stage == 1:
        run_dir = create_run_dir(args.product)
        print(f"  📁 Run directory: {run_dir}\n")
    else:
        # Find most recent run for this product
        runs_dir = SKILL_DIR.parent / "runs"
        candidates = sorted([d for d in runs_dir.glob(f"{args.product}-*") if d.is_dir()], reverse=True)
        if not candidates:
            print(f"  ERROR: No existing runs for product '{args.product}'", file=sys.stderr)
            sys.exit(1)
        run_dir = str(candidates[0])
        print(f"  📁 Resuming run: {run_dir}\n")

    # Extract product name / search query from URL
    from urllib.parse import urlparse
    domain = urlparse(args.url).netloc.replace("www.", "").split(".")[0]

    # Stage 1: LP Analysis (auto)
    if args.from_stage <= 1:
        if not run_stage_1(run_dir, args.url, args.dry_run):
            print("\n  ✗ Stage 1 failed. Check errors above.", file=sys.stderr)
            sys.exit(1)

    # Stage 5: Competitor analysis (auto, but do it before strategy)
    if args.from_stage <= 5:
        run_stage_5(run_dir, domain, args.dry_run)

    # Print handoff instructions for Claude-driven stages
    print_handoff_instructions(run_dir, args.product)

    # Write a session file for easy resumption
    session_file = Path(run_dir) / "session.json"
    with open(session_file, "w") as f:
        json.dump({
            "url": args.url,
            "product": args.product,
            "run_dir": run_dir,
            "created_at": datetime.utcnow().isoformat() + "Z",
            "status": "awaiting_stage_2_interview",
        }, f, indent=2)

    print(f"  ✅ Automated stages complete. Session saved: {session_file}")
    print(f"  → Continue with Stage 2 (interview) in Claude Code.\n")


if __name__ == "__main__":
    main()
