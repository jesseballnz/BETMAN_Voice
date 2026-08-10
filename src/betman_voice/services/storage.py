from __future__ import annotations

from pathlib import Path

import boto3

from betman_voice.core.config import get_settings


class Storage:
    def put_audio(self, key: str, data: bytes, content_type: str) -> str:
        settings = get_settings()
        if settings.storage_backend.lower() == "spaces":
            client = boto3.client(
                "s3",
                region_name=settings.spaces_region,
                endpoint_url=settings.spaces_endpoint,
                aws_access_key_id=settings.spaces_access_key_id,
                aws_secret_access_key=settings.spaces_secret_access_key,
            )
            client.put_object(
                Bucket=settings.spaces_bucket,
                Key=key,
                Body=data,
                ContentType=content_type,
                ACL="public-read",
            )
            base_url = settings.spaces_public_base_url or (
                f"https://{settings.spaces_bucket}.{settings.spaces_region}.digitaloceanspaces.com"
            )
            return f"{base_url.rstrip('/')}/{key}"

        target = Path(settings.local_storage_dir) / key
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        return f"{settings.public_base_url.rstrip('/')}/audio/{key}"


storage = Storage()
