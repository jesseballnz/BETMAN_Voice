# BETMAN_Voice Manual

## Deployment on batman-staging

1. Clone this repo to `/Volumes/HDD/voicebox/app`
2. Run `./install.sh`
3. Start with `./scripts/run.sh`

## Configuration

Edit `app/core/config.py` for storage paths.

## Integration with BETMAN_Content

Set in BETMAN_Content:
```
DJ_TTS_PROVIDER=voicebox
DJ_VOICEBOX_BASE_URL=http://192.168.1.111:8000
```

## Voice Training

See `scripts/import_elevenlabs.py` for cloning existing voices.