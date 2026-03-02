#!/usr/bin/env python3
"""
Step 1: Daily Health Check
Answers the same 5 questions every morning:
  1. Am I on track?          (spend vs budget)
  2. What's running?         (active campaigns/adsets)
  3. Who's winning?          (lowest CPA, best ROAS)
  4. Who's bleeding?         (highest CPA, overspending)
  5. Any fatigue?            (frequency alerts)

Output: JSON to stdout + human-readable summary to stderr
Usage:
    python3 health_check.py [--product genviral] [--days 7] [--json]
"""

import argparse
import json
import sys
import os
from datetime import datetime, timezone, timedelta

sys.path.insert(0, os.path.dirname(__file__))
from meta_api import MetaAPI, load_config

FREQ_WARN = 3.0    # Start watching
FREQ_ALERT = 3.5   # Audience is cooked
CPA_WARN_MULTIPLIER = 2.0
CPA_ALERT_MULTIPLIER = 2.5


def run_health_check(product: str, config: dict, days: int = 7) -> dict:
    product_cfg = config["products"][product]
    api = MetaAPI(
        access_token=config["access_token"],
        ad_account_id=product_cfg["ad_account_id"],
    )
    target_cpa = product_cfg.get("target_cpa", None)
    action_type = product_cfg.get("action_type", "purchase")

    # Use explicit time_range to avoid invalid date_preset values
    # (Meta only supports: last_3d, last_7d, last_14d, last_28d, last_30d, last_90d)
    today = datetime.now(timezone.utc).date()
    date_stop = today.isoformat()
    date_start = (today - timedelta(days=max(1, days) - 1)).isoformat()

    # 1. Account info
    acct = api.get_account_info()
    print(f"[health] Account: {acct['name']} | Currency: {acct['currency']}", file=sys.stderr)

    # 2. Campaign-level insights
    campaign_insights = api.get_insights(
        level="campaign",
        date_start=date_start,
        date_stop=date_stop,
        action_type=action_type,
    )

    # 3. Ad-set level for frequency + budget data
    adset_insights = api.get_insights(
        level="adset",
        date_start=date_start,
        date_stop=date_stop,
        action_type=action_type,
    )

    # ── Compute winners/losers ──
    # Filter to rows with actual spend
    active = [r for r in campaign_insights if r["spend"] > 0]
    active.sort(key=lambda x: x["target_cpa"] if x["target_cpa"] else float("inf"))

    winners = []
    bleeders = []

    for row in active:
        cpa = row.get("target_cpa")
        spend = row["spend"]
        name = row.get("campaign_name", row.get("campaign_id", "?"))
        roas_list = row.get("purchase_roas", [])
        roas = float(roas_list[0]["value"]) if roas_list else None

        entry = {
            "name": name,
            "id": row.get("campaign_id"),
            "spend": spend,
            "cpa": cpa,
            "conversions": row.get("target_action_count", 0),
            "roas": roas,
            "frequency": row.get("frequency", 0),
            "ctr": row.get("ctr", 0),
        }

        if target_cpa and cpa:
            if cpa > target_cpa * CPA_ALERT_MULTIPLIER:
                entry["status"] = "BLEEDING"
                bleeders.append(entry)
            elif cpa < target_cpa * 0.8:
                entry["status"] = "WINNING"
                winners.append(entry)
            else:
                entry["status"] = "OK"
        elif cpa and not target_cpa:
            # No target set — still track by CPA
            entry["status"] = "NO_TARGET"
            winners.append(entry)
        else:
            # No CPA data (no conversions yet) — don't call it a winner
            entry["status"] = "INSUFFICIENT_DATA"

    # ── Frequency alerts (adset level) ──
    freq_alerts = []
    for row in adset_insights:
        freq = row.get("frequency", 0)
        if freq >= FREQ_WARN:
            freq_alerts.append({
                "adset_id": row.get("adset_id"),
                "adset_name": row.get("adset_name", "?"),
                "frequency": freq,
                "severity": "HIGH" if freq >= FREQ_ALERT else "WARN",
                "spend": row["spend"],
                "ctr": row.get("ctr", 0),
            })
    freq_alerts.sort(key=lambda x: x["frequency"], reverse=True)

    # ── Total spend / on-track ──
    total_spend = sum(r["spend"] for r in campaign_insights)
    total_conversions = sum(r.get("target_action_count", 0) for r in campaign_insights)
    blended_cpa = (total_spend / total_conversions) if total_conversions > 0 else None

    result = {
        "product": product,
        "account": acct["name"],
        "period_days": days,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "summary": {
            "total_spend": total_spend,
            "total_conversions": total_conversions,
            "blended_cpa": blended_cpa,
            "target_cpa": target_cpa,
            "on_track": (blended_cpa <= target_cpa * 1.2) if (blended_cpa is not None and target_cpa is not None) else None,
        },
        "winners": winners[:5],
        "bleeders": bleeders[:5],
        "frequency_alerts": freq_alerts,
        "raw_campaigns": campaign_insights,
    }

    return result


