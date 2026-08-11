from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

import httpx
from sqlalchemy.orm import Session

from betman_voice.core.config import get_settings
from betman_voice.db.models import Voice
from betman_voice.services.storage import storage

BETMAN_ELEVENLABS_VOICES = [
    {
        "voice_id": "hp7ETPcMxGdsmsPtJd8I",
        "name": "Paul - Social, Out-going and Kind",
        "roles": ["boss"],
        "local_alias": "paul-social-outgoing-kind",
        "model_ref": "piper:en_US-ryan-high",
    },
    {
        "voice_id": "9K2UBMDog21eSfMdLhEX",
        "name": "Betman Comms Girl",
        "roles": ["conversation", "comms", "control-room", "general-banter"],
        "local_alias": "betman-comms-girl",
        "model_ref": "piper:en_US-amy-medium",
    },
    {
        "voice_id": "2Ei5B6ir7ZzmLurX6KU4",
        "name": "BETMAN Female Presenter",
        "roles": ["presenter", "market-mover", "interesting-runner"],
        "local_alias": "betman-female-presenter",
        "model_ref": "piper:en_US-amy-medium",
    },
    {
        "voice_id": "pDZ0CqONaFi2LrK1f413",
        "name": "Torey Slatter",
        "roles": ["junior-analyst", "upcoming-edge", "signal-proof"],
        "local_alias": "torey-slatter",
        "model_ref": "piper:en_US-ryan-high",
    },
]


def import_betman_elevenlabs_voices(
    db: Session,
    tenant_id: str,
    api_key: str = "",
    voice_specs: Iterable[dict] | None = None,
) -> dict:
    specs = list(voice_specs or BETMAN_ELEVENLABS_VOICES)
    remote_by_id = fetch_elevenlabs_voice_metadata(api_key) if api_key else {}
    imported = []

    for spec in specs:
        remote = remote_by_id.get(spec["voice_id"], {})
        voice = (
            db.query(Voice)
            .filter(Voice.tenant_id == tenant_id, Voice.voice_id == spec["voice_id"])
            .first()
        )
        if not voice:
            voice = Voice(tenant_id=tenant_id, voice_id=spec["voice_id"], name=spec["name"])
            db.add(voice)
        voice.name = remote.get("name") or spec["name"]
        voice.description = "Imported from ElevenLabs for BETMAN_Voice local training."
        voice.model_backend = "voicebox"
        samples = remote.get("samples") or []
        voice.settings = {
            **(voice.settings or {}),
            "source": "elevenlabs",
            "elevenlabs_voice_id": spec["voice_id"],
            "local_alias": spec.get("local_alias", ""),
            "model_ref": spec.get("model_ref", "piper:en_US-amy-medium"),
            "roles": spec.get("roles", []),
            "remote_sample_count": len(samples),
            "training_status": "training_required",
            "training_note": "Imported ElevenLabs mapping metadata. Synthesis stays on local BETMAN VoiceBox/Piper until a trained local checkpoint replaces it.",
        }
        imported.append({"voice_id": voice.voice_id, "name": voice.name, "samples": len(samples)})

        alias = spec.get("local_alias")
        if alias:
            alias_voice = (
                db.query(Voice)
                .filter(Voice.tenant_id == tenant_id, Voice.voice_id == alias)
                .first()
            )
            if not alias_voice:
                alias_voice = Voice(tenant_id=tenant_id, voice_id=alias, name=spec["name"])
                db.add(alias_voice)
            alias_voice.name = spec["name"]
            alias_voice.description = f"BETMAN VoiceBox alias mapped from ElevenLabs presenter {spec['voice_id']}."
            alias_voice.model_backend = "voicebox"
            alias_voice.settings = {
                **(alias_voice.settings or {}),
                "source": "elevenlabs_alias",
                "elevenlabs_voice_id": spec["voice_id"],
                "model_ref": spec.get("model_ref", "piper:en_US-amy-medium"),
                "roles": spec.get("roles", []),
                "training_status": "training_required",
            }

    db.commit()
    return {"ok": True, "imported": imported}


def fetch_elevenlabs_voice_metadata(api_key: str) -> dict:
    headers = {"xi-api-key": api_key}
    with httpx.Client(timeout=30) as client:
        response = client.get("https://api.elevenlabs.io/v1/voices", headers=headers)
        response.raise_for_status()
        payload = response.json()
    return {item.get("voice_id"): item for item in payload.get("voices", []) if item.get("voice_id")}


def write_training_manifest(tenant_slug: str = "betman") -> Path:
    settings = get_settings()
    target = Path(settings.model_dir) / "training" / tenant_slug / "elevenlabs-import-manifest.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(BETMAN_ELEVENLABS_VOICES, indent=2))
    return target
