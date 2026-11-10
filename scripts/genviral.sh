#!/usr/bin/env bash
# Thin wrapper around the genviral npm package.
# Installs: npm install -g genviral
set -euo pipefail

SKILL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if ! command -v genviral >/dev/null 2>&1; then
  cat >&2 <<'EOF'
genviral CLI is not installed.

Install globally:
  npm install -g genviral

Local install from the monorepo (before npm publish):
  pnpm --filter genviral pack --pack-destination /tmp
  npm install -g /tmp/genviral-*.tgz
EOF
  exit 127
fi

if [[ -f "${HOME}/.config/env/global.env" ]]; then
  # shellcheck disable=SC1091
  source "${HOME}/.config/env/global.env" 2>/dev/null || true
fi

export GENVIRAL_CONFIG="${GENVIRAL_CONFIG:-$SKILL_DIR/defaults.yaml}"

exec genviral "$@"
