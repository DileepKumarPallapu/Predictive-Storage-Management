import hashlib
import logging
import os
from pathlib import Path
from typing import Optional, Tuple

from app.config import settings

logger = logging.getLogger("aegisstor.storage")


def compute_sha256(file_path: str) -> str:
    """Compute SHA-256 hex digest of a local file."""
    h = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


class DurableObjectStorage:
    """
    S3-compatible durable object storage for ML model binaries, generated PDF reports,
    and uploaded telemetry archives, with verified local cache fallback for local/test runs.
    """

    def __init__(self) -> None:
        self.bucket = (settings.OBJECT_STORAGE_BUCKET or "").strip()
        self.endpoint_url = (settings.OBJECT_STORAGE_ENDPOINT_URL or "").strip() or None
        self.region = (settings.OBJECT_STORAGE_REGION or "us-east-1").strip()
        self.prefix = (settings.OBJECT_STORAGE_PREFIX or "aegisstor").strip("/")
        self._client = None

    @property
    def is_remote_enabled(self) -> bool:
        return bool(
            self.bucket
            and settings.OBJECT_STORAGE_ACCESS_KEY_ID
            and settings.OBJECT_STORAGE_SECRET_ACCESS_KEY
        )

    def _get_s3_client(self):
        if self._client is not None:
            return self._client
        if not self.is_remote_enabled:
            return None
        try:
            import boto3  # type: ignore

            self._client = boto3.client(
                "s3",
                endpoint_url=self.endpoint_url,
                region_name=self.region,
                aws_access_key_id=settings.OBJECT_STORAGE_ACCESS_KEY_ID,
                aws_secret_access_key=settings.OBJECT_STORAGE_SECRET_ACCESS_KEY,
            )
            return self._client
        except Exception as exc:
            logger.warning("S3 client initialization failed, falling back to local cache: %s", exc)
            return None

    def build_key(self, category: str, filename: str) -> str:
        safe_cat = category.strip("/")
        safe_name = os.path.basename(filename)
        return f"{self.prefix}/{safe_cat}/{safe_name}"

    def put_file(self, local_path: str, category: str, filename: Optional[str] = None) -> Tuple[str, str]:
        """
        Persist local_path to durable object storage (if configured) and return (uri, sha256).
        Local dev/test falls back to `local://<abs_path>`.
        """
        if not os.path.exists(local_path):
            raise FileNotFoundError(f"Cannot store missing artifact: {local_path}")
        checksum = compute_sha256(local_path)
        name = filename or os.path.basename(local_path)
        key = self.build_key(category, name)

        client = self._get_s3_client()
        if client is not None:
            client.upload_file(
                local_path,
                self.bucket,
                key,
                ExtraArgs={"Metadata": {"sha256": checksum}},
            )
            return f"s3://{self.bucket}/{key}", checksum

        return f"local://{os.path.abspath(local_path)}", checksum

    def ensure_local_file(
        self,
        local_path: str,
        remote_uri: Optional[str] = None,
        expected_sha256: Optional[str] = None,
    ) -> str:
        """
        Ensure artifact exists locally (downloading from S3 URI if needed) and verify SHA-256 if provided.
        """
        if not os.path.exists(local_path) and remote_uri and remote_uri.startswith("s3://"):
            client = self._get_s3_client()
            if client is None:
                raise RuntimeError("S3 artifact requested but object storage credentials are not configured.")
            without_scheme = remote_uri[len("s3://"):]
            bucket, _, key = without_scheme.partition("/")
            Path(local_path).parent.mkdir(parents=True, exist_ok=True)
            client.download_file(bucket, key, local_path)

        if not os.path.exists(local_path):
            raise FileNotFoundError(f"Artifact not found at {local_path} (remote={remote_uri})")

        if expected_sha256:
            actual = compute_sha256(local_path)
            if actual != expected_sha256:
                raise ValueError(
                    f"Artifact checksum mismatch for {local_path}: expected {expected_sha256}, got {actual}"
                )
        return local_path

    def status_summary(self) -> dict:
        return {
            "provider": "s3_compatible" if self.is_remote_enabled else "local_filesystem",
            "durable_remote_configured": self.is_remote_enabled,
            "bucket": self.bucket if self.is_remote_enabled else None,
            "endpoint_configured": bool(self.endpoint_url),
        }


object_storage = DurableObjectStorage()
