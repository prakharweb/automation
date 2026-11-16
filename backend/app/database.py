"""
Database Connection & Session Management (app/database.py)
Supports Neon PostgreSQL via SQLAlchemy in production (Render) and falls back cleanly
to SQLite when running local unit tests or inside offline sandbox environments.
"""
from typing import Generator
from app.config import settings

try:
    from sqlalchemy import (
        Boolean,
        Column,
        DateTime,
        Float,
        ForeignKey,
        Integer,
        JSON,
        String,
        Text,
        and_,
        create_engine,
        or_,
    )
    from sqlalchemy.exc import IntegrityError
    from sqlalchemy.orm import Session, declarative_base, relationship, sessionmaker

    USING_NATIVE_SQLALCHEMY = True
except ImportError:
    from app.utils.orm_compat import (  # type: ignore
        Boolean,
        Column,
        CompatSession as Session,
        DateTime,
        Float,
        ForeignKey,
        Integer,
        IntegrityError,
        JSON,
        String,
        Text,
        and_,
        create_engine,
        declarative_base,
        or_,
        relationship,
        sessionmaker,
    )

    USING_NATIVE_SQLALCHEMY = False


db_url = settings.normalized_database_url
connect_args = {}
engine_kwargs = {}

if db_url.startswith("sqlite"):
    connect_args = {"check_same_thread": False}
else:
    engine_kwargs = {
        "pool_pre_ping": True,
        "pool_size": 5,
        "max_overflow": 10,
        "pool_recycle": 300,
    }

engine = create_engine(db_url, connect_args=connect_args, **engine_kwargs)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
