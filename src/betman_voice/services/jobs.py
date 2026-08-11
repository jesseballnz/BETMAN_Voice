from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from betman_voice.core.config import get_settings
from betman_voice.db.models import GenerationJob, Voice
from betman_voice.inference.backends import SynthesisRequest, select_backend
from betman_voice.services.storage import storage


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
        voice_settings = dict(voice.settings if voice else {})
        if voice and voice.model_ref:
            voice_settings["model_ref"] = voice.model_ref
        request_voice_settings = {}
        if isinstance(job.request_meta, dict):
            request_voice_settings = job.request_meta.get("voice_settings") or {}
        if isinstance(request_voice_settings, dict):
            request_profile = request_voice_settings.get("profile") or {}
            request_presenter = request_voice_settings.get("presenter") or {}
            if isinstance(request_profile, dict) and request_profile:
                voice_settings["request_profile"] = request_profile
            if isinstance(request_presenter, dict) and request_presenter:
                voice_settings["request_presenter"] = request_presenter
            if isinstance(request_voice_settings.get("voice_settings"), dict):
                voice_settings["voice_settings"] = request_voice_settings["voice_settings"]

        result = backend.synthesize(
            SynthesisRequest(
                text=job.text,
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
