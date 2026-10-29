import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    app_name: str = os.getenv("APP_NAME", "LLM Evaluation & Observability")
    environment: str = os.getenv("ENVIRONMENT", "development")
    db_path: str = os.getenv("EVAL_DB_PATH", "./data/evaluations.sqlite3")
    openai_default_model: str = os.getenv("OPENAI_DEFAULT_MODEL", "gpt-4o-mini")

    def ensure_data_dir(self) -> None:
        Path(self.db_path).expanduser().parent.mkdir(parents=True, exist_ok=True)


settings = Settings()
