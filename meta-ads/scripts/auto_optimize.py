#!/usr/bin/env python3
"""
Step 3: Auto-Optimizer — Pause Bleeders + Recommend Budget Shifts

Rules:
  PAUSE:  adset CPA > target_cpa * 2.5x  AND  this condition has persisted 48h
          OR adset frequency > 3.5 (audience saturated)
  SCALE:  adset CPA < target_cpa * 0.8 AND spend < daily_budget cap

The 48h check uses a rolling CPA history file stored in data/cpa-history/{product}.json.
On first run it seeds the history. On second run (48h later) it compares.

Usage:
    python3 auto_optimize.py --product genviral [--dry-run] [--config config.yaml]
    
    --dry-run: show what WOULD happen, make no API calls

Output: summary of actions taken (or planned in dry-run mode)
"""

import argparse
import json
import os
import sys
from datetime import datetime, timezone, timedelta

sys.path.insert(0, os.path.dirname(__file__))
from meta_api import MetaAPI, load_config

CPA_PAUSE_MULTIPLIER = 2.5
CPA_SCALE_THRESHOLD = 0.8
FREQ_PAUSE = 3.5
BUDGET_SCALE_FACTOR = 1.20   # increase winner budget by 20%
MIN_SPEND_TO_JUDGE = 10.0    # don't judge adsets with < $10 spend
HISTORY_WINDOW_HOURS = 48


def load_history(product: str, data_dir: str) -> dict:
    path = os.path.join(data_dir, "cpa-history", f"{product}.json")
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return {}


def save_history(product: str, data_dir: str, history: dict):
    path = os.path.join(data_dir, "cpa-history", f"{product}.json")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(history, f, indent=2)


def is_persistently_bad(adset_id: str, current_cpa: float, target_cpa: float, history: dict) -> bool:
    """Check if CPA has been > 2.5x target for the last 48h."""
    key = str(adset_id)
    now = datetime.now(timezone.utc).timestamp()
    threshold = target_cpa * CPA_PAUSE_MULTIPLIER

    if current_cpa <= threshold:
        return False

    if key not in history:
        return False  # First observation — seed it, don't act yet

    entry = history[key]
    first_bad_ts = entry.get("first_bad_ts")
    if not first_bad_ts:
        return False

    hours_bad = (now - first_bad_ts) / 3600
    return hours_bad >= HISTORY_WINDOW_HOURS


def update_history(adset_id: str, current_cpa: float, target_cpa: float, history: dict):
    key = str(adset_id)
    now = datetime.now(timezone.utc).timestamp()
    threshold = target_cpa * CPA_PAUSE_MULTIPLIER

    if current_cpa > threshold:
        if key not in history or not history[key].get("first_bad_ts"):
            history[key] = {"first_bad_ts": now, "cpa": current_cpa}
        else:
            history[key]["cpa"] = current_cpa  # Keep first_bad_ts
    else:
        # CPA recovered — reset history
        history.pop(key, None)


