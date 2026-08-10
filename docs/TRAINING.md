# BETMAN Voice Training

## Imported ElevenLabs Voices

The BETMAN presenter voices are imported into the voice registry on bootstrap and
can be refreshed from ElevenLabs:

```bash
docker compose exec api python scripts/poll_elevenlabs.py --api-key "$ELEVENLABS_API_KEY"
```

Imported voice IDs:

- `hp7ETPcMxGdsmsPtJd8I` - Paul - Social, Out-going and Kind
- `9K2UBMDog21eSfMdLhEX` - Betman Comms Girl
- `2Ei5B6ir7ZzmLurX6KU4` - BETMAN Female Presenter
- `pDZ0CqONaFi2LrK1f413` - Torey Slatter

Each voice is marked `training_required` until a local Voicebox/Qwen checkpoint
is trained and attached.

## Training Flow

1. Import ElevenLabs registry metadata.
2. Export approved BETMAN_Content TTS training pairs from the config UI.
3. Place clean WAV/MP3 samples under `/models/training/<tenant-id>/<voice-id>/samples/`.
4. Queue training:

```bash
docker compose exec api python scripts/train_voice.py betman-female-presenter
```

Or via API:

```bash
curl -X POST "$BETMAN_VOICE_URL/admin/voices/betman-female-presenter/training" \
  -H "xi-api-key: $BETMAN_VOICE_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"source":"elevenlabs"}'
```

5. The worker creates `training-manifest.json` and moves the job to:

- `waiting_for_samples` when no samples are present.
- `waiting_for_trainer` when samples exist but no trainer command is configured.
- `completed` when the configured trainer exits successfully.

6. Configure the real trainer command when the model host is ready:

```env
BETMAN_VOICE_TRAINING_COMMAND='voicebox-train --manifest {manifest} --output {output}'
```

Available template variables: `{manifest}`, `{dataset}`, `{samples}`, `{output}`,
`{voice_id}`, `{job_id}`.

7. When a trainer completes successfully, the worker updates `model_ref` and marks
the voice `training_status=ready`. You can also manually update a voice via
`POST /admin/voices`:

```json
{
  "voice_id": "2Ei5B6ir7ZzmLurX6KU4",
  "name": "BETMAN Female Presenter",
  "model_backend": "qwen3-tts",
  "model_ref": "/models/betman-female-presenter/checkpoint",
  "settings": {
    "training_status": "ready",
    "source": "elevenlabs"
  }
}
```

The alias `betman-female-presenter` should point to the same trained checkpoint
once ready.

## ElevenLabs Polling

The worker polls ElevenLabs when `ELEVENLABS_API_KEY` or
`BETMAN_VOICE_ELEVENLABS_API_KEY` is set. The interval defaults to one hour:

```env
BETMAN_VOICE_ELEVENLABS_POLL_SECONDS=3600
```

Set it to `0` to disable automatic polling.

## Model Runtime Package

The default Docker image installs the core service only so CPU hosts deploy
quickly and keep the API/job fallback alive. On a model host, install model
dependencies inside a derived image or virtual environment:

```bash
pip install ".[models]"
```
