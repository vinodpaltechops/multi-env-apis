"""Azure SQL access via SQLAlchemy + pyodbc."""
import struct
from functools import lru_cache

from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL, Engine

from app.config import Settings, get_settings

SQL_COPT_SS_ACCESS_TOKEN = 1256  # msodbcsql pre-connect attribute
_SQL_SCOPE = "https://database.windows.net/.default"


def _token_struct() -> bytes:
    from azure.identity import DefaultAzureCredential  # lazy: only needed for Entra auth

    token = DefaultAzureCredential().get_token(_SQL_SCOPE).token.encode("utf-16-le")
    return struct.pack(f"<I{len(token)}s", len(token), token)


def build_engine(settings: Settings) -> Engine:
    query = {"driver": settings.db_driver, "Encrypt": "yes", "TrustServerCertificate": "no"}
    if settings.db_auth == "sql":
        url = URL.create(
            "mssql+pyodbc",
            username=settings.secret("db-user"),
            password=settings.secret("db-password"),
            host=settings.db_server,
            database=settings.db_name,
            query=query,
        )
        return create_engine(url, pool_pre_ping=True)
    url = URL.create(
        "mssql+pyodbc", host=settings.db_server, database=settings.db_name, query=query
    )
    # Token is fetched per new physical connection, so it never goes stale in the pool.
    return create_engine(
        url,
        pool_pre_ping=True,
        pool_recycle=1800,
        connect_args={"attrs_before": {SQL_COPT_SS_ACCESS_TOKEN: _token_struct()}},
    )


@lru_cache
def get_engine() -> Engine:
    return build_engine(get_settings())


def check_database() -> None:
    """Raise if the database is unreachable."""
    with get_engine().connect() as conn:
        conn.execute(text("SELECT 1"))
