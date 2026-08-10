#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json

from betman_voice.db.bootstrap import bootstrap_defaults
from betman_voice.db.models import Tenant
from betman_voice.db.session import Base, SessionLocal, engine
from betman_voice.services.training import enqueue_training_job, run_training_job


def main() -> None:
    parser = argparse.ArgumentParser(description="Queue or run a BETMAN voice training job")
    parser.add_argument("voice_id")
    parser.add_argument("--tenant", default="betman")
    parser.add_argument("--source", default="elevenlabs")
    parser.add_argument("--run-now", action="store_true")
    args = parser.parse_args()

    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        bootstrap_defaults(db)
        tenant = db.query(Tenant).filter(Tenant.slug == args.tenant).one()
        job = enqueue_training_job(db, tenant.id, args.voice_id, source=args.source)
        if args.run_now:
            job = run_training_job(db, job)
        print(
            json.dumps(
                {
                    "ok": True,
                    "id": job.id,
                    "voice_id": job.voice_id,
                    "status": job.status,
                    "sample_count": job.sample_count,
                    "manifest_path": job.manifest_path,
                    "model_ref": job.model_ref,
                    "error": job.error,
                },
                indent=2,
            )
        )


if __name__ == "__main__":
    main()
