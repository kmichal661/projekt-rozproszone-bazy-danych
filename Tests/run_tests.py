"""Command-line entry point for the integration-test report."""

from __future__ import annotations

import argparse
import sys
import time
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path

if __package__:
    from . import test_consistency, test_failure, test_load, test_response_time, test_scalability
    from .common import GraphQLClient
    from .config import RESULTS_DIR, load_settings
    from .report_writer import ReportWriter
    from .test_catalog import CATALOG
    from .test_models import TestResult
else:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from Tests import test_consistency, test_failure, test_load, test_response_time, test_scalability
    from Tests.common import GraphQLClient
    from Tests.config import RESULTS_DIR, load_settings
    from Tests.report_writer import ReportWriter
    from Tests.test_catalog import CATALOG
    from Tests.test_models import TestResult


Scenario = tuple[str, Callable[[], TestResult]]


class TestRunner:
    def __init__(self, scenarios: list[Scenario]):
        self.scenarios = scenarios

    def run(self) -> list[TestResult]:
        results = []
        for key, scenario in self.scenarios:
            started = time.perf_counter()
            try:
                result = scenario()
                if not isinstance(result, TestResult):
                    raise TypeError("Scenariusz musi zwrócić TestResult")
                result.duration_ms = (time.perf_counter() - started) * 1000
            except Exception as error:
                result = TestResult.failed(CATALOG[key], error, (time.perf_counter() - started) * 1000)
            results.append(result)
            print(f"[{result.definition.section}] {result.definition.name}: {'PASS' if result.success else 'FAIL'}")
        return results


def main() -> int:
    parser = argparse.ArgumentParser(description="Uruchamia integracyjne testy systemu sklepu.")
    parser.add_argument("--skip-failure", action="store_true", help="Pomiń scenariusz zatrzymywania Krakowa.")
    args = parser.parse_args()
    settings = load_settings()
    GraphQLClient(settings.graphql_url).wait_until_ready()
    scenarios: list[Scenario] = [
        ("response_time", test_response_time.run),
        ("load", test_load.run),
        ("consistency", test_consistency.run),
        ("scalability", test_scalability.run),
    ]
    if not args.skip_failure:
        scenarios.insert(3, ("failure", test_failure.run))
    results = TestRunner(scenarios).run()
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "api": settings.graphql_url,
        "tests": [result.to_dict() for result in results],
    }
    report_path = ReportWriter(RESULTS_DIR).write(report)
    print(f"Raport HTML: {report_path}")
    return 0 if all(result.success for result in results) else 1


if __name__ == "__main__":
    sys.exit(main())
