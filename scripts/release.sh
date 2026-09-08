#!/usr/bin/env bash
# XTC LIVE release packaging (V13-RC2)
# Prevents ephemeral CI runners from clobbering production tags.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

TAG="${1:-}"
MODE="${2:-}"

usage() {
  cat <<'EOF'
Usage: ./scripts/release.sh <tag> [--final-verified]

Examples:
  ./scripts/release.sh v13-rc2
  ./scripts/release.sh v13-rc2 --final-verified
EOF
}

if [[ -z "${TAG}" ]]; then
  usage
  exit 1
fi

if [[ "${TAG}" == "-h" || "${TAG}" == "--help" ]]; then
  usage
  exit 0
fi

# Reject unexpected file injection outside allow-list when RELEASE_STRICT=1
if [[ "${RELEASE_STRICT:-0}" == "1" ]]; then
  mapfile -t dirty < <(git status --porcelain | awk '{print $2}')
  allow_re='^(dist/|artifacts/|package-lock.json)$'
  for f in "${dirty[@]:-}"; do
    [[ -z "${f}" ]] && continue
    if [[ ! "${f}" =~ ${allow_re} ]]; then
      echo "error: unexpected file injection detected: ${f}" >&2
      exit 2
    fi
  done
fi

# Remote registry tag collision check — query refs/tags before creating
if git rev-parse "refs/tags/${TAG}" >/dev/null 2>&1; then
  echo "error: local tag already exists: ${TAG}" >&2
  exit 3
fi

# Also probe remote (best-effort; may be unavailable offline)
if git ls-remote --tags origin "refs/tags/${TAG}" 2>/dev/null | grep -q "refs/tags/${TAG}"; then
  echo "error: remote tag already exists (refusing clobber): ${TAG}" >&2
  exit 3
fi

echo "==> Building release artifact for ${TAG}"
if [[ -f package.json ]]; then
  npm run build
fi

mkdir -p artifacts
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
ARTIFACT="artifacts/xtc-live-${TAG}-${STAMP}.txt"

{
  echo "product=XTC-LIVE"
  echo "tag=${TAG}"
  echo "built_at=${STAMP}"
  echo "git_head=$(git rev-parse HEAD 2>/dev/null || echo unknown)"
  echo "final_verified=$([[ "${MODE}" == "--final-verified" ]] && echo true || echo false)"
  echo "status=PRODUCTION_CANDIDATE"
  echo "unverified=play_14d_closed_test,maia200_50k_soak"
} > "${ARTIFACT}"

echo "==> Wrote ${ARTIFACT}"

if [[ "${MODE}" == "--final-verified" ]]; then
  echo "==> Final-verified packaging complete (immutable artifact path ready)"
  echo "NOTE: Google Play 14-day closed testing and Maia 200 soak remain calendar/hardware gated."
fi

echo "OK ${TAG}"
