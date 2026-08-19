from __future__ import annotations

import io
import math
import os
import subprocess
import time
import wave
from dataclasses import dataclass
from pathlib import Path
from tempfile import NamedTemporaryFile

import httpx

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


class PiperBackend(InferenceBackend):
    name = "voicebox-piper"

    def _resolve_paths(self, request: SynthesisRequest | None = None):
        settings = get_settings()
        request_settings = request.settings if request else {}
        model_path = request_settings.get("piper_model_path") if isinstance(request_settings, dict) else ""
        config_path = request_settings.get("piper_config_path") if isinstance(request_settings, dict) else ""
        model_ref = str(request.model_id or "").strip() if request else ""
        if isinstance(request_settings, dict):
            model_ref = str(request_settings.get("model_ref") or model_ref).strip()
        if model_ref.startswith("piper:"):
            model_name = model_ref.split(":", 1)[1].strip()
            if model_name:
                model_path = str(settings.model_dir / "piper" / f"{model_name}.onnx")
                config_path = str(settings.model_dir / "piper" / f"{model_name}.onnx.json")
        return (
            Path(model_path) if model_path else settings.piper_model_path,
            Path(config_path) if config_path else settings.piper_config_path,
        )

    def available(self) -> bool:
        model_path, config_path = self._resolve_paths()
        return model_path.exists() and config_path.exists()

    def synthesize(self, request: SynthesisRequest) -> SynthesisResult:
        settings = get_settings()
        model_path, config_path = self._resolve_paths(request)
        if not model_path.exists():
            raise RuntimeError(f"piper_model_missing: {model_path}")
        if not config_path.exists():
            raise RuntimeError(f"piper_config_missing: {config_path}")

        with NamedTemporaryFile(suffix=".wav") as output_file:
            command = [
                "python",
                "-m",
                "piper",
                "--model",
                str(model_path),
                "--config",
                str(config_path),
                "--output_file",
                output_file.name,
            ]
            subprocess.run(
                command,
                input=request.text,
                text=True,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=settings.request_timeout_seconds,
            )
            output_file.seek(0)
            audio = output_file.read()
        if not audio:
            raise RuntimeError("piper_empty_audio")
        return SynthesisResult(audio, "audio/wav", self.name, _estimate_duration_ms(audio))


class VoiceBoxBackend(InferenceBackend):
    name = "voicebox"

    def available(self) -> bool:
        return bool(_voicebox_base_url())

    def synthesize(self, request: SynthesisRequest) -> SynthesisResult:
        base_url = _voicebox_base_url()
        if not base_url:
            raise RuntimeError("voicebox_base_url_missing")

        voice_id = str((request.settings or {}).get("voicebox_voice_id") or request.voice_id).strip()
        if not voice_id:
            raise RuntimeError("voicebox_voice_id_missing")

        timeout = get_settings().request_timeout_seconds
        with httpx.Client(timeout=timeout) as client:
            response = client.post(
                f"{base_url}/tts",
                json={"voice_id": voice_id, "text": request.text},
            )
            response.raise_for_status()
            payload = response.json()
            job_id = str(payload.get("job_id") or payload.get("id") or "").strip()
            if not job_id:
                raise RuntimeError("voicebox_job_id_missing")

            deadline = time.monotonic() + timeout
            last_payload = payload
            while time.monotonic() < deadline:
                job_response = client.get(f"{base_url}/jobs/{job_id}")
                job_response.raise_for_status()
                last_payload = job_response.json()
                status = str(last_payload.get("status") or "").lower()
                if status == "completed":
                    audio_response = client.get(f"{base_url}/audio/{job_id}")
                    audio_response.raise_for_status()
                    audio = audio_response.content
                    mime_type = audio_response.headers.get("content-type") or "audio/wav"
                    return SynthesisResult(audio, mime_type.split(";")[0], self.name, _estimate_duration_ms(audio))
                if status in {"failed", "error"}:
                    raise RuntimeError(str(last_payload.get("error") or "voicebox_generation_failed"))
                time.sleep(0.5)

        raise RuntimeError(f"voicebox_generation_timeout: {job_id} {last_payload}")


def select_backend(preference: str = "auto") -> InferenceBackend:
    settings = get_settings()
    runtime = detect_runtime()
    pref = (preference or "auto").lower()
    if pref in {"voicebox", "piper"}:
        piper = PiperBackend()
        if piper.available():
            return piper
        raise RuntimeError("voicebox_piper_unavailable")
    if pref in {"external-voicebox", "voicebox-http"}:
        return VoiceBoxBackend()
    if pref in {"elevenlabs", "eleven-labs"}:
        raise RuntimeError("elevenlabs_backend_not_available_in_betman_voice")
    qwen = QwenTtsBackend(runtime)
    if pref in {"qwen", "qwen3", "qwen3-tts", "auto", "cuda", "cpu"} and qwen.available():
        return qwen
    if not settings.allow_synthetic_fallback:
        raise RuntimeError(f"tts_backend_unavailable: {pref}")
    return SyntheticCpuBackend()


def _estimate_duration_ms(audio: bytes) -> int:
    try:
        with wave.open(io.BytesIO(audio), "rb") as wav:
            return int(wav.getnframes() / float(wav.getframerate()) * 1000)
    except Exception:
        return 0


def _voicebox_base_url() -> str:
    return (
        os.getenv("VOICEBOX_BASE_URL", "").strip()
        or os.getenv("BETMAN_VOICE_VOICEBOX_BASE_URL", "").strip()
    ).rstrip("/")
