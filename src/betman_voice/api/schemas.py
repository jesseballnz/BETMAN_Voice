from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    email: str
    password: str


class LoginResponse(BaseModel):
    token: str


class TtsRequest(BaseModel):
    text: str = Field(min_length=1, max_length=12000)
    voiceId: str | None = None
    voiceName: str | None = None
    model_id: str | None = None
    voice_settings: dict | None = None
    async_job: bool = False


class TtsResponse(BaseModel):
    ok: bool
    id: str
    status: str
    audio_url: str | None = None
    backend: str | None = None
    duration_ms: int = 0
    error: str | None = None


class TrainingRequest(BaseModel):
    source: str = "elevenlabs"
    force: bool = False
    metadata: dict = Field(default_factory=dict)


class TrainingResponse(BaseModel):
    ok: bool
    id: str
    voice_id: str
    status: str
    source: str = "elevenlabs"
    sample_count: int = 0
    dataset_path: str = ""
    manifest_path: str = ""
    model_ref: str = ""
    error: str | None = None


class VoiceUpsert(BaseModel):
    voice_id: str
    name: str
    description: str = ""
    model_backend: str = "auto"
    model_ref: str = ""
    sample_url: str = ""
    settings: dict = Field(default_factory=dict)
