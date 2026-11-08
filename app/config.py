"""Runtime configuration, read from environment variables.

Non-secret values come from the Helm ConfigMap/env. Secrets (SQL password, when
DB_AUTH=sql) are read from files mounted by the Key Vault CSI driver.
"""
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    environment: str = "local"
    db_server: str = ""  # e.g. myserver.database.windows.net
    db_name: str = ""
    db_auth: str = "entra"  # "entra" (workload identity) or "sql" (user/password files)
    db_driver: str = "ODBC Driver 18 for SQL Server"
    secrets_dir: str = "/mnt/secrets"
    readiness_timeout_seconds: int = 3

    def secret(self, name: str) -> str:
        path = Path(self.secrets_dir) / name
        return path.read_text().strip() if path.exists() else ""


@lru_cache
def get_settings() -> Settings:
    return Settings()
