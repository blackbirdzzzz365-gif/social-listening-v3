#!/usr/bin/env bash
set -euo pipefail

APP_DIR="${APP_DIR:-/home/ubuntu/social-listening-v3}"
ROLLBACK_SHA="${ROLLBACK_SHA:-}"

cd "$APP_DIR"

git config core.fileMode false

state_file="${APP_DIR}/.deploy/production-state.env"
if [ ! -f "$state_file" ]; then
  echo "Missing ${state_file}; cannot determine rollback target." >&2
  exit 1
fi

# shellcheck disable=SC1090
. "$state_file"

target_sha="${ROLLBACK_SHA:-${PREVIOUS_SHA:-}}"
if [ -z "$target_sha" ]; then
  echo "No rollback target SHA was provided and no PREVIOUS_SHA is recorded." >&2
  exit 1
fi

owner_lc="$(git remote get-url origin | sed -E 's#(git@|https://)github.com[:/]([^/]+)/.*#\2#' | tr '[:upper:]' '[:lower:]')"
image_ref="ghcr.io/${owner_lc}/social-listening-v3:sha-${target_sha}"

current_sha="${CURRENT_SHA:-}"
current_image_ref="${CURRENT_IMAGE_REF:-}"

git fetch origin --prune
git checkout --detach "$target_sha"

APP_DIR="$APP_DIR" DEPLOY_SHA="$target_sha" IMAGE_REF="$image_ref" PREVIOUS_HEAD="${current_sha}" scripts/deploy_production.sh

cat > "$state_file" <<EOF
CURRENT_SHA=${target_sha}
CURRENT_IMAGE_REF=${image_ref}
PREVIOUS_SHA=${current_sha}
PREVIOUS_IMAGE_REF=${current_image_ref}
DEPLOYED_AT=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
EOF
