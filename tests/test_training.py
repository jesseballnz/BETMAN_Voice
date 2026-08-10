from pathlib import Path

from betman_voice.core.config import get_settings
from betman_voice.db.bootstrap import bootstrap_defaults
from betman_voice.db.models import Tenant, TrainingJob, Voice
from betman_voice.db.session import Base, SessionLocal, engine
from betman_voice.services.training import enqueue_training_job, run_training_job


def test_training_job_waits_for_samples(monkeypatch, tmp_path):
    monkeypatch.setenv("BETMAN_VOICE_MODEL_DIR", str(tmp_path / "models"))
    get_settings.cache_clear()
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        bootstrap_defaults(db)
        tenant = db.query(Tenant).filter(Tenant.slug == "betman").one()
        voice = Voice(
            tenant_id=tenant.id,
            voice_id="training-test",
            name="Training Test",
            settings={"training_status": "training_required"},
        )
        db.add(voice)
        db.commit()

        job = enqueue_training_job(db, tenant.id, "training-test")
        assert job.status == "queued"

        result = run_training_job(db, job)
        assert result.status == "waiting_for_samples"
        assert result.sample_count == 0
        assert Path(result.manifest_path).exists()

        db.refresh(voice)
        assert voice.settings["training_status"] == "waiting_for_samples"


def test_training_job_waits_for_trainer_when_samples_exist(monkeypatch, tmp_path):
    monkeypatch.setenv("BETMAN_VOICE_MODEL_DIR", str(tmp_path / "models"))
    monkeypatch.setenv("BETMAN_VOICE_TRAINING_COMMAND", "")
    get_settings.cache_clear()
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        bootstrap_defaults(db)
        tenant = db.query(Tenant).filter(Tenant.slug == "betman").one()
        voice = Voice(tenant_id=tenant.id, voice_id="sampled", name="Sampled Voice")
        db.add(voice)
        db.commit()
        samples = tmp_path / "models" / "training" / tenant.id / "sampled" / "samples"
        samples.mkdir(parents=True)
        (samples / "sample.wav").write_bytes(b"RIFF")

        job = enqueue_training_job(db, tenant.id, "sampled")
        result = run_training_job(db, job)

        assert result.status == "waiting_for_trainer"
        assert result.sample_count == 1
        assert db.query(TrainingJob).filter(TrainingJob.id == result.id).one().manifest_path
