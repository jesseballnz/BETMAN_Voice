import os
import tempfile

os.environ["BETMAN_VOICE_DATABASE_URL"] = "sqlite:///:memory:"
os.environ["BETMAN_VOICE_SECRET_KEY"] = "test-secret-key-long"
os.environ["BETMAN_VOICE_ADMIN_EMAIL"] = "betman"
os.environ["BETMAN_VOICE_ADMIN_PASSWORD"] = "betman1234"
os.environ["BETMAN_VOICE_DEFAULT_API_KEY"] = "test-api-key"
os.environ["BETMAN_VOICE_LOCAL_STORAGE_DIR"] = tempfile.mkdtemp()

from betman_voice.core.config import get_settings

get_settings.cache_clear()

from betman_voice.api.app import create_app
from fastapi.testclient import TestClient

app = create_app()


def test_health():
    with TestClient(app) as client:
        response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["ok"] is True


def test_api_key_tts_generation():
    with TestClient(app) as client:
        response = client.post(
            "/tts",
            headers={"xi-api-key": "test-api-key"},
            json={"voiceId": "betman-female-presenter", "text": "Markets are live."},
        )
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] in {"completed", "failed"}
    assert payload.get("backend") != "elevenlabs"
    if payload["status"] == "completed":
        assert payload["ok"] is True
        assert payload["audio_url"]
    else:
        assert any(
            marker in payload.get("error", "")
            for marker in ("piper", "qwen_remote_unavailable", "tts_backend_unavailable")
        )


def test_auth_login_and_voices():
    with TestClient(app) as client:
        login = client.post("/auth/login", json={"email": "betman", "password": "betman1234"})
        assert login.status_code == 200
        token = login.json()["token"]
        voices = client.get("/voices", headers={"Authorization": f"Bearer {token}"})
    assert voices.status_code == 200
    assert len(voices.json()["voices"]) >= 1
    assert "settings" in voices.json()["voices"][0]


def test_admin_requires_authenticated_session():
    with TestClient(app) as client:
        response = client.get("/admin")
    assert response.status_code == 200
    assert "Admin access required" in response.text
    assert "Voice Configuration" not in response.text
    assert "Queue Training" not in response.text


def test_admin_console_loads_after_login_cookie():
    with TestClient(app) as client:
        login = client.post("/auth/login", json={"email": "betman", "password": "betman1234"})
        assert login.status_code == 200
        response = client.get("/admin")
    assert response.status_code == 200
    assert "Voice Configuration" in response.text
    assert "Queue Training" in response.text
    assert "<h2>Auth</h2>" not in response.text
    assert "API key override" not in response.text
    assert "Import / Poll" not in response.text
    assert "ElevenLabs" not in response.text


def test_admin_console_not_available_as_static_asset():
    with TestClient(app) as client:
        response = client.get("/static/admin.html")
    assert response.status_code == 404


def test_voice_settings_fill_blank_request_profile_from_registered_voice():
    with TestClient(app) as client:
        response = client.post(
            "/tts",
            headers={"xi-api-key": "test-api-key"},
            json={
                "voiceId": "betman-female-presenter",
                "text": "Markets are live.",
                "voice_settings": {
                    "presenter": {
                        "name": "BETMAN FEMALE",
                        "role": "market-mover",
                        "profile": {
                            "role": "market-mover",
                            "personality": "",
                            "tone": "",
                            "delivery": "",
                            "pace": "",
                            "useCase": "",
                        },
                    },
                    "profile": {
                        "role": "market-mover",
                        "personality": "",
                        "tone": "",
                        "delivery": "",
                        "pace": "",
                        "useCase": "",
                    },
                },
            },
        )
    assert response.status_code == 200

    from betman_voice.db.models import GenerationJob, Voice
    from betman_voice.db.session import SessionLocal
    from betman_voice.services.jobs import build_effective_voice_settings

    with SessionLocal() as db:
        job = db.query(GenerationJob).order_by(GenerationJob.created_at.desc()).first()
        voice = (
            db.query(Voice)
            .filter(Voice.tenant_id == job.tenant_id, Voice.voice_id == job.voice_id)
            .first()
        )
        settings = build_effective_voice_settings(voice, job.request_meta["voice_settings"])

    assert settings["profile"]["personality"] == "authoritative, composed, sharp racing presenter"
    assert settings["profile"]["tone"] == "premium broadcast, confident, concise"
    assert settings["request_presenter"]["profile"]["personality"] == "authoritative, composed, sharp racing presenter"
