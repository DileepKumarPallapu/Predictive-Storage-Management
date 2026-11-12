import os
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True, extra="ignore")

    PROJECT_NAME: str = "AEGISSTOR"
    PROJECT_VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"

    # Deployment environment: 'local' | 'staging' | 'production'
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "local").lower()

    # Storage operational mode: 'demo' | 'replay' | 'live'
    OPERATING_MODE: str = os.getenv("AEGISSTOR_MODE", "demo")

    # Database & Pooling
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./aegisstor.db")
    DB_POOL_SIZE: int = int(os.getenv("DB_POOL_SIZE", "10"))
    DB_MAX_OVERFLOW: int = int(os.getenv("DB_MAX_OVERFLOW", "20"))
    DB_POOL_TIMEOUT: int = int(os.getenv("DB_POOL_TIMEOUT", "30"))
    DB_POOL_RECYCLE: int = int(os.getenv("DB_POOL_RECYCLE", "1800"))
    DB_SSL_MODE: str = os.getenv("DB_SSL_MODE", "")

    # Security & Shadow Mode
    SECRET_KEY: str = os.getenv("SECRET_KEY", "aegisstor-enterprise-resilience-secret-key-2026")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", str(60 * 24)))
    SHADOW_MODE_ENABLED: bool = True  # Hard safety: mutations to real storage hardware disabled
    PHYSICAL_MUTATION_DISABLED: bool = True  # Hard safety: physical storage disk mutations strictly disabled

    # Request limits & timeouts
    MAX_REQUEST_BODY_BYTES: int = int(os.getenv("MAX_REQUEST_BODY_BYTES", str(25 * 1024 * 1024)))
    REQUEST_TIMEOUT_SECONDS: float = float(os.getenv("REQUEST_TIMEOUT_SECONDS", "60.0"))

    # Telemetry parameters
    TELEMETRY_SAMPLING_MINUTES: int = 60
    DEFAULT_FORECAST_HORIZON_HOURS: int = 72
    NOMINAL_COVERAGE: float = 0.80

    # CORS configuration
    CORS_ALLOWED_ORIGINS: str = os.getenv("CORS_ALLOWED_ORIGINS", "*")

    # Redis & Background Worker
    REDIS_URL: str = os.getenv("REDIS_URL", "")
    WORKER_POLL_INTERVAL_SEC: float = float(os.getenv("WORKER_POLL_INTERVAL_SEC", "2.0"))
    WORKER_HEARTBEAT_INTERVAL_SEC: int = int(os.getenv("WORKER_HEARTBEAT_INTERVAL_SEC", "15"))
    WORKER_STALE_JOB_TIMEOUT_SEC: int = int(os.getenv("WORKER_STALE_JOB_TIMEOUT_SEC", "600"))
    JOB_MAX_RETRIES: int = int(os.getenv("JOB_MAX_RETRIES", "3"))

    # Durable S3-Compatible Object Storage (models, reports, uploaded archives)
    OBJECT_STORAGE_BUCKET: str = os.getenv("OBJECT_STORAGE_BUCKET", "")
    OBJECT_STORAGE_ENDPOINT_URL: str = os.getenv("OBJECT_STORAGE_ENDPOINT_URL", "")
    OBJECT_STORAGE_REGION: str = os.getenv("OBJECT_STORAGE_REGION", "us-east-1")
    OBJECT_STORAGE_ACCESS_KEY_ID: str = os.getenv("OBJECT_STORAGE_ACCESS_KEY_ID", "")
    OBJECT_STORAGE_SECRET_ACCESS_KEY: str = os.getenv("OBJECT_STORAGE_SECRET_ACCESS_KEY", "")
    OBJECT_STORAGE_PREFIX: str = os.getenv("OBJECT_STORAGE_PREFIX", "aegisstor")

    # Prometheus Connector
    PROMETHEUS_URL: str = os.getenv("PROMETHEUS_URL", "")
    PROMETHEUS_BEARER_TOKEN: str = os.getenv("PROMETHEUS_BEARER_TOKEN", "")
    PROMETHEUS_TLS_VERIFY: bool = os.getenv("PROMETHEUS_TLS_VERIFY", "true").lower() == "true"
    PROMETHEUS_TIMEOUT_SEC: float = float(os.getenv("PROMETHEUS_TIMEOUT_SEC", "5.0"))

    # Disaster Recovery & Vault Backup
    BACKUP_STORAGE_DIR: str = os.getenv("BACKUP_STORAGE_DIR", "vault_backups")
    DEFAULT_RPO_HOURS: float = 1.0
    DEFAULT_RTO_SECONDS: float = 60.0
    MAX_BACKUPS_RETAINED: int = 10

    def validate_production_safety(self) -> None:
        """Fail fast if unsafe defaults are used in production."""
        if self.ENVIRONMENT == "production":
            default_secret = "aegisstor-enterprise-resilience-secret-key-2026"
            if not self.SECRET_KEY or self.SECRET_KEY == default_secret or len(self.SECRET_KEY) < 32:
                raise RuntimeError(
                    "PRODUCTION SECURITY ERROR: SECRET_KEY must be a unique >=32-character secret in production."
                )
            if self.CORS_ALLOWED_ORIGINS.strip() == "*":
                raise RuntimeError(
                    "PRODUCTION SECURITY ERROR: CORS_ALLOWED_ORIGINS cannot be '*' in production."
                )


settings = Settings()
