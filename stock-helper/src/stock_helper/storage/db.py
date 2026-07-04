"""Engine and session management. All DB access goes through here so swapping
SQLite for DuckDB/Postgres later is a connection-string change."""

from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import Engine
from sqlmodel import Session, SQLModel, create_engine

from stock_helper.core.config import Settings, get_settings

_engines: dict[str, Engine] = {}


def get_engine(settings: Settings | None = None) -> Engine:
    settings = settings or get_settings()
    url = settings.db_url
    if url not in _engines:
        _engines[url] = create_engine(url)
    return _engines[url]


def init_db(settings: Settings | None = None) -> None:
    settings = settings or get_settings()
    settings.ensure_dirs()
    # Import models so all tables are registered before create_all.
    from stock_helper.storage import models  # noqa: F401

    SQLModel.metadata.create_all(get_engine(settings))


@contextmanager
def get_session(settings: Settings | None = None) -> Iterator[Session]:
    # expire_on_commit=False: report objects hold ORM rows (Company, Filing)
    # that are rendered after the session closes.
    with Session(get_engine(settings), expire_on_commit=False) as session:
        yield session
