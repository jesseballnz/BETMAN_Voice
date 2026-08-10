# BETMAN Voice Training

## Imported ElevenLabs Voices

The BETMAN presenter voices are imported into the voice registry on bootstrap and
can be refreshed from ElevenLabs:

```bash
docker compose exec api python scripts/import_elevenlabs.py --api-key "$ELEVENLABS_API_KEY"
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
3. Place clean WAV/MP3 samples under `models/training/betman/<voice-id>/samples/`.
4. Train a Qwen/Voicebox checkpoint for each voice.
5. Update the voice in `/admin` or via `POST /admin/voices`:

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

## Model Runtime Package

The default Docker image installs the core service only so CPU hosts deploy
quickly and keep the API/job fallback alive. On a model host, install model
dependencies inside a derived image or virtual environment:

```bash
pip install ".[models]"
```
