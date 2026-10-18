from __future__ import annotations

from .common import graphql, query_products
from .data_generator import cleanup_generated_data, generate_products
from .test_catalog import DESCRIPTIONS
from .test_models import Measurement, TestResult


def run(sizes: tuple[int, ...] = (100, 1000, 10000)) -> TestResult:
    measurements: list[Measurement] = []
    try:
        for size in sizes:
            generate_products(size)
            result, elapsed_ms = graphql(query_products())
            products = result.get("data", {}).get("products", []) or []
            generated_products = [
                product for product in products if product.get("sku", "").startswith("PERF-")
            ]
            returned = len(generated_products)
            total_returned = len(products)
            success = not result.get("errors") and returned == size
            measurements.append(
                Measurement(
                    variant=f"{size:,} rekordów".replace(",", " "),
                    success=success,
                    values={
                        "czas odpowiedzi [ms]": round(elapsed_ms, 3),
                        "wygenerowane rekordy": returned,
                        "wszystkie rekordy w katalogu": total_returned,
                    },
                    conclusion=(
                        "Zapytanie zwróciło oczekiwaną liczbę rekordów."
                        if success
                        else "Liczba rekordów lub wykonanie zapytania jest niepoprawne."
                    ),
                )
            )
    finally:
        cleanup_generated_data()
    description = DESCRIPTIONS["response_time"]
    return TestResult(**description.__dict__, measurements=measurements)