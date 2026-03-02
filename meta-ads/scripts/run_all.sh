#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────
# Meta Ads Full Pipeline Runner
# Runs all steps in sequence for one or all products.
#
# Usage:
#   ./run_all.sh                          # all products from config
#   ./run_all.sh genviral                 # single product
#   ./run_all.sh --dry-run                # no API mutations
#   ./run_all.sh --skip-copy              # skip copy generation (saves Claude API calls)
#   ./run_all.sh --brief-only             # just regenerate the brief from cached data
# ─────────────────────────────────────────────────────────────

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_DIR="$(dirname "$SCRIPT_DIR")"
CONFIG="$SKILL_DIR/config.yaml"
PYTHON="${PYTHON:-python3}"

DRY_RUN=""
SKIP_COPY=false
BRIEF_ONLY=false
PRODUCT=""

for arg in "$@"; do
  case $arg in
    --dry-run) DRY_RUN="--dry-run" ;;
    --skip-copy) SKIP_COPY=true ;;
    --brief-only) BRIEF_ONLY=true ;;
    --*) echo "Unknown flag: $arg"; exit 1 ;;
    *) PRODUCT="$arg" ;;
  esac
done

# Get product list from config
if [ -n "$PRODUCT" ]; then
  PRODUCTS="$PRODUCT"
else
  # Parse all product keys from config.yaml
  PRODUCTS=$(python3 -c "
import yaml, sys
with open('$CONFIG') as f:
    cfg = yaml.safe_load(f)
print(','.join(cfg['products'].keys()))
")
fi

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🔄 Meta Ads Pipeline — $(date '+%Y-%m-%d %H:%M UTC')"
echo "Products: $PRODUCTS"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if [ "$BRIEF_ONLY" = true ]; then
  echo "[brief-only] Generating brief from cached data…"
  $PYTHON "$SCRIPT_DIR/morning_brief.py" --products "$PRODUCTS"
  exit 0
fi

IFS=',' read -ra PRODUCT_LIST <<< "$PRODUCTS"

for product in "${PRODUCT_LIST[@]}"; do
  echo ""
  echo "── $product ──────────────────────────────"

  echo "▶ Step 1: Health check…"
  $PYTHON "$SCRIPT_DIR/health_check.py" --product "$product" --config "$CONFIG" || {
    echo "⚠️  Health check failed for $product — continuing"
  }

  echo "▶ Step 2: Auto-optimizer…"
  $PYTHON "$SCRIPT_DIR/auto_optimize.py" --product "$product" --config "$CONFIG" ${DRY_RUN:+"$DRY_RUN"} || {
    echo "⚠️  Optimizer failed for $product — continuing"
  }

  if [ "$SKIP_COPY" = false ]; then
    echo "▶ Step 3: Copy generator…"
    $PYTHON "$SCRIPT_DIR/copy_generator.py" --product "$product" --config "$CONFIG" || {
      echo "⚠️  Copy generator failed for $product — continuing"
    }
  else
    echo "▶ Step 3: Copy generator skipped (--skip-copy)"
  fi
done

echo ""
echo "▶ Step 4: Morning brief…"
$PYTHON "$SCRIPT_DIR/morning_brief.py" --products "$PRODUCTS"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ Pipeline complete — $(date '+%H:%M UTC')"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
