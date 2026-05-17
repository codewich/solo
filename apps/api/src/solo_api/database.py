import os
from collections.abc import Iterable
from contextlib import contextmanager
from typing import Any


def database_url() -> str | None:
    return os.getenv("DATABASE_URL")


def is_database_configured() -> bool:
    return bool(database_url())


@contextmanager
def connect():
    url = database_url()
    if not url:
        raise RuntimeError("DATABASE_URL is not configured.")

    try:
        import psycopg
        from psycopg.rows import dict_row
    except ImportError as error:
        raise RuntimeError("Install psycopg to use PostgreSQL persistence.") from error

    with psycopg.connect(url, row_factory=dict_row) as connection:
        yield connection


def fetch_all(sql: str, params: Iterable[Any] = ()) -> list[dict[str, Any]]:
    with connect() as connection:
        with connection.cursor() as cursor:
            cursor.execute(sql, tuple(params))
            return list(cursor.fetchall())


def fetch_one(sql: str, params: Iterable[Any] = ()) -> dict[str, Any] | None:
    rows = fetch_all(sql, params)
    return rows[0] if rows else None


def execute(sql: str, params: Iterable[Any] = ()) -> None:
    with connect() as connection:
        with connection.cursor() as cursor:
            cursor.execute(sql, tuple(params))
        connection.commit()
