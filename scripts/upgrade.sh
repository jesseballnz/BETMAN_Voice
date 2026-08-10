#!/usr/bin/env bash
set -euo pipefail

scripts/backup.sh
git pull --ff-only
docker compose up -d --build
docker compose exec -T api alembic upgrade head
curl -fsS http://127.0.0.1:8088/health
