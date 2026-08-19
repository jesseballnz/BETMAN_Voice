import io
import wave

import httpx
import pytest

from betman_voice.core.config import get_settings
from betman_voice.inference.backends import QwenRemoteBackend, SynthesisRequest, select_backend


@pytest.fixture(autouse=True)
def clear_settings_cache():
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def _wav_bytes() -> bytes:
    output = io.BytesIO()
    with wave.open(output, "wb") as audio:
        audio.setnchannels(1)
        audio.setsampwidth(2)
        audio.setframerate(24_000)
        audio.writeframes(b"\x00\x00" * 2_400)
    return output.getvalue()


def test_qwen_remote_synthesizes_with_profile_ref(monkeypatch):
    monkeypatch.setenv("BETMAN_VOICE_QWEN_REMOTE_BASE_URL", "http://qwen-worker:18011")
    get_settings.cache_clear()
    wav = _wav_bytes()
    requests = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.url.path == "/generate":
            return httpx.Response(200, json={"id": "generation-1"})
        return httpx.Response(200, content=wav, headers={"content-type": "audio/wav"})

    class MockClient(httpx.Client):
        def __init__(self, **kwargs):
            super().__init__(transport=httpx.MockTransport(handler), **kwargs)

    monkeypatch.setattr(httpx, "Client", MockClient)
    result = QwenRemoteBackend().synthesize(
        SynthesisRequest(
            text="BETMAN Voice test",
            voice_id="paul-social-outgoing-kind",
            settings={"model_ref": "qwen:93bd7993-4d63-4937-b3c1-2e76602b062f"},
        )
    )

    assert result.backend == "qwen-remote"
    assert result.audio == wav
    assert result.duration_ms == 100
    assert requests[0].url.path == "/generate"
    assert requests[1].url.path == "/audio/generation-1"
    assert b'"seed":42' in requests[0].content
    assert b'"model_size":"0.6B"' in requests[0].content


def test_qwen_remote_requires_qwen_model_ref(monkeypatch):
    monkeypatch.setenv("BETMAN_VOICE_QWEN_REMOTE_BASE_URL", "http://qwen-worker:18011")
    get_settings.cache_clear()
    backend = select_backend("qwen-remote")
    try:
        backend.synthesize(SynthesisRequest(text="test", voice_id="voice", model_id="qwen3-tts"))
    except RuntimeError as exc:
        assert "qwen_remote_model_ref_invalid" in str(exc)
    else:
        raise AssertionError("missing qwen profile ref should fail")
