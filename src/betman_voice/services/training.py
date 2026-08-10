from __future__ import annotations

import json
import shlex
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy.orm import Session

from betman_voice.core.config import get_settings
from betman_voice.core.logging import get_logger
from betman_voice.db.models import TrainingJob, Voice

log = get_logger(__name__)


def enqueue_training_job(
    db: Session,
    tenant_id: str,
    voice_id: str,
    *,
    source: str = "elevenlabs",
    request_meta: dict | None = None,
) -> TrainingJob:
    voice = (
        db.query(Voice)
        .filter(Voice.tenant_id == tenant_id, Voice.voice_id == voice_id, Voice.active.is_(True))
        .first()
    )
    if not voice:
        raise ValueError("voice_not_found")
    job = TrainingJob(
        tenant_id=tenant_id,
        voice_id=voice_id,
        source=source,
        request_meta=request_meta or {},
    )
    db.add(job)
    db.flush()
    settings = dict(voice.settings or {})
    settings["training_status"] = "queued"
    settings["training_job_id"] = job.id
    voice.settings = settings
    voice.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(job)
    return job


def run_training_job(db: Session, job: TrainingJob) -> TrainingJob:
    settings = get_settings()
    now = datetime.now(timezone.utc)
    job.status = "running"
    job.started_at = now
    db.commit()

    voice = (
        db.query(Voice)
        .filter(Voice.tenant_id == job.tenant_id, Voice.voice_id == job.voice_id)
        .first()
    )
    if not voice:
        job.status = "failed"
        job.error = "voice_not_found"
        job.completed_at = datetime.now(timezone.utc)
        db.commit()
        return job

    try:
        dataset_dir = Path(settings.model_dir) / "training" / str(job.tenant_id) / job.voice_id
        samples_dir = dataset_dir / "samples"
        output_dir = dataset_dir / "output"
        samples_dir.mkdir(parents=True, exist_ok=True)
        output_dir.mkdir(parents=True, exist_ok=True)
        sample_count = len([p for p in samples_dir.iterdir() if p.is_file()])
        manifest = {
            "job_id": job.id,
            "tenant_id": job.tenant_id,
            "voice_id": job.voice_id,
            "voice_name": voice.name,
            "source": job.source,
            "elevenlabs_voice_id": (voice.settings or {}).get("elevenlabs_voice_id", ""),
            "samples_dir": str(samples_dir),
            "output_dir": str(output_dir),
            "sample_count": sample_count,
            "requested_at": job.created_at.isoformat(),
        }
        manifest_path = dataset_dir / "training-manifest.json"
        manifest_path.write_text(json.dumps(manifest, indent=2))

        job.dataset_path = str(dataset_dir)
        job.manifest_path = str(manifest_path)
        job.sample_count = sample_count

        voice_settings = dict(voice.settings or {})
        voice_settings["training_status"] = "waiting_for_samples" if sample_count == 0 else "training"
        voice_settings["training_job_id"] = job.id
        voice_settings["training_manifest"] = str(manifest_path)
        voice.settings = voice_settings
        voice.updated_at = datetime.now(timezone.utc)
        db.commit()

        if sample_count == 0:
            job.status = "waiting_for_samples"
            job.error = "No sample files found. Add WAV/MP3 samples then enqueue training again."
            job.completed_at = datetime.now(timezone.utc)
            db.commit()
            return job

        if not settings.training_command.strip():
            job.status = "waiting_for_trainer"
            job.error = "BETMAN_VOICE_TRAINING_COMMAND is not configured."
            job.completed_at = datetime.now(timezone.utc)
            voice_settings["training_status"] = "waiting_for_trainer"
            voice.settings = voice_settings
            voice.updated_at = datetime.now(timezone.utc)
            db.commit()
            return job

        command = settings.training_command.format(
            manifest=shlex.quote(str(manifest_path)),
            dataset=shlex.quote(str(dataset_dir)),
            samples=shlex.quote(str(samples_dir)),
            output=shlex.quote(str(output_dir)),
            voice_id=shlex.quote(job.voice_id),
            job_id=shlex.quote(job.id),
        )
        result = subprocess.run(command, shell=True, check=False, text=True, capture_output=True)
        if result.returncode != 0:
            job.status = "failed"
            job.error = (result.stderr or result.stdout or "trainer_failed").strip()[-4000:]
        else:
            model_ref = str(output_dir)
            job.status = "completed"
            job.error = ""
            job.model_ref = model_ref
            voice.model_ref = model_ref
            voice.model_backend = "qwen-tts"
            voice_settings["training_status"] = "ready"
            voice_settings["training_completed_at"] = datetime.now(timezone.utc).isoformat()
            voice.settings = voice_settings
            voice.updated_at = datetime.now(timezone.utc)
        job.completed_at = datetime.now(timezone.utc)
        db.commit()
        log.info("training_job_finished", job_id=job.id, status=job.status, voice_id=job.voice_id)
    except Exception as exc:  # noqa: BLE001
        job.status = "failed"
        job.error = str(exc)
        job.completed_at = datetime.now(timezone.utc)
        db.commit()
        log.warning("training_job_failed", job_id=job.id, error=str(exc))
    return job
