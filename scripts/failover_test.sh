#!/usr/bin/env bash
set -euo pipefail

docker compose stop worker
curl -fsS http://127.0.0.1:8088/health >/dev/null
docker compose start worker
sleep 5
curl -fsS http://127.0.0.1:8088/health >/dev/null
docker compose stop api
docker compose start api
sleep 5
curl -fsS http://127.0.0.1:8088/health >/dev/null
echo "failover smoke test passed"