def run_optimizer(product: str, config: dict, dry_run: bool = False) -> dict:
    product_cfg = config["products"][product]
    api = MetaAPI(
        access_token=config["access_token"],
        ad_account_id=product_cfg["ad_account_id"],
    )
    target_cpa = product_cfg.get("target_cpa")
    action_type = product_cfg.get("action_type", "purchase")
    data_dir = os.path.join(os.path.dirname(__file__), "..", "data")

    if not target_cpa:
        print(f"[auto-optimize] No target_cpa set for {product} — skipping CPA-based rules", file=sys.stderr)

    # Load CPA history
    history = load_history(product, data_dir)

    # Get adset-level insights (last 2 days for CPA check)
    # Note: "last_2d" is NOT a valid Meta date_preset — use explicit time_range
    now = datetime.now(timezone.utc)
    date_stop = now.strftime("%Y-%m-%d")
    date_start = (now - timedelta(days=2)).strftime("%Y-%m-%d")
    adset_insights = api.get_insights(
        level="adset",
        date_start=date_start,
        date_stop=date_stop,
        action_type=action_type,
    )

    actions_taken = []
    recommendations = []

    for row in adset_insights:
        adset_id = row.get("adset_id")
        name = row.get("adset_name", adset_id)
        spend = row["spend"]
        cpa = row.get("target_cpa")
        freq = row.get("frequency", 0)
        conversions = row.get("target_action_count", 0)

        if spend < MIN_SPEND_TO_JUDGE:
            continue  # Not enough data yet

        # ── Rule 1: Frequency saturation ──
        if freq >= FREQ_PAUSE:
            action = {
                "type": "PAUSE",
                "reason": f"Frequency {freq:.1f} ≥ {FREQ_PAUSE} (audience saturated)",
                "adset_id": adset_id,
                "adset_name": name,
                "spend": spend,
                "frequency": freq,
            }
            if not dry_run:
                try:
                    api.pause_adset(adset_id)
                    action["executed"] = True
                    print(f"[auto-optimize] PAUSED {name} (freq={freq:.1f})", file=sys.stderr)
                except Exception as e:
                    action["executed"] = False
                    action["error"] = str(e)
            actions_taken.append(action)
            continue

        # ── Rule 2: CPA bleeding for 48h ──
        if target_cpa is not None and cpa is not None:
            update_history(adset_id, cpa, target_cpa, history)

            if is_persistently_bad(adset_id, cpa, target_cpa, history):
                action = {
                    "type": "PAUSE",
                    "reason": f"CPA ${cpa:.2f} > {CPA_PAUSE_MULTIPLIER}x target ${target_cpa:.2f} for 48h+",
                    "adset_id": adset_id,
                    "adset_name": name,
                    "spend": spend,
                    "cpa": cpa,
                }
                if not dry_run:
                    try:
                        api.pause_adset(adset_id)
                        action["executed"] = True
                        print(f"[auto-optimize] PAUSED {name} (CPA ${cpa:.2f})", file=sys.stderr)
                    except Exception as e:
                        action["executed"] = False
                        action["error"] = str(e)
                actions_taken.append(action)

            # ── Rule 3: Scale winners ──
            elif cpa < target_cpa * CPA_SCALE_THRESHOLD and conversions >= 5:
                # Recommend scaling — don't auto-scale without confirmation
                recommendations.append({
                    "type": "SCALE",
                    "reason": f"CPA ${cpa:.2f} is {CPA_SCALE_THRESHOLD*100:.0f}%+ below target (${target_cpa:.2f})",
                    "adset_id": adset_id,
                    "adset_name": name,
                    "spend": spend,
                    "cpa": cpa,
                    "conversions": conversions,
                    "suggested_budget_increase": f"+{int((BUDGET_SCALE_FACTOR-1)*100)}%",
                })

    # Save updated history
    if not dry_run:
        save_history(product, data_dir, history)

    result = {
        "product": product,
        "dry_run": dry_run,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "actions_taken": actions_taken,
        "scaling_recommendations": recommendations,
        "adsets_evaluated": len([r for r in adset_insights if r["spend"] >= MIN_SPEND_TO_JUDGE]),
    }
    return result


def format_human(result: dict) -> str:
    lines = [
        f"🤖 Auto-Optimizer — {result['product'].upper()}",
        f"{'[DRY RUN] ' if result['dry_run'] else ''}Evaluated {result['adsets_evaluated']} adsets",
        "",
    ]

    if result["actions_taken"]:
        lines.append("🛑 PAUSED:")
        for a in result["actions_taken"]:
            executed = " ✅" if a.get("executed") else (" ❌ FAILED" if "executed" in a else " (dry run)")
            lines.append(f"  • {a['adset_name']}{executed}")
            lines.append(f"    ↳ {a['reason']}")
    else:
        lines.append("✅ No pauses needed")

    if result["scaling_recommendations"]:
        lines.append("\n📈 SCALE RECOMMENDATIONS:")
        for r in result["scaling_recommendations"]:
            lines.append(f"  • {r['adset_name']} — {r['reason']}")
            lines.append(f"    ↳ Suggested: {r['suggested_budget_increase']} budget ({r['conversions']} conversions @ ${r['cpa']:.2f})")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Auto-pause bleeders, recommend budget shifts")
    parser.add_argument("--product", required=True)
    parser.add_argument("--dry-run", action="store_true", help="Show actions without executing")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--config")
    args = parser.parse_args()

    config = load_config(args.config)
    result = run_optimizer(args.product, config, dry_run=args.dry_run)

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(format_human(result))

    # Save for morning brief
    data_dir = os.path.join(os.path.dirname(__file__), "..", "data")
    os.makedirs(data_dir, exist_ok=True)
    out_path = os.path.join(data_dir, f"optimize-{args.product}-latest.json")
    with open(out_path, "w") as f:
        json.dump(result, f, indent=2)


if __name__ == "__main__":
    main()
