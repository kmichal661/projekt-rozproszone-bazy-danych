from __future__ import annotations

from .common import measure_repeated_queries, query_products
from .test_catalog import DESCRIPTIONS
from .test_models import Measurement, TestResult


def run(repetitions: tuple[int, ...] = (1, 10, 100)) -> TestResult:
    measurements: list[Measurement] = []
    query = query_products()
    for count in repetitions:
        total_ms, average_ms, errors = measure_repeated_queries(query, count)
        measurements.append(
            Measurement(
                variant=f"{count} zapytań",
                success=errors == 0,
                values={
                    "czas całkowity": round(total_ms, 3),
                    "średni czas": round(average_ms, 3),
                    "błędy": errors,
                },
                conclusion=(
                    "Wszystkie zapytania zakończyły się poprawnie."
                    if errors == 0
                    else f"Wystąpiło {errors} błędów."
                ),
            )
        )
    description = DESCRIPTIONS["load"]
    return TestResult(**description.__dict__, measurements=measurements)