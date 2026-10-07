from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import get_settings


class Base(DeclarativeBase):
    pass


def normalize_database_url(database_url: str) -> str:
    """Supabase and Render hand out `postgresql://` (or `postgres://`) URLs, which SQLAlchemy maps
    to psycopg2. We ship psycopg 3, so point those at it."""
    for prefix in ("postgresql://", "postgres://"):
        if database_url.startswith(prefix):
            return "postgresql+psycopg://" + database_url[len(prefix) :]
    return database_url


def make_engine(database_url: str) -> Engine:
    database_url = normalize_database_url(database_url)
    if database_url.startswith("sqlite"):
        kwargs: dict = {"connect_args": {"check_same_thread": False}}
        if ":memory:" in database_url:
            kwargs["poolclass"] = StaticPool  # one shared connection, or each session sees an empty DB
        return create_engine(database_url, **kwargs)
    return create_engine(database_url, pool_pre_ping=True)


engine = make_engine(get_settings().database_url)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def create_all() -> None:
    from app.db import models  # noqa: F401  (registers the tables on Base.metadata)

    Base.metadata.create_all(engine)
    enable_row_level_security(engine)


def enable_row_level_security(target: Engine) -> None:
    """Supabase exposes every table in `public` through its REST API to anyone holding the project's
    public anon key. Turning on RLS with no policies closes that door; this backend connects as the
    `postgres` owner role, which bypasses RLS, so it is unaffected. No-op on SQLite. Idempotent."""
    if target.dialect.name != "postgresql":
        return
    with target.begin() as conn:
        for table in Base.metadata.sorted_tables:
            conn.exec_driver_sql(f'ALTER TABLE "{table.name}" ENABLE ROW LEVEL SECURITY')
