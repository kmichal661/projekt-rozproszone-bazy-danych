"""Central configuration for the integration test suite."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
RESULTS_DIR = Path(os.getenv("TEST_RESULTS_DIR", Path(__file__).parent / "results"))


@dataclass(frozen=True)
class DatabaseSettings:
    host: str
    port: int
    name: str
    user: str
    password: str


@dataclass(frozen=True)
class TestSettings:
    graphql_url: str
    compose_file: Path
    databases: dict[str, DatabaseSettings]


def load_settings() -> TestSettings:
    user = os.getenv("TEST_DB_USER", "sklep")
    password = os.getenv("TEST_DB_PASSWORD", "sklep_password")
    return TestSettings(
        graphql_url=os.getenv("GRAPHQL_URL", "http://127.0.0.1:8000/graphql/"),
        compose_file=PROJECT_ROOT / "docker-compose.yml",
        databases={
            "KATOWICE": DatabaseSettings(
                host=os.getenv("TEST_KATOWICE_DB_HOST", "127.0.0.1"),
                port=int(os.getenv("TEST_KATOWICE_DB_PORT", "5433")),
                name=os.getenv("TEST_KATOWICE_DB_NAME", "sklep_katowice"),
                user=user,
                password=password,
            ),
            "KRAKOW": DatabaseSettings(
                host=os.getenv("TEST_KRAKOW_DB_HOST", "127.0.0.1"),
                port=int(os.getenv("TEST_KRAKOW_DB_PORT", "5434")),
                name=os.getenv("TEST_KRAKOW_DB_NAME", "sklep_krakow"),
                user=user,
                password=password,
            ),
        },
    )
