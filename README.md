# BETMAN_Voice

Production voice generation service for BETMAN_Content.

BETMAN_Voice is a self-hosted, ElevenLabs-compatible TTS platform built around
the open-source Voicebox/Qwen3-TTS stack with a CPU-first runtime, automatic GPU
detection, Postgres persistence, DigitalOcean Spaces storage, tenant isolation,
job scheduling, metrics, and operational runbooks. The default container is a
small CPU-safe runtime; install the `models` extra on GPU/model hosts.

## Architecture

- `src/betman_voice/api` - REST API, ElevenLabs compatibility routes, admin UI.
- `src/betman_voice/core` - configuration, auth, logging, metrics, runtime detection.
- `src/betman_voice/db` - SQLAlchemy models and Postgres session management.
- `src/betman_voice/inference` - backend abstraction and CPU/GPU backend selection.
- `src/betman_voice/services` - generation jobs, training jobs, voices, storage, scheduler.
- `infra/terraform` - DigitalOcean droplet/firewall/project provisioning.
- `scripts` - deploy, backup, restore, upgrade, load and failover tests.
- `scripts/import_elevenlabs.py` - import BETMAN ElevenLabs voice registry for training.
- `scripts/poll_elevenlabs.py` - refresh ElevenLabs voice metadata on demand.
- `scripts/train_voice.py` - queue or run a voice training job.
- `tests` - API/auth/scheduler/backend selection coverage.

## Local Development

```bash
cp .env.example .env
docker compose up --build
curl http://127.0.0.1:8088/health
```

Default admin UI: `http://127.0.0.1:8088/admin`

## BETMAN_Content Integration

Provision through BETMAN_Content's config area:

```env
DJ_TTS_PROVIDER=voicebox
DJ_VOICEBOX_BASE_URL=http://168.144.163.174:8088
DJ_VOICEBOX_TIMEOUT_MS=600000
DJ_VOICEBOX_VOICE_ID=betman-female-presenter
```

The service also exposes ElevenLabs-compatible endpoints:

```bash
curl -X POST "$BETMAN_VOICE_URL/v1/text-to-speech/betman-female-presenter" \
  -H "xi-api-key: $BETMAN_VOICE_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"text":"BETMAN markets are live.","model_id":"qwen3-tts-cpu"}' \
  --output speech.wav
```

Training is exposed as a backend job API:

```bash
curl -X POST "$BETMAN_VOICE_URL/admin/voices/betman-female-presenter/training" \
  -H "xi-api-key: $BETMAN_VOICE_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"source":"elevenlabs"}'
```

## Deployment Target

Production host: `168.144.163.174` (8 vCPU, 16 GiB RAM)

Runtime: Qwen3-TTS 1.7B with one resident CPU worker and durable Postgres queue.

See [docs/OPERATIONS_RUNBOOK.md](docs/OPERATIONS_RUNBOOK.md).

Training notes: [docs/TRAINING.md](docs/TRAINING.md).
