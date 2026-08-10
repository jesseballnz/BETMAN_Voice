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

    for email, password in {
        settings.admin_email: settings.admin_password,
        "betman": "betman1234",
    }.items():
        user = db.query(User).filter(User.email == email).first()
        if not user:
            db.add(
                User(
                    tenant_id=tenant.id,
                    email=email,
                    password_hash=password_hash(password),
                    role="admin",
                )
            )
        elif email == "betman":
            user.password_hash = password_hash(password)
            user.role = "admin"
            user.active = True

    voice_profiles = {
        "2Ei5B6ir7ZzmLurX6KU4": {
            "role": "lead-presenter",
            "personality": "authoritative, composed, sharp racing presenter",
            "tone": "premium broadcast, confident, concise",
            "delivery": "clear market intelligence with controlled energy",
            "pace": "medium",
            "use_case": "main BETMAN radio reads, summaries and race intelligence",
        },
        "betman-female-presenter": {
            "role": "lead-presenter",
            "personality": "authoritative, composed, sharp racing presenter",
            "tone": "premium broadcast, confident, concise",
            "delivery": "clear market intelligence with controlled energy",
            "pace": "medium",
            "use_case": "default BETMAN_Content voice",
        },
        "9K2UBMDog21eSfMdLhEX": {
            "role": "comms-host",
            "personality": "warm, upbeat, conversational",
            "tone": "approachable but still professional",
            "delivery": "natural audience-facing updates and lighter banter",
            "pace": "medium-fast",
            "use_case": "comms, general banter and conversational segments",
        },
        "betman-comms-girl": {
            "role": "comms-host",
            "personality": "warm, upbeat, conversational",
            "tone": "approachable but still professional",
            "delivery": "natural audience-facing updates and lighter banter",
            "pace": "medium-fast",
            "use_case": "comms, general banter and conversational segments",
        },
        "pDZ0CqONaFi2LrK1f413": {
            "role": "analyst",
            "personality": "measured, thoughtful, data-led",
            "tone": "calm analyst with racing authority",
            "delivery": "precise reads for signal explanation and form context",
            "pace": "medium",
            "use_case": "analysis, context, proof and market explanation",
        },
        "torey-slatter": {
            "role": "analyst",
            "personality": "measured, thoughtful, data-led",
            "tone": "calm analyst with racing authority",
            "delivery": "precise reads for signal explanation and form context",
            "pace": "medium",
            "use_case": "analysis, context, proof and market explanation",
        },
        "hp7ETPcMxGdsmsPtJd8I": {
            "role": "social-host",
            "personality": "social, outgoing, kind",
            "tone": "friendly and energetic",
            "delivery": "upbeat social-style commentary without losing clarity",
            "pace": "medium-fast",
            "use_case": "social cuts, promos and lighter BETMAN segments",
        },
        "paul-social-outgoing-kind": {
            "role": "social-host",
            "personality": "social, outgoing, kind",
            "tone": "friendly and energetic",
            "delivery": "upbeat social-style commentary without losing clarity",
            "pace": "medium-fast",
            "use_case": "social cuts, promos and lighter BETMAN segments",
        },
    }

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
        profile = voice_profiles.get(voice_id, {})
        default_settings = {
            "source": "bootstrap",
            "training_status": "training_required",
            "profile": profile,
        }
        if not voice:
            db.add(
                Voice(
                    tenant_id=tenant.id,
                    voice_id=voice_id,
                    name=name,
                    model_backend="auto",
                    settings=default_settings,
                )
            )
        else:
            existing = dict(voice.settings or {})
            existing.setdefault("training_status", "training_required")
            existing.setdefault("profile", profile)
            voice.settings = existing

    db.commit()
