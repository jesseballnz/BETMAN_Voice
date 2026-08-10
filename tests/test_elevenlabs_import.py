from betman_voice.db.bootstrap import bootstrap_defaults
from betman_voice.db.models import Tenant, Voice
from betman_voice.db.session import Base, SessionLocal, engine
from betman_voice.services.elevenlabs_import import import_betman_elevenlabs_voices


def test_import_registers_betman_elevenlabs_voices():
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        bootstrap_defaults(db)
        tenant = db.query(Tenant).filter(Tenant.slug == "betman").first()
        result = import_betman_elevenlabs_voices(db, tenant.id)
        assert result["ok"] is True
        voice = (
            db.query(Voice)
            .filter(Voice.tenant_id == tenant.id, Voice.voice_id == "2Ei5B6ir7ZzmLurX6KU4")
            .first()
        )
        assert voice is not None
        assert voice.settings["training_status"] == "training_required"
        alias = (
            db.query(Voice)
            .filter(Voice.tenant_id == tenant.id, Voice.voice_id == "betman-female-presenter")
            .first()
        )
        assert alias.settings["elevenlabs_voice_id"] == "2Ei5B6ir7ZzmLurX6KU4"
