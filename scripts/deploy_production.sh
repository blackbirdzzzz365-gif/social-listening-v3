#!/usr/bin/env bash
set -euo pipefail

APP_DIR="${APP_DIR:-/home/ubuntu/social-listening-v3}"
DEPLOY_SHA="${DEPLOY_SHA:?DEPLOY_SHA is required}"
IMAGE_REF="${IMAGE_REF:?IMAGE_REF is required}"
PREVIOUS_HEAD="${PREVIOUS_HEAD:-}"

cd "$APP_DIR"

deploy_dir="${APP_DIR}/.deploy"
state_file="${deploy_dir}/production-state.env"
deploy_env_file="${deploy_dir}/deploy.env"

mkdir -p "$deploy_dir"

if [ -n "${GHCR_USERNAME:-}" ] && [ -n "${GHCR_TOKEN:-}" ]; then
  printf '%s' "$GHCR_TOKEN" | docker login ghcr.io -u "$GHCR_USERNAME" --password-stdin
fi

previous_sha=""
previous_image_ref=""
if [ -f "$state_file" ]; then
  # shellcheck disable=SC1090
  . "$state_file"
  previous_sha="${CURRENT_SHA:-${PREVIOUS_SHA:-}}"
  previous_image_ref="${CURRENT_IMAGE_REF:-}"
fi

if [ -z "$previous_sha" ] && [ -n "$PREVIOUS_HEAD" ]; then
  previous_sha="$PREVIOUS_HEAD"
fi

cat > "$deploy_env_file" <<EOF
IMAGE_REF=${IMAGE_REF}
DEPLOY_SHA=${DEPLOY_SHA}
EOF

docker compose --env-file .env --env-file "$deploy_env_file" -f docker-compose.production.yml pull
docker compose --env-file .env --env-file "$deploy_env_file" -f docker-compose.production.yml up -d --remove-orphans

APP_DIR="$APP_DIR" scripts/healthcheck_production.sh

deployed_at="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
cat > "$state_file" <<EOF
CURRENT_SHA=${DEPLOY_SHA}
CURRENT_IMAGE_REF=${IMAGE_REF}
PREVIOUS_SHA=${previous_sha}
PREVIOUS_IMAGE_REF=${previous_image_ref}
DEPLOYED_AT=${deployed_at}
EOF

docker compose --env-file .env --env-file "$deploy_env_file" -f docker-compose.production.yml ps
