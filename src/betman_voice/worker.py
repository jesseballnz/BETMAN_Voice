from __future__ import annotations

import time

from sqlalchemy import select

from betman_voice.core.config import get_settings
from betman_voice.core.logging import configure_logging, get_logger
from betman_voice.db.models import GenerationJob
from betman_voice.db.session import SessionLocal
from betman_voice.services.jobs import run_generation_job

log = get_logger(__name__)


def run_worker() -> None:
    configure_logging()
    settings = get_settings()
    log.info("worker_started", poll_seconds=settings.job_poll_seconds)
    while True:
        with SessionLocal() as db:
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
            else:
                time.sleep(settings.job_poll_seconds)


if __name__ == "__main__":
    run_worker()