def format_human(result: dict) -> str:
    s = result["summary"]
    lines = [
        f"📊 Meta Ads Health — {result['product'].upper()} ({result['period_days']}d)",
        f"Account: {result['account']}",
        "",
        f"💰 Spend: ${s['total_spend']:.2f}",
        f"🎯 Conversions: {s['total_conversions']}",
        f"📉 Blended CPA: ${s['blended_cpa']:.2f}" if s['blended_cpa'] is not None else "📉 Blended CPA: N/A",
        f"🏹 Target CPA: ${s['target_cpa']:.2f}" if s['target_cpa'] is not None else "🏹 Target CPA: not set",
    ]

    if s["on_track"] is not None:
        lines.append("✅ ON TRACK" if s["on_track"] else "🚨 OFF TRACK")

    if result["winners"]:
        lines.append("\n🏆 WINNERS:")
        for w in result["winners"][:3]:
            cpa_str = f"CPA ${w['cpa']:.2f}" if w["cpa"] is not None else "CPA N/A"
            roas_str = f"ROAS {w['roas']:.1f}x" if w["roas"] is not None else ""
            lines.append(f"  • {w['name']} — {cpa_str} {roas_str} | Spend ${w['spend']:.2f}")

    if result["bleeders"]:
        lines.append("\n🩸 BLEEDERS:")
        for b in result["bleeders"][:3]:
            cpa_str = f"CPA ${b['cpa']:.2f}" if b["cpa"] is not None else "CPA N/A"
            lines.append(f"  • {b['name']} — {cpa_str} | Spend ${b['spend']:.2f}")

    if result["frequency_alerts"]:
        lines.append("\n⚠️  FREQUENCY ALERTS:")
        for f in result["frequency_alerts"][:5]:
            icon = "🚨" if f["severity"] == "HIGH" else "⚠️"
            lines.append(f"  {icon} {f['adset_name']} — freq {f['frequency']:.1f} | CTR {f['ctr']:.2f}%")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Meta Ads daily health check")
    parser.add_argument("--product", required=True, help="Product name (must match config.yaml)")
    parser.add_argument("--days", type=int, default=7, help="Lookback window in days (default: 7)")
    parser.add_argument("--json", action="store_true", help="Output raw JSON instead of summary")
    parser.add_argument("--config", help="Path to config.yaml")
    args = parser.parse_args()

    config = load_config(args.config)
    result = run_health_check(args.product, config, days=args.days)

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(format_human(result))

    # Always write JSON to data dir for other scripts to consume
    data_dir = os.path.join(os.path.dirname(__file__), "..", "data")
    os.makedirs(data_dir, exist_ok=True)
    out_path = os.path.join(data_dir, f"health-{args.product}-latest.json")
    with open(out_path, "w") as f:
        json.dump(result, f, indent=2)
    print(f"\n[saved → {out_path}]", file=sys.stderr)


if __name__ == "__main__":
    main()
