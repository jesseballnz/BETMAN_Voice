# BETMAN_Voice Operations Runbook

## Deploy

```bash
cp .env.example .env
vim .env
scripts/deploy.sh
```

BETMAN-TEST runs from `root@170.64.201.92:/opt/betman-test/BETMAN_Voice`.

## Health

```bash
curl https://170.64.201.92:8088/health
curl https://170.64.201.92:8088/metrics
ssh root@170.64.201.92 'systemctl status betman-test-voice betman-test-voice-worker'
```

## Logs

```bash
ssh root@170.64.201.92 'journalctl -fu betman-test-voice -u betman-test-voice-worker'
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
DJ_VOICEBOX_BASE_URL=http://127.0.0.1:18088
DJ_VOICEBOX_API_KEY=<BETMAN_VOICE_DEFAULT_API_KEY>
DJ_VOICEBOX_VOICE_ID=betman-female-presenter
```

## Qwen/MLX M4 Worker

BETMAN-TEST uses `model_backend=qwen-remote`. Content still talks only to the
BETMAN Voice API; the Voice worker calls Qwen/MLX through a reverse SSH tunnel:

```text
BETMAN Content -> BETMAN Voice :18088 -> TEST loopback :18011 -> M4 Qwen/MLX
```

Required Voice environment:

```env
BETMAN_VOICE_QWEN_REMOTE_BASE_URL=http://127.0.0.1:18011
BETMAN_VOICE_QWEN_REMOTE_MODEL_SIZE=0.6B
BETMAN_VOICE_QWEN_REMOTE_SEED=42
BETMAN_VOICE_QWEN_REMOTE_LANGUAGE=en
```

The tunnel must bind only to `127.0.0.1` on BETMAN-TEST. Check it with:

```bash
ssh root@170.64.201.92 'curl -fsS http://127.0.0.1:18011/health'
```

## Import ElevenLabs Voices

```bash
ssh root@170.64.201.92 'cd /opt/betman/BETMAN_Voice && docker compose exec -T api python scripts/import_elevenlabs.py --api-key "$ELEVENLABS_API_KEY"'
```

The four BETMAN identities and aliases are mapped to their trained Qwen/MLX
profiles and marked `ready`. See `docs/TRAINING.md` for adding future voices.

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
