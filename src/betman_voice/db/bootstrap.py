from sqlalchemy.orm import Session

from betman_voice.core.auth import hash_secret, password_hash
from betman_voice.core.config import get_settings
from betman_voice.db.models import ApiKey, Tenant, User, Voice


def bootstrap_defaults(db: Session) -> None:
    settings = get_settings()
    tenant = db.query(Tenant).filter(Tenant.slug == settings.default_tenant).first()
    if not tenant:
        tenant = Tenant(slug=settings.default_tenant, name="BETMAN")
        db.add(tenant)
        db.flush()

    user = db.query(User).filter(User.email == settings.admin_email).first()
    if not user:
        db.add(
            User(
                tenant_id=tenant.id,
                email=settings.admin_email,
                password_hash=password_hash(settings.admin_password),
                role="admin",
            )
        )

    if settings.default_api_key:
        existing_key = db.query(ApiKey).filter(ApiKey.key_hash == hash_secret(settings.default_api_key)).first()
        if not existing_key:
            db.add(
                ApiKey(
                    tenant_id=tenant.id,
                    name="BETMAN_Content",
                    key_hash=hash_secret(settings.default_api_key),
                    role="service",
                )
            )

    for voice_id, name in [
        ("2Ei5B6ir7ZzmLurX6KU4", "BETMAN Female Presenter"),
        ("9K2UBMDog21eSfMdLhEX", "Betman Comms Girl"),
        ("pDZ0CqONaFi2LrK1f413", "Torey Slatter"),
        ("hp7ETPcMxGdsmsPtJd8I", "Paul - Social, Out-going and Kind"),
        ("betman-female-presenter", "BETMAN Female Presenter"),
        ("betman-comms-girl", "Betman Comms Girl"),
        ("torey-slatter", "Torey Slatter"),
        ("paul-social-outgoing-kind", "Paul - Social, Out-going and Kind"),
    ]:
        voice = (
            db.query(Voice)
            .filter(Voice.tenant_id == tenant.id, Voice.voice_id == voice_id)
            .first()
        )
        if not voice:
            db.add(
                Voice(
                    tenant_id=tenant.id,
                    voice_id=voice_id,
                    name=name,
                    model_backend="auto",
                    settings={"source": "bootstrap", "training_status": "training_required"},
                )
            )

    db.commit()
