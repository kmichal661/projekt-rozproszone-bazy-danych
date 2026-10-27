from __future__ import annotations

from .catalog_benchmark import run_catalog_benchmark
from .common import GraphQLClient
from .config import load_settings
from .data_generator import TestDataRepository
from .test_catalog import CATALOG
from .test_models import TestResult


def run(sizes: tuple[int, ...] = (100, 1_000, 10_000)) -> TestResult:
    settings = load_settings()
    return run_catalog_benchmark(
        CATALOG["response_time"], GraphQLClient(settings.graphql_url), TestDataRepository(settings), sizes
    )
