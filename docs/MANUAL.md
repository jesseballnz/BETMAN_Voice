# BETMAN_Voice Manual

## Installation

1. Clone the repo
2. Run `./install.sh`
3. Start with `./scripts/run.sh`

## Configuration

Edit `app/core/config.py` for storage paths and ports.

## Integration with BETMAN_Content

Set in BETMAN_Content environment:
```
DJ_TTS_PROVIDER=voicebox
DJ_VOICEBOX_BASE_URL=http://your-voicebox-host:8000
```

## Voice Training

See `scripts/import_elevenlabs.py` for cloning existing voices.