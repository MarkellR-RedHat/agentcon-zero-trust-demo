from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", case_sensitive=False)

    host: str = "0.0.0.0"
    port: int = 8000

    # Which runs_summary.json the app serves. Points at the synthetic fixture until the real run
    # is imported; set RUNS_DIR to the real run folder then.
    runs_dir: str = "runs/qwen-r2"

    # "replay" plays the recorded transcripts; "live" would drive real endpoints (not wired in the
    # booth build: the booth runs replay, which is the plan).
    demo_mode: str = "replay"


@lru_cache
def settings() -> Settings:
    return Settings()


@lru_cache
def summary() -> dict:
    path = ROOT / settings().runs_dir / "runs_summary.json"
    return json.loads(path.read_text())


def is_synthetic() -> bool:
    return summary()["run"].get("tag") == "SYNTHETIC" or "SYNTHETIC" in summary()["run"].get("runtime", "")
