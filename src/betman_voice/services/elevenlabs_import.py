from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

import httpx
from sqlalchemy.orm import Session

from betman_voice.core.config import get_settings
from betman_voice.db.models import Voice

BETMAN_ELEVENLABS_VOICES = [
    {
        "voice_id": "hp7ETPcMxGdsmsPtJd8I",
        "name": "Paul - Social, Out-going and Kind",
        "roles": ["boss"],
        "local_alias": "paul-social-outgoing-kind",
        "model_ref": "qwen:93bd7993-4d63-4937-b3c1-2e76602b062f",
    },
    {
        "voice_id": "9K2UBMDog21eSfMdLhEX",
        "name": "Betman Comms Girl",
        "roles": ["conversation", "comms", "control-room", "general-banter"],
        "local_alias": "betman-comms-girl",
        "model_ref": "qwen:67de3c0d-acbd-4236-a120-910c4e569c75",
    },
    {
        "voice_id": "2Ei5B6ir7ZzmLurX6KU4",
        "name": "BETMAN Female Presenter",
        "roles": ["presenter", "market-mover", "interesting-runner"],
        "local_alias": "betman-female-presenter",
        "model_ref": "qwen:9f0d5d97-93a7-46a8-a0af-9260e60ab3e2",
    },
    {
        "voice_id": "pDZ0CqONaFi2LrK1f413",
        "name": "Torey Slatter",
        "roles": ["junior-analyst", "upcoming-edge", "signal-proof"],
        "local_alias": "torey-slatter",
        "model_ref": "qwen:fd581ac5-5f66-49a5-a596-e5986d65bcbc",
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
        model_ref = spec["model_ref"]
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
        voice.model_backend = "qwen-local"
        voice.model_ref = model_ref
        samples = remote.get("samples") or []
        voice.settings = {
            **(voice.settings or {}),
            "source": "elevenlabs",
            "elevenlabs_voice_id": spec["voice_id"],
            "local_alias": spec.get("local_alias", ""),
            "model_ref": model_ref,
            "roles": spec.get("roles", []),
            "remote_sample_count": len(samples),
            "training_status": "ready",
            "training_note": "ElevenLabs identity mapped 1:1 to a trained BETMAN Qwen profile.",
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
            alias_voice.model_backend = "qwen-local"
            alias_voice.model_ref = model_ref
            alias_voice.settings = {
                **(alias_voice.settings or {}),
                "source": "elevenlabs_alias",
                "elevenlabs_voice_id": spec["voice_id"],
                "model_ref": model_ref,
                "roles": spec.get("roles", []),
                "training_status": "ready",
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
