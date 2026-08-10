#!/usr/bin/env bash
set -euo pipefail

if [ $# -lt 1 ]; then
  echo "usage: scripts/restore.sh backups/betman_voice_YYYYMMDD.sql"
  exit 2
fi

docker compose exec -T postgres psql \
  -U "${POSTGRES_USER:-betman_voice}" \
  -d "${POSTGRES_DB:-betman_voice}" \
  < "$1"
