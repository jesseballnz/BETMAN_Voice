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
) -> GenerationJob:
    job = GenerationJob(
        tenant_id=str(tenant_id),
        voice_id=voice_id,
        text=text,
        model_id=model_id,
        request_meta=request_meta or {},
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


def run_generation_job(db: Session, job: GenerationJob) -> GenerationJob:
    settings = get_settings()
    job.status = "running"
    job.started_at = datetime.now(timezone.utc)
    job.attempts += 1
    db.commit()

    try:
        voice = (
            db.query(Voice)
            .filter(Voice.tenant_id == job.tenant_id, Voice.voice_id == job.voice_id, Voice.active.is_(True))
            .first()
        )
        backend_name = voice.model_backend if voice and voice.model_backend else settings.model_backend
        backend = select_backend(backend_name)
        result = backend.synthesize(
            SynthesisRequest(
                text=job.text,
                voice_id=job.voice_id,
                model_id=job.model_id or settings.model_name,
                settings=voice.settings if voice else {},
            )
        )
        key = f"{job.tenant_id}/{job.id}.{settings.audio_format}"
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
