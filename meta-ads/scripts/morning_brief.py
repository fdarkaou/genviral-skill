#!/usr/bin/env python3
"""
Step 6: Morning Brief Compiler
Reads the latest JSON outputs from health_check, auto_optimize, and copy_generator
and compiles a single Telegram-ready morning brief.

Usage:
    python3 morning_brief.py --products genviral,buildfound [--send-telegram]

Output: formatted message ready for Telegram, optionally sent automatically
"""

import argparse
import json
import os
import sys
from datetime import datetime, timezone

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")


def _md_escape(text: str) -> str:
    """Escape Telegram markdown special chars in dynamic content."""
    return str(text).replace("\\", "\\\\").replace("_", "\\_").replace("*", "\\*").replace("[", "\\[").replace("`", "\\`")


def load_latest(filename: str) -> dict | None:
    path = os.path.join(DATA_DIR, filename)
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return None


def build_brief(products: list) -> str:
    now = datetime.now(timezone.utc)
    date_str = now.strftime("%A %b %d")

    lines = [
        f"📊 *Meta Ads Brief — {date_str}*",
        "━━━━━━━━━━━━━━━━━━━━",
    ]

    for product in products:
        health = load_latest(f"health-{product}-latest.json")
        optimize = load_latest(f"optimize-{product}-latest.json")
        copy = load_latest(f"copy-{product}-latest.json")

        lines.append(f"\n*{product.upper()}*")

        if health:
            s = health["summary"]
            spend = s.get("total_spend", 0)
            cpa = s.get("blended_cpa")
            target = s.get("target_cpa")
            convs = s.get("total_conversions", 0)
            on_track = s.get("on_track")

            track_icon = "✅" if on_track else ("🚨" if on_track is False else "❓")
            cpa_str = f"${cpa:.2f}" if cpa else "N/A"
            target_str = f"${target:.2f}" if target else "N/A"

            lines.append(f"{track_icon} Spend: ${spend:.2f} | CPA: {cpa_str} (target: {target_str}) | Conv: {convs}")

            # Freq alerts
            alerts = health.get("frequency_alerts", [])
            high_alerts = [a for a in alerts if a["severity"] == "HIGH"]
            if high_alerts:
                lines.append(f"⚠️ Freq alert: {', '.join(_md_escape(a['adset_name']) for a in high_alerts[:2])}")

            # Top winner
            winners = health.get("winners", [])
            if winners:
                w = winners[0]
                w_cpa = f"${w['cpa']:.2f}" if w.get("cpa") is not None else "N/A CPA"
                lines.append(f"🏆 Best: {_md_escape(w['name'])} — {w_cpa}")

            # Top bleeder
            bleeders = health.get("bleeders", [])
            if bleeders:
                b = bleeders[0]
                b_cpa = f"${b['cpa']:.2f}" if b.get("cpa") is not None else "N/A CPA"
                lines.append(f"🩸 Worst: {_md_escape(b['name'])} — {b_cpa}")
        else:
            lines.append("_(no health data — run health_check.py first)_")

        # Optimizer actions
        if optimize:
            paused = [a for a in optimize.get("actions_taken", []) if a.get("type") == "PAUSE" and a.get("executed")]
            recs = optimize.get("scaling_recommendations", [])
            if paused:
                lines.append(f"🛑 Auto-paused: {', '.join(_md_escape(a['adset_name']) for a in paused[:3])}")
            if recs:
                lines.append(f"📈 Scale recs: {len(recs)} adset(s) ready to scale")

        # New copy
        if copy:
            n = len(copy.get("new_variations", []))
            if n > 0:
                lines.append(f"✍️ {n} new copy variations ready")

    lines.append("\n━━━━━━━━━━━━━━━━━━━━")
    lines.append("Reply _approve_ to greenlight scale recs\nReply _copy_ for new ad variations\nReply _pause_ to review auto-actions")

    return "\n".join(lines)


def send_to_telegram(message: str):
    """Send brief via OpenClaw's internal messaging (just prints for now — Atlas handles the actual send)."""
    # In practice, Atlas (me) will call message tool with this text
    # This function writes to a trigger file that the cron job / Atlas picks up
    trigger_path = os.path.join(DATA_DIR, "brief-pending.txt")
    with open(trigger_path, "w") as f:
        f.write(message)
    print(f"[morning-brief] Brief written to {trigger_path} — Atlas will send it", file=sys.stderr)


def main():
    parser = argparse.ArgumentParser(description="Compile and send Meta Ads morning brief")
    parser.add_argument("--products", required=True, help="Comma-separated product names")
    parser.add_argument("--send-telegram", action="store_true", help="Write brief to pending file for Atlas to send")
    args = parser.parse_args()

    products = [p.strip() for p in args.products.split(",")]
    brief = build_brief(products)

    print(brief)

    if args.send_telegram:
        send_to_telegram(brief)

    # Also save
    os.makedirs(DATA_DIR, exist_ok=True)
    out_path = os.path.join(DATA_DIR, "brief-latest.txt")
    with open(out_path, "w") as f:
        f.write(brief)


if __name__ == "__main__":
    main()
