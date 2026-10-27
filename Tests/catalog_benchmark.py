"""Reusable benchmark scenario for catalog reads."""

from __future__ import annotations

from .common import GraphQLClient, products_query
from .data_generator import PERFORMANCE_PREFIX, TestDataRepository
from .test_models import Measurement, TestDefinition, TestResult


def run_catalog_benchmark(
    definition: TestDefinition,
    client: GraphQLClient,
    repository: TestDataRepository,
    sizes: tuple[int, ...] = (100, 1_000, 10_000),
) -> TestResult:
    measurements: list[Measurement] = []
    try:
        for size in sizes:
            repository.cleanup()
            repository.create_performance_products(size)
            response = client.execute(products_query())
            products = response.data("products", []) or []
            returned = sum(product.get("sku", "").startswith(PERFORMANCE_PREFIX) for product in products)
            success = not response.has_errors and returned == size
            measurements.append(
                Measurement(
                    variant=f"{size:,} produktów".replace(",", " "),
                    success=success,
                    values={
                        "czas odpowiedzi (ms)": round(response.elapsed_ms, 3),
                        "produkty testowe": returned,
                        "wszystkie produkty": len(products),
                    },
                    conclusion=(
                        "API zwróciło komplet danych testowych."
                        if success else "Odpowiedź zawiera błąd lub niepełny zestaw danych."
                    ),
                )
            )
    finally:
        repository.cleanup()
    return TestResult(definition=definition, measurements=measurements)
