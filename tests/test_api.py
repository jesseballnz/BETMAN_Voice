import os
import tempfile

os.environ["BETMAN_VOICE_DATABASE_URL"] = "sqlite:///:memory:"
os.environ["BETMAN_VOICE_SECRET_KEY"] = "test-secret-key-long"
os.environ["BETMAN_VOICE_ADMIN_EMAIL"] = "betman"
os.environ["BETMAN_VOICE_ADMIN_PASSWORD"] = "betman1234"
os.environ["BETMAN_VOICE_DEFAULT_API_KEY"] = "test-api-key"
os.environ["BETMAN_VOICE_LOCAL_STORAGE_DIR"] = tempfile.mkdtemp()

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
    assert payload["ok"] is True
    assert payload["audio_url"]
    assert payload["backend"] in {"qwen3-tts", "synthetic-cpu-fallback"}


def test_auth_login_and_voices():
    with TestClient(app) as client:
        login = client.post("/auth/login", json={"email": "betman", "password": "betman1234"})
        assert login.status_code == 200
        token = login.json()["token"]
        voices = client.get("/voices", headers={"Authorization": f"Bearer {token}"})
    assert voices.status_code == 200
    assert len(voices.json()["voices"]) >= 1
    assert "settings" in voices.json()["voices"][0]
