from __future__ import annotations

import os
import time

from sqlalchemy import select

from betman_voice.core.config import get_settings
from betman_voice.core.logging import configure_logging, get_logger
from betman_voice.db.models import GenerationJob, Tenant, TrainingJob
from betman_voice.db.session import SessionLocal
from betman_voice.services.elevenlabs_import import import_betman_elevenlabs_voices
from betman_voice.services.jobs import run_generation_job
from betman_voice.services.training import run_training_job

log = get_logger(__name__)


def run_worker() -> None:
    configure_logging()
    settings = get_settings()
    last_elevenlabs_poll = 0.0
    log.info(
        "worker_started",
        poll_seconds=settings.job_poll_seconds,
        elevenlabs_poll_seconds=settings.elevenlabs_poll_seconds,
    )
    while True:
        with SessionLocal() as db:
            if maybe_poll_elevenlabs(db, settings, last_elevenlabs_poll):
                last_elevenlabs_poll = time.time()
            job = (
                db.execute(
                    select(GenerationJob)
                    .where(GenerationJob.status == "queued")
                    .order_by(GenerationJob.created_at.asc())
                    .limit(1)
                )
                .scalars()
                .first()
            )
            if job:
                log.info("job_started", job_id=str(job.id), tenant_id=str(job.tenant_id))
                result = run_generation_job(db, job)
                log.info("job_finished", job_id=str(result.id), status=result.status, backend=result.backend)
                continue
            training_job = (
                db.execute(
                    select(TrainingJob)
                    .where(TrainingJob.status == "queued")
                    .order_by(TrainingJob.created_at.asc())
                    .limit(1)
                )
                .scalars()
                .first()
            )
            if training_job:
                log.info(
                    "training_job_started",
                    job_id=str(training_job.id),
                    tenant_id=str(training_job.tenant_id),
                    voice_id=training_job.voice_id,
                )
                result = run_training_job(db, training_job)
                log.info("training_job_finished", job_id=str(result.id), status=result.status)
                continue
            time.sleep(settings.job_poll_seconds)


def maybe_poll_elevenlabs(db, settings, last_poll: float) -> bool:
    if settings.elevenlabs_poll_seconds <= 0:
        return False
    if last_poll and time.time() - last_poll < settings.elevenlabs_poll_seconds:
        return False
    api_key = os.getenv("ELEVENLABS_API_KEY", "").strip() or os.getenv(
        "BETMAN_VOICE_ELEVENLABS_API_KEY", ""
    ).strip()
    if not api_key:
        return False
    tenant = db.query(Tenant).filter(Tenant.slug == settings.default_tenant).first()
    if not tenant:
        return False
    try:
        result = import_betman_elevenlabs_voices(db, tenant.id, api_key=api_key)
        log.info("elevenlabs_poll_finished", imported=len(result.get("imported", [])))
    except Exception as exc:  # noqa: BLE001
        log.warning("elevenlabs_poll_failed", error=str(exc))
    return True


if __name__ == "__main__":
    run_worker()
