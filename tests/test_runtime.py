from betman_voice.core.runtime import detect_runtime
from betman_voice.inference.backends import SyntheticCpuBackend, select_backend
import pytest


def test_runtime_detection_returns_device():
    runtime = detect_runtime()
    assert runtime.selected_device in {"cpu", "cuda", "mps"}


def test_safe_cpu_fallback_generates_wav():
    result = SyntheticCpuBackend().synthesize(
        request=type("Req", (), {"text": "Hello", "voice_id": "betman", "model_id": "", "settings": {}})()
    )
    assert result.mime_type == "audio/wav"
    assert result.audio[:4] == b"RIFF"


def test_backend_selection_always_returns_backend():
    with pytest.raises(RuntimeError, match="tts_backend_unavailable"):
        select_backend("auto")
