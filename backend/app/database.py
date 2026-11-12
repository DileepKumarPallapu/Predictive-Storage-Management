import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

from app.config import settings

connect_args = {}
db_url = settings.DATABASE_URL
if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)

is_sqlite = db_url.startswith("sqlite")
if is_sqlite:
    connect_args["check_same_thread"] = False
    if db_url.startswith("sqlite:///./") or db_url == "sqlite:///aegisstor.db":
        backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        db_path = os.path.join(backend_dir, "aegisstor.db")
        db_url = f"sqlite:///{db_path}"
else:
    if settings.DB_SSL_MODE and "sslmode=" not in db_url:
        connect_args["sslmode"] = settings.DB_SSL_MODE

engine_kwargs = {
    "connect_args": connect_args,
    "pool_pre_ping": True,
}
if not is_sqlite:
    engine_kwargs.update({
        "pool_size": settings.DB_POOL_SIZE,
        "max_overflow": settings.DB_MAX_OVERFLOW,
        "pool_timeout": settings.DB_POOL_TIMEOUT,
        "pool_recycle": settings.DB_POOL_RECYCLE,
    })

engine = create_engine(db_url, **engine_kwargs)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
