from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from betman_voice.db.session import Base


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def uuid_pk():
    return mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))


class Tenant(Base):
    __tablename__ = "tenants"

    id: Mapped[str] = uuid_pk()
    slug: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(160))
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)

    voices = relationship("Voice", back_populates="tenant")


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = uuid_pk()
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id"), index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(40), default="admin")
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)


class ApiKey(Base):
    __tablename__ = "api_keys"

    id: Mapped[str] = uuid_pk()
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id"), index=True)
    name: Mapped[str] = mapped_column(String(120))
    key_hash: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    role: Mapped[str] = mapped_column(String(40), default="service")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Voice(Base):
    __tablename__ = "voices"
    __table_args__ = (UniqueConstraint("tenant_id", "voice_id", name="uq_voice_tenant_voice_id"),)

    id: Mapped[str] = uuid_pk()
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id"), index=True)
    voice_id: Mapped[str] = mapped_column(String(120), index=True)
    name: Mapped[str] = mapped_column(String(160))
    description: Mapped[str] = mapped_column(Text, default="")
    model_backend: Mapped[str] = mapped_column(String(80), default="auto")
    model_ref: Mapped[str] = mapped_column(String(255), default="")
    sample_url: Mapped[str] = mapped_column(Text, default="")
    settings: Mapped[dict] = mapped_column(JSON, default=dict)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)

    tenant = relationship("Tenant", back_populates="voices")


class GenerationJob(Base):
    __tablename__ = "generation_jobs"

    id: Mapped[str] = uuid_pk()
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id"), index=True)
    voice_id: Mapped[str] = mapped_column(String(120), index=True)
    text: Mapped[str] = mapped_column(Text)
    model_id: Mapped[str] = mapped_column(String(120), default="")
    status: Mapped[str] = mapped_column(String(40), default="queued", index=True)
    backend: Mapped[str] = mapped_column(String(80), default="")
    storage_key: Mapped[str] = mapped_column(Text, default="")
    audio_url: Mapped[str] = mapped_column(Text, default="")
    mime_type: Mapped[str] = mapped_column(String(120), default="audio/wav")
    duration_ms: Mapped[int] = mapped_column(Integer, default=0)
    error: Mapped[str] = mapped_column(Text, default="")
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    request_meta: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc, index=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
