#!/usr/bin/env bash
set -euo pipefail

HOST="${BETMAN_VOICE_DEPLOY_HOST:-root@170.64.201.92}"
APP_DIR="${BETMAN_VOICE_REMOTE_DIR:-/opt/betman/BETMAN_Voice}"

ssh "$HOST" "mkdir -p '$APP_DIR'"
rsync -az --delete \
  --exclude '.git' \
  --exclude '.env' \
  --exclude 'data' \
  --exclude 'models' \
  ./ "$HOST:$APP_DIR/"

ssh "$HOST" "cd '$APP_DIR' && \
  if [ ! -f .env ]; then cp .env.example .env; fi && \
  docker compose pull postgres || true && \
  docker compose up -d --build && \
  docker compose ps && \
  curl -fsS http://127.0.0.1:8088/health"
