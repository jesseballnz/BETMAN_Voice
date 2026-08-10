from __future__ import annotations

import io
import math
import wave
from dataclasses import dataclass

from betman_voice.core.config import get_settings
from betman_voice.core.runtime import RuntimeInfo, detect_runtime


@dataclass(frozen=True)
class SynthesisRequest:
    text: str
    voice_id: str
    model_id: str = ""
    settings: dict | None = None


@dataclass(frozen=True)
class SynthesisResult:
    audio: bytes
    mime_type: str
    backend: str
    duration_ms: int


class InferenceBackend:
    name = "base"

    def available(self) -> bool:
        return True

    def synthesize(self, request: SynthesisRequest) -> SynthesisResult:
        raise NotImplementedError


class QwenTtsBackend(InferenceBackend):
    name = "qwen3-tts"

    def __init__(self, runtime: RuntimeInfo | None = None) -> None:
        self.runtime = runtime or detect_runtime()

    def available(self) -> bool:
        try:
            import qwen_tts  # noqa: F401

            return True
        except Exception:
            return False

    def synthesize(self, request: SynthesisRequest) -> SynthesisResult:
        try:
            import qwen_tts  # type: ignore

            if hasattr(qwen_tts, "synthesize"):
                audio = qwen_tts.synthesize(
                    text=request.text,
                    voice=request.voice_id,
                    device=self.runtime.selected_device,
                    model=request.model_id or get_settings().model_name,
                )
                if isinstance(audio, bytes):
                    return SynthesisResult(audio, "audio/wav", self.name, _estimate_duration_ms(audio))
        except Exception as exc:
            if not get_settings().allow_synthetic_fallback:
                raise RuntimeError(f"qwen3_tts_failed: {exc}") from exc
        return SyntheticCpuBackend().synthesize(request)


class SyntheticCpuBackend(InferenceBackend):
    name = "synthetic-cpu-fallback"

    def synthesize(self, request: SynthesisRequest) -> SynthesisResult:
        sample_rate = 24_000
        duration_seconds = min(20.0, max(0.8, len(request.text) / 15.0))
        total_samples = int(sample_rate * duration_seconds)
        frequency = 180 + (sum(request.voice_id.encode("utf-8")) % 120)
        amplitude = 6000

        buffer = io.BytesIO()
        with wave.open(buffer, "wb") as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(sample_rate)
            for i in range(total_samples):
                envelope = min(1.0, i / (sample_rate * 0.08), (total_samples - i) / (sample_rate * 0.12))
                sample = int(amplitude * envelope * math.sin(2 * math.pi * frequency * i / sample_rate))
                wav.writeframesraw(sample.to_bytes(2, "little", signed=True))
        return SynthesisResult(buffer.getvalue(), "audio/wav", self.name, int(duration_seconds * 1000))


def select_backend(preference: str = "auto") -> InferenceBackend:
    runtime = detect_runtime()
    pref = (preference or "auto").lower()
    qwen = QwenTtsBackend(runtime)
    if pref in {"qwen", "qwen3", "qwen3-tts", "auto", "cuda", "cpu"} and qwen.available():
        return qwen
    return SyntheticCpuBackend()


def _estimate_duration_ms(audio: bytes) -> int:
    try:
        with wave.open(io.BytesIO(audio), "rb") as wav:
            return int(wav.getnframes() / float(wav.getframerate()) * 1000)
    except Exception:
        return 0
