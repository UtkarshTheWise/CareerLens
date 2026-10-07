import pytest

from app.db.base import make_engine, normalize_database_url


@pytest.mark.parametrize(
    ("given", "expected"),
    [
        ("postgresql://u:p@host:5432/postgres", "postgresql+psycopg://u:p@host:5432/postgres"),
        ("postgres://u:p@host:5432/postgres", "postgresql+psycopg://u:p@host:5432/postgres"),
        ("postgresql+psycopg://u:p@host/db", "postgresql+psycopg://u:p@host/db"),
        ("sqlite:///./dev.db", "sqlite:///./dev.db"),
    ],
)
def test_plain_postgres_urls_use_the_installed_driver(given, expected):
    assert normalize_database_url(given) == expected


def test_engine_for_a_dashboard_style_url_uses_psycopg3():
    engine = make_engine("postgresql://user:secret@localhost:5432/postgres")  # no connection is opened
    assert engine.dialect.driver == "psycopg"
