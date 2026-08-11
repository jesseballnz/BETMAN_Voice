# BETMAN_Voice Operations Runbook

## Deploy

```bash
cp .env.example .env
vim .env
scripts/deploy.sh
```

Deployment target defaults to `root@170.64.201.92:/opt/betman/BETMAN_Voice`.

## Health

```bash
curl https://170.64.201.92:8088/health
curl https://170.64.201.92:8088/metrics
ssh root@170.64.201.92 'cd /opt/betman/BETMAN_Voice && docker compose ps'
```

## Logs

```bash
ssh root@170.64.201.92 'cd /opt/betman/BETMAN_Voice && docker compose logs -f --tail=200 api worker'
```

Logs are structured JSON from the app and worker.

## Backup

```bash
ssh root@170.64.201.92 'cd /opt/betman/BETMAN_Voice && scripts/backup.sh'
```

This captures Postgres and local audio. If DigitalOcean Spaces is enabled, the
database backup is the source of truth for asset keys and Spaces handles object
durability.

## Restore

```bash
ssh root@170.64.201.92 'cd /opt/betman/BETMAN_Voice && scripts/restore.sh backups/betman_voice_YYYY.sql'
```

Restart the API and worker after restore:

```bash
docker compose restart api worker
```

## Upgrade

```bash
ssh root@170.64.201.92 'cd /opt/betman/BETMAN_Voice && scripts/upgrade.sh'
```

The upgrade script backs up first, pulls the latest code, rebuilds containers,
runs migrations, and checks `/health`.

## Load Test

```bash
locust -f scripts/load_test.py --host https://170.64.201.92:8088
```

## Failover Test

```bash
ssh root@170.64.201.92 'cd /opt/betman/BETMAN_Voice && scripts/failover_test.sh'
```

Expected behavior: API health remains available when worker is restarted, queued
jobs survive worker restarts because Postgres is the queue.

## BETMAN_Content Config

Set these through the BETMAN_Content config UI or environment:

```env
DJ_TTS_PROVIDER=voicebox
DJ_VOICEBOX_BASE_URL=https://170.64.201.92:8088
DJ_VOICEBOX_VOICE_ID=betman-female-presenter
```

## Import ElevenLabs Voices

```bash
ssh root@170.64.201.92 'cd /opt/betman/BETMAN_Voice && docker compose exec -T api python scripts/import_elevenlabs.py --api-key "$ELEVENLABS_API_KEY"'
```

Imported voices are intentionally marked `training_required` until the local
Voicebox/Qwen checkpoints are trained. See `docs/TRAINING.md`.

The worker can poll ElevenLabs automatically when `ELEVENLABS_API_KEY` is set.
Tune the interval with `BETMAN_VOICE_ELEVENLABS_POLL_SECONDS`; set it to `0` to
disable polling.

## Queue Voice Training

Training is tracked as a first-class job. Queue it through the API:

```bash
curl -X POST "$BETMAN_VOICE_URL/admin/voices/betman-female-presenter/training" \
  -H "xi-api-key: $BETMAN_VOICE_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"source":"elevenlabs"}'
```

Or run from the host:

```bash
ssh root@170.64.201.92 'cd /opt/betman/BETMAN_Voice && docker compose exec -T api python scripts/train_voice.py betman-female-presenter --run-now'
```

If samples are missing, the job moves to `waiting_for_samples`. If samples exist
but no trainer command is configured, it moves to `waiting_for_trainer`.

For ElevenLabs-compatible clients:

```env
ELEVENLABS_BASE_URL=https://170.64.201.92:8088
ELEVENLABS_API_KEY=<BETMAN_VOICE_DEFAULT_API_KEY>
```
