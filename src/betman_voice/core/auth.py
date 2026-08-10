from __future__ import annotations

import hashlib
import hmac
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from betman_voice.core.config import get_settings
from betman_voice.db.models import ApiKey, User
from betman_voice.db.session import get_db

pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")
bearer = HTTPBearer(auto_error=False)


def hash_secret(secret: str) -> str:
    return hashlib.sha256(secret.encode("utf-8")).hexdigest()


def verify_secret(secret: str, hashed: str) -> bool:
    return hmac.compare_digest(hash_secret(secret), hashed)


def password_hash(password: str) -> str:
    return pwd_context.hash(password)


def password_verify(password: str, hashed: str) -> bool:
    return pwd_context.verify(password, hashed)


def issue_token(user: User) -> str:
    settings = get_settings()
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user.id),
        "tenant_id": str(user.tenant_id),
        "email": user.email,
        "role": user.role,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(hours=12)).timestamp()),
    }
    return jwt.encode(payload, settings.secret_key, algorithm="HS256")


def require_principal(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: Session = Depends(get_db),
) -> dict:
    api_key = request.headers.get("xi-api-key") or request.headers.get("x-api-key")
    if api_key:
        hashed = hash_secret(api_key)
        key = db.query(ApiKey).filter(ApiKey.key_hash == hashed, ApiKey.revoked_at.is_(None)).first()
        if key:
            return {"tenant_id": str(key.tenant_id), "role": key.role, "auth": "api_key"}

    if credentials and credentials.scheme.lower() == "bearer":
        try:
            payload = jwt.decode(credentials.credentials, get_settings().secret_key, algorithms=["HS256"])
            return {
                "tenant_id": payload["tenant_id"],
                "role": payload.get("role", "user"),
                "auth": "jwt",
                "user_id": payload.get("sub"),
            }
        except jwt.PyJWTError as exc:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid_token") from exc

    raise HTTPException(status.HTTP_401_UNAUTHORIZED, "authentication_required")
