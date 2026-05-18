"""
Veritabanı bağlantısı ve oturum yönetimi.
SQLAlchemy engine ve Session fabrikasını sağlar.
"""

from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from src.utils.config import config
from src.utils.logger import get_logger

logger = get_logger(__name__)


class Base(DeclarativeBase):
    """Tüm SQLAlchemy modelleri için temel sınıf."""
    pass


def _create_engine():
    """Engine oluşturur; SQLite için foreign key desteğini aktif eder."""
    engine = create_engine(
        config.DATABASE_URL,
        connect_args={"check_same_thread": False} if "sqlite" in config.DATABASE_URL else {},
        echo=config.APP_DEBUG,
    )

    # SQLite için foreign key kısıtlamalarını etkinleştir
    if "sqlite" in config.DATABASE_URL:
        @event.listens_for(engine, "connect")
        def set_sqlite_pragma(dbapi_conn, _):
            cursor = dbapi_conn.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    logger.info("Veritabanı bağlantısı oluşturuldu: %s", config.DATABASE_URL)
    return engine


engine = _create_engine()

SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
)


@contextmanager
def get_db() -> Generator[Session, None, None]:
    """
    Context manager ile veritabanı oturumu sağlar.
    Hata durumunda otomatik rollback yapar.

    Usage:
        with get_db() as db:
            db.add(record)
            db.commit()
    """
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
