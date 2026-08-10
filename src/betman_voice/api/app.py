from __future__ import annotations

from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse, Response
from fastapi.staticfiles import StaticFiles
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest
from sqlalchemy.orm import Session

from betman_voice.api.schemas import LoginRequest, LoginResponse, TtsRequest, TtsResponse, VoiceUpsert
from betman_voice.core.auth import issue_token, password_verify, require_principal
from betman_voice.core.config import get_settings
from betman_voice.core.logging import configure_logging, get_logger
from betman_voice.core.runtime import detect_runtime
from betman_voice.db.bootstrap import bootstrap_defaults
from betman_voice.db.models import GenerationJob, User, Voice
from betman_voice.db.session import Base, SessionLocal, engine, get_db
from betman_voice.services.jobs import enqueue_generation, run_generation_job
from betman_voice.services.elevenlabs_import import import_betman_elevenlabs_voices

REQUESTS = Counter("betman_voice_requests_total", "HTTP requests", ["path", "method", "status"])
LATENCY = Histogram("betman_voice_request_seconds", "HTTP latency", ["path", "method"])
GENERATIONS = Counter("betman_voice_generations_total", "Voice generations", ["status", "backend"])
log = get_logger(__name__)


def create_app() -> FastAPI:
    configure_logging()
    app = FastAPI(title="BETMAN_Voice", version="0.1.0")
    settings = get_settings()

    @app.on_event("startup")
    def startup() -> None:
        Base.metadata.create_all(bind=engine)
        with SessionLocal() as db:
            bootstrap_defaults(db)
        Path(settings.local_storage_dir).mkdir(parents=True, exist_ok=True)
        log.info("app_started", env=settings.env, runtime=detect_runtime().__dict__)

    @app.middleware("http")
    async def metrics_middleware(request: Request, call_next):
        with LATENCY.labels(request.url.path, request.method).time():
            response = await call_next(request)
        REQUESTS.labels(request.url.path, request.method, response.status_code).inc()
        return response

    @app.get("/health")
    def health() -> dict:
        runtime = detect_runtime()
        return {"ok": True, "service": "BETMAN_Voice", "runtime": runtime.__dict__}

    @app.get("/metrics")
    def metrics() -> Response:
        return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

    @app.post("/auth/login", response_model=LoginResponse)
    def login(body: LoginRequest, db: Session = Depends(get_db)) -> LoginResponse:
        user = db.query(User).filter(User.email == body.email, User.active.is_(True)).first()
        if not user or not password_verify(body.password, user.password_hash):
            raise HTTPException(401, "invalid_credentials")
        return LoginResponse(token=issue_token(user))

    @app.get("/voices")
    def voices(
        principal: dict = Depends(require_principal),
        db: Session = Depends(get_db),
    ) -> dict:
        rows = (
            db.query(Voice)
            .filter(Voice.tenant_id == principal["tenant_id"], Voice.active.is_(True))
            .order_by(Voice.name.asc())
            .all()
        )
        return {
            "voices": [
                {
                    "voice_id": row.voice_id,
                    "name": row.name,
                    "description": row.description,
                    "preview_url": row.sample_url,
                    "model_backend": row.model_backend,
                }
                for row in rows
            ]
        }

    @app.post("/admin/voices")
    def upsert_voice(
        body: VoiceUpsert,
        principal: dict = Depends(require_principal),
        db: Session = Depends(get_db),
    ) -> dict:
        if principal.get("role") not in {"admin", "service"}:
            raise HTTPException(403, "admin_required")
        voice = (
            db.query(Voice)
            .filter(Voice.tenant_id == principal["tenant_id"], Voice.voice_id == body.voice_id)
            .first()
        )
        if not voice:
            voice = Voice(tenant_id=principal["tenant_id"], voice_id=body.voice_id, name=body.name)
            db.add(voice)
        voice.name = body.name
        voice.description = body.description
        voice.model_backend = body.model_backend
        voice.model_ref = body.model_ref
        voice.sample_url = body.sample_url
        voice.settings = body.settings
        db.commit()
        return {"ok": True, "voice_id": voice.voice_id}

    @app.post("/admin/import/elevenlabs")
    def import_elevenlabs(
        body: dict,
        principal: dict = Depends(require_principal),
        db: Session = Depends(get_db),
    ) -> dict:
        if principal.get("role") not in {"admin", "service"}:
            raise HTTPException(403, "admin_required")
        api_key = str(body.get("api_key") or "").strip()
        return import_betman_elevenlabs_voices(db, principal["tenant_id"], api_key=api_key)

    @app.post("/tts", response_model=TtsResponse)
    def tts(
        body: TtsRequest,
        principal: dict = Depends(require_principal),
        db: Session = Depends(get_db),
    ) -> TtsResponse:
        voice_id = body.voiceId or body.voiceName or "betman-female-presenter"
        job = enqueue_generation(
            db,
            principal["tenant_id"],
            voice_id,
            body.text,
            model_id=body.model_id or "",
            request_meta={"voice_settings": body.voice_settings or {}, "compat": "betman"},
        )
        if body.async_job:
            return TtsResponse(ok=True, id=str(job.id), status=job.status)
        job = run_generation_job(db, job)
        GENERATIONS.labels(job.status, job.backend or "none").inc()
        return _job_response(job)

    @app.post("/generate", response_model=TtsResponse)
    def generate(body: TtsRequest, principal: dict = Depends(require_principal), db: Session = Depends(get_db)):
        return tts(body, principal, db)

    @app.get("/jobs/{job_id}", response_model=TtsResponse)
    def job_status(job_id: str, principal: dict = Depends(require_principal), db: Session = Depends(get_db)):
        job = (
            db.query(GenerationJob)
            .filter(GenerationJob.id == job_id, GenerationJob.tenant_id == principal["tenant_id"])
            .first()
        )
        if not job:
            raise HTTPException(404, "job_not_found")
        return _job_response(job)

    @app.post("/v1/text-to-speech/{voice_id}")
    def elevenlabs_tts(
        voice_id: str,
        body: dict,
        principal: dict = Depends(require_principal),
        db: Session = Depends(get_db),
    ) -> Response:
        text = str(body.get("text") or "").strip()
        if not text:
            raise HTTPException(400, "text_required")
        job = enqueue_generation(
            db,
            principal["tenant_id"],
            voice_id,
            text,
            model_id=str(body.get("model_id") or ""),
            request_meta={"voice_settings": body.get("voice_settings") or {}, "compat": "elevenlabs"},
        )
        job = run_generation_job(db, job)
        GENERATIONS.labels(job.status, job.backend or "none").inc()
        if job.status != "completed":
            raise HTTPException(502, job.error or "generation_failed")
        audio_path = Path(settings.local_storage_dir) / job.storage_key
        if settings.storage_backend.lower() == "local" and audio_path.exists():
            return FileResponse(audio_path, media_type=job.mime_type)
        return Response(status_code=302, headers={"location": job.audio_url})

    @app.get("/v1/voices")
    def elevenlabs_voices(principal: dict = Depends(require_principal), db: Session = Depends(get_db)):
        return voices(principal, db)

    @app.get("/audio/{tenant_id}/{filename}")
    def audio(tenant_id: str, filename: str):
        target = Path(settings.local_storage_dir) / tenant_id / filename
        if not target.exists():
            raise HTTPException(404, "audio_not_found")
        return FileResponse(target, media_type="audio/wav")

    static_dir = Path(__file__).resolve().parents[3] / "static"
    if static_dir.exists():
        app.mount("/static", StaticFiles(directory=static_dir), name="static")

    @app.get("/admin", response_class=HTMLResponse)
    def admin_ui():
        index = static_dir / "admin.html"
        if index.exists():
            return HTMLResponse(index.read_text())
        return HTMLResponse("<h1>BETMAN_Voice</h1>")

    return app


def _job_response(job: GenerationJob) -> TtsResponse:
    return TtsResponse(
        ok=job.status == "completed",
        id=str(job.id),
        status=job.status,
        audio_url=job.audio_url or None,
        backend=job.backend or None,
        duration_ms=job.duration_ms or 0,
        error=job.error or None,
    )
