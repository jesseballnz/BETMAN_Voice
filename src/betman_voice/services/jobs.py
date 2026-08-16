from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from betman_voice.core.config import get_settings
from betman_voice.db.models import GenerationJob, Voice
from betman_voice.inference.backends import SynthesisRequest, select_backend
from betman_voice.services.storage import storage
from betman_voice.services.text_normalizer import normalize_racing_text

PROFILE_KEYS = ("role", "personality", "tone", "delivery", "pace", "use_case", "useCase")


def _string_map(value: dict | None) -> dict:
    if not isinstance(value, dict):
        return {}
    return {str(key): str(raw).strip() for key, raw in value.items() if str(raw or "").strip()}


def _merge_profile(default_profile: dict | None, request_profile: dict | None) -> dict:
    merged = _string_map(default_profile)
    requested = _string_map(request_profile)
    for key in PROFILE_KEYS:
        if requested.get(key):
            merged[key] = requested[key]
    if merged.get("useCase") and not merged.get("use_case"):
        merged["use_case"] = merged["useCase"]
    if merged.get("use_case") and not merged.get("useCase"):
        merged["useCase"] = merged["use_case"]
    return merged


def build_effective_voice_settings(voice: Voice | None, request_voice_settings: dict | None) -> dict:
    voice_settings = dict(voice.settings if voice else {})
    if voice and voice.model_ref:
        voice_settings["model_ref"] = voice.model_ref

    request_settings = request_voice_settings if isinstance(request_voice_settings, dict) else {}
    request_presenter = request_settings.get("presenter") or {}
    if not isinstance(request_presenter, dict):
        request_presenter = {}

    voice_profile = voice_settings.get("profile") or {}
    request_profile = request_settings.get("profile") or request_presenter.get("profile") or {}
    effective_profile = _merge_profile(voice_profile, request_profile)
    if effective_profile:
        voice_settings["profile"] = effective_profile

    if request_profile:
        voice_settings["request_profile"] = _string_map(request_profile)
    if request_presenter:
        presenter = dict(request_presenter)
        presenter["profile"] = _merge_profile(effective_profile, presenter.get("profile") or {})
        voice_settings["request_presenter"] = presenter
    if isinstance(request_settings.get("voice_settings"), dict):
        voice_settings["voice_settings"] = request_settings["voice_settings"]
    return voice_settings


def enqueue_generation(
    db: Session,
    tenant_id: str,
    voice_id: str,
    text: str,
    model_id: str = "",
    request_meta: dict | None = None,
    initial_status: str = "queued",
) -> GenerationJob:
    job = GenerationJob(
        tenant_id=str(tenant_id),
        voice_id=voice_id,
        text=text,
        model_id=model_id,
        status=initial_status,
        request_meta=request_meta or {},
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


def run_generation_job(db: Session, job: GenerationJob) -> GenerationJob:
    settings = get_settings()
    if job.status != "running":
        claimed = (
            db.query(GenerationJob)
            .filter(GenerationJob.id == job.id, GenerationJob.status == "queued")
            .update(
                {
                    GenerationJob.status: "running",
                    GenerationJob.started_at: datetime.now(timezone.utc),
                    GenerationJob.attempts: GenerationJob.attempts + 1,
                },
                synchronize_session=False,
            )
        )
        db.commit()
        if claimed != 1:
            db.refresh(job)
            return job
        db.refresh(job)
    else:
        job.attempts += 1

    job.started_at = datetime.now(timezone.utc)
    db.commit()

    try:
        voice = (
            db.query(Voice)
            .filter(Voice.tenant_id == job.tenant_id, Voice.voice_id == job.voice_id, Voice.active.is_(True))
            .first()
        )
        backend_name = voice.model_backend if voice and voice.model_backend else settings.model_backend
        backend = select_backend(backend_name)
        request_voice_settings = {}
        if isinstance(job.request_meta, dict):
            request_voice_settings = job.request_meta.get("voice_settings") or {}
        voice_settings = build_effective_voice_settings(voice, request_voice_settings)

        normalized_text = normalize_racing_text(job.text)
        result = backend.synthesize(
            SynthesisRequest(
                text=normalized_text or job.text,
                voice_id=job.voice_id,
                model_id=job.model_id or settings.model_name,
                settings=voice_settings,
            )
        )
        key = f"{job.tenant_id}/{job.id}.{extension_for_mime_type(result.mime_type, settings.audio_format)}"
        url = storage.put_audio(key, result.audio, result.mime_type)
        job.status = "completed"
        job.backend = result.backend
        job.storage_key = key
        job.audio_url = url
        job.mime_type = result.mime_type
        job.duration_ms = result.duration_ms
        job.completed_at = datetime.now(timezone.utc)
        db.commit()
    except Exception as exc:
        job.status = "failed"
        job.error = str(exc)
        job.completed_at = datetime.now(timezone.utc)
        db.commit()
    db.refresh(job)
    return job


def extension_for_mime_type(mime_type: str, fallback: str = "wav") -> str:
    value = str(mime_type or "").lower().split(";")[0].strip()
    if value in {"audio/mpeg", "audio/mp3"}:
        return "mp3"
    if value in {"audio/wav", "audio/x-wav", "audio/wave"}:
        return "wav"
    if value in {"audio/mp4", "audio/m4a", "audio/aac"}:
        return "m4a"
    fallback = str(fallback or "wav").lower().lstrip(".")
    return fallback or "wav"
