import os
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True, extra="ignore")

    PROJECT_NAME: str = "AEGISSTOR"
    PROJECT_VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    
    # Storage operational mode: 'demo' | 'replay' | 'live'
    OPERATING_MODE: str = os.getenv("AEGISSTOR_MODE", "demo")
    
    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./aegisstor.db")
    
    # Security & Shadow Mode
    SECRET_KEY: str = os.getenv("SECRET_KEY", "aegisstor-enterprise-resilience-secret-key-2026")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24
    SHADOW_MODE_ENABLED: bool = True  # Hard safety: mutations to real storage hardware disabled
    PHYSICAL_MUTATION_DISABLED: bool = True  # Hard safety: physical storage disk mutations strictly disabled
    
    # Telemetry parameters
    TELEMETRY_SAMPLING_MINUTES: int = 60
    DEFAULT_FORECAST_HORIZON_HOURS: int = 72
    
    # Uncertainty nominal coverage (e.g. 80% interval: [q10, q90])
    NOMINAL_COVERAGE: float = 0.80

    # CORS configuration
    CORS_ALLOWED_ORIGINS: str = os.getenv("CORS_ALLOWED_ORIGINS", "*")

    # Disaster Recovery & Vault Backup
    BACKUP_STORAGE_DIR: str = os.getenv("BACKUP_STORAGE_DIR", "vault_backups")
    DEFAULT_RPO_HOURS: float = 1.0  # Recovery Point Objective: Max 1 hour data loss
    DEFAULT_RTO_SECONDS: float = 60.0  # Recovery Time Objective: Target under 60 seconds
    MAX_BACKUPS_RETAINED: int = 10


settings = Settings()
