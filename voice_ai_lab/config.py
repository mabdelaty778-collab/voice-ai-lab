"""Explicit lab settings; no production database or CRM settings are consumed."""

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


@dataclass(frozen=True)
class Settings:
    api_key: str
    db_path: Path
    fail_writes: bool = False

    @classmethod
    def from_env(cls) -> "Settings":
        load_dotenv(Path.cwd() / ".env", override=False)
        key = os.getenv("LAB_API_KEY", "").strip()
        if len(key) < 24:
            raise RuntimeError("Run python scripts/setup_lab.py to create a local lab key.")
        return cls(
            api_key=key,
            db_path=Path(os.getenv("LAB_DB_PATH", ".local/lab.sqlite3")),
            fail_writes=os.getenv("LAB_FAIL_WRITES", "false").lower() == "true",
        )
