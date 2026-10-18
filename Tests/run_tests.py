from __future__ import annotations

import argparse
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

try:
    from .common import wait_for_api
    from . import test_consistency, test_failure, test_load, test_response_time, test_scalability
except ImportError:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from Tests.common import wait_for_api
    from Tests import test_consistency, test_failure, test_load, test_response_time, test_scalability
from Tests.report_writer import ReportWriter
from Tests.test_models import TestResult


RESULTS_DIR = Path(__file__).resolve().parent / "results"


def main() -> int:
    parser = argparse.ArgumentParser(description="Testy systemu rozproszonego sklepu.")
    parser.add_argument(
        "--skip-failure",
        action="store_true",
        help="Pomija test zatrzymywania kontenera PostgreSQL Kraków.",
    )
    args = parser.parse_args()

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    wait_for_api()
    tests = [
        ("6.1", test_response_time.run),
        ("6.2", test_load.run),
        ("6.3", test_consistency.run),
    ]
    if not args.skip_failure:
        tests.append(("6.4", test_failure.run))
    tests.append(("6.5", test_scalability.run))

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "api": "http://127.0.0.1:8000/graphql/",
        "tests": [],
    }
    for section, test in tests:
        started = time.perf_counter()
        try:
            result = test()
            if not isinstance(result, TestResult):
                raise TypeError(f"Test {test.__module__} nie zwrócił TestResult")
            result.duration_ms = round((time.perf_counter() - started) * 1000, 3)
            report["tests"].append(result.to_dict())
        except Exception as error:
            report["tests"].append(
                {
                    "section": section,
                    "name": test.__module__,
                    "purpose": "Nie udało się uruchomić testu.",
                    "method": "-",
                    "expected": "Test powinien zakończyć się bez wyjątku.",
                    "success": False,
                    "duration_ms": round((time.perf_counter() - started) * 1000, 3),
                    "error": repr(error),
                    "measurements": [],
                }
            )
        current = report["tests"][-1]
        print(f"[{section}] {current.get('name')}: {'OK' if current.get('success') else 'BŁĄD'}")

    ReportWriter(RESULTS_DIR).write(report)
    print(f"Raport zapisano w: {RESULTS_DIR}")
    return 0 if all(test["success"] for test in report["tests"]) else 1


if __name__ == "__main__":
    sys.exit(main())