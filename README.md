# BETMAN_Voice

Standalone VoiceBox deployment package for BETMAN.

## Overview

VoiceBox is the local TTS/STT platform used by BETMAN_Content.

It is designed to be installed and run independently of any specific host.

## Quick Start (batman-staging)

```bash
git clone git@github.com:jesseballnz/BETMAN_Voice.git
cd BETMAN_Voice
./install.sh
```

## Services

- `POST /tts` — Text to speech (Piper + future clones)
- `POST /stt` — Speech to text
- `POST /voices/clone` — Voice cloning
- Admin UI at `/`

## Environment

- Python 3.11+
- Piper (onnx models)
- Redis (optional, for queuing)
- SQLite (jobs)

## Next

- Custom BETMAN voice training
- Integration with BETMAN_Content (`DJ_TTS_PROVIDER=voicebox`)
- JWT + multi-tenant

See `docs/` for full manual.