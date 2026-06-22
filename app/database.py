from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool
from app.config import settings

_is_sqlite = settings.database_url.startswith("sqlite")

engine = create_engine(
    settings.database_url,
    # SQLite needs this for multi-threaded use; PostgreSQL does not
    connect_args={"check_same_thread": False} if _is_sqlite else {},
    # NullPool: open/close a fresh connection per request.
    # Required on serverless platforms (Vercel) where there is no
    # persistent process to hold a connection pool.
    poolclass=None if _is_sqlite else NullPool,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
