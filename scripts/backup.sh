#!/usr/bin/env bash
set -euo pipefail

STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
BACKUP_DIR="${BETMAN_VOICE_BACKUP_DIR:-./backups}"
mkdir -p "$BACKUP_DIR"

docker compose exec -T postgres pg_dump \
  -U "${POSTGRES_USER:-betman_voice}" \
  -d "${POSTGRES_DB:-betman_voice}" \
  > "$BACKUP_DIR/betman_voice_$STAMP.sql"

tar -czf "$BACKUP_DIR/betman_voice_audio_$STAMP.tar.gz" data/audio || true
echo "$BACKUP_DIR/betman_voice_$STAMP.sql"
