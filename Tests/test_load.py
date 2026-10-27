from __future__ import annotations

from .common import GraphQLClient, products_query
from .config import load_settings
from .test_catalog import CATALOG
from .test_models import Measurement, TestResult


def run(repetitions: tuple[int, ...] = (1, 10, 100)) -> TestResult:
    client = GraphQLClient(load_settings().graphql_url)
    measurements = []
    for count in repetitions:
        total_ms, average_ms, errors = client.measure_repeated(products_query(), count)
        measurements.append(
            Measurement(
                variant=f"{count} zapytań",
                success=errors == 0,
                values={"czas całkowity (ms)": round(total_ms, 3), "średni czas (ms)": round(average_ms, 3), "błędy": errors},
                conclusion="Wszystkie odpowiedzi są poprawne." if errors == 0 else f"Wystąpiło {errors} błędów.",
            )
        )
    return TestResult(definition=CATALOG["load"], measurements=measurements)
