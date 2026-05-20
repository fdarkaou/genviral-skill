#!/usr/bin/env bash
# Thin wrapper around the @genviral/cli npm package.
# Installs: npm install -g @genviral/cli
set -euo pipefail

SKILL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if ! command -v genviral >/dev/null 2>&1; then
  cat >&2 <<'EOF'
genviral CLI is not installed.

Install globally:
  npm install -g @genviral/cli

Local install from the monorepo (before npm publish):
  pnpm --filter @genviral/partner-api-contracts pack --pack-destination /tmp
  pnpm --filter @genviral/cli pack --pack-destination /tmp
  npm install -g /tmp/genviral-partner-api-contracts-0.1.0.tgz /tmp/genviral-cli-0.1.0.tgz
EOF
  exit 127
fi

if [[ -f "${HOME}/.config/env/global.env" ]]; then
  # shellcheck disable=SC1091
  source "${HOME}/.config/env/global.env" 2>/dev/null || true
fi

export GENVIRAL_CONFIG="${GENVIRAL_CONFIG:-$SKILL_DIR/defaults.yaml}"

exec genviral "$@"
