#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os

from betman_voice.db.bootstrap import bootstrap_defaults
from betman_voice.db.models import Tenant
from betman_voice.db.session import Base, SessionLocal, engine
from betman_voice.services.elevenlabs_import import import_betman_elevenlabs_voices


def main() -> None:
    parser = argparse.ArgumentParser(description="Poll ElevenLabs and refresh BETMAN voice metadata")
    parser.add_argument("--tenant", default="betman")
    parser.add_argument("--api-key", default=os.getenv("ELEVENLABS_API_KEY", ""))
    args = parser.parse_args()

    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        bootstrap_defaults(db)
        tenant = db.query(Tenant).filter(Tenant.slug == args.tenant).one()
        result = import_betman_elevenlabs_voices(db, tenant.id, api_key=args.api_key)
        print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
