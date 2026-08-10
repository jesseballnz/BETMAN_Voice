#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os

from betman_voice.db.bootstrap import bootstrap_defaults
from betman_voice.db.session import Base, SessionLocal, engine
from betman_voice.services.elevenlabs_import import (
    BETMAN_ELEVENLABS_VOICES,
    import_betman_elevenlabs_voices,
    write_training_manifest,
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Import BETMAN ElevenLabs voices for local training")
    parser.add_argument("--api-key", default=os.getenv("ELEVENLABS_API_KEY", ""))
    parser.add_argument("--tenant", default=os.getenv("BETMAN_VOICE_DEFAULT_TENANT", "betman"))
    parser.add_argument("--manifest-only", action="store_true")
    args = parser.parse_args()

    manifest = write_training_manifest(args.tenant)
    if args.manifest_only:
        print(json.dumps({"ok": True, "manifest": str(manifest), "voices": BETMAN_ELEVENLABS_VOICES}, indent=2))
        return

    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        bootstrap_defaults(db)
        from betman_voice.db.models import Tenant

        tenant = db.query(Tenant).filter(Tenant.slug == args.tenant).first()
        if not tenant:
            raise SystemExit(f"tenant not found: {args.tenant}")
        result = import_betman_elevenlabs_voices(db, tenant.id, api_key=args.api_key)
    result["manifest"] = str(manifest)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
