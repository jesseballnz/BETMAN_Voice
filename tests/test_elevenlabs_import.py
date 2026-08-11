from betman_voice.db.bootstrap import bootstrap_defaults
from betman_voice.db.models import Tenant, Voice
from betman_voice.db.session import Base, SessionLocal, engine
from betman_voice.services.elevenlabs_import import BETMAN_ELEVENLABS_VOICES, import_betman_elevenlabs_voices


def test_import_registers_betman_elevenlabs_voices():
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        bootstrap_defaults(db)
        tenant = db.query(Tenant).filter(Tenant.slug == "betman").first()
        result = import_betman_elevenlabs_voices(db, tenant.id)
        assert result["ok"] is True
        for spec in BETMAN_ELEVENLABS_VOICES:
            voice = (
                db.query(Voice)
                .filter(Voice.tenant_id == tenant.id, Voice.voice_id == spec["voice_id"])
                .first()
            )
            assert voice is not None
            assert voice.model_backend == "voicebox"
            assert voice.model_ref == spec["model_ref"]
            assert voice.settings["elevenlabs_voice_id"] == spec["voice_id"]
            assert voice.settings["model_ref"] == spec["model_ref"]
            assert voice.settings["training_status"] == "training_required"

            alias = (
                db.query(Voice)
                .filter(Voice.tenant_id == tenant.id, Voice.voice_id == spec["local_alias"])
                .first()
            )
            assert alias is not None
            assert alias.model_backend == "voicebox"
            assert alias.model_ref == spec["model_ref"]
            assert alias.settings["source"] == "elevenlabs_alias"
            assert alias.settings["elevenlabs_voice_id"] == spec["voice_id"]
            assert alias.settings["model_ref"] == spec["model_ref"]
