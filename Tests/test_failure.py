from __future__ import annotations

from .common import ComposeClient, GraphQLClient, inventory_query, products_query
from .config import load_settings
from .test_catalog import CATALOG
from .test_models import Measurement, TestResult


def run() -> TestResult:
    settings = load_settings()
    api = GraphQLClient(settings.graphql_url)
    compose = ComposeClient(settings)
    measurements: list[Measurement] = []
    krakow_stopped = False
    try:
        compose.run("stop", "postgres_krakow")
        krakow_stopped = True
        measurements.append(_availability_measurement(api, "podczas awarii Krakowa"))
    finally:
        if krakow_stopped:
            compose.run("start", "postgres_krakow")
            compose.run("run", "--rm", "seed_database")
            api.wait_until_ready()
            measurements.append(_availability_measurement(api, "po restarcie Krakowa"))
    return TestResult(definition=CATALOG["failure"], measurements=measurements)


def _availability_measurement(api: GraphQLClient, label: str) -> Measurement:
    catalog = api.execute(products_query())
    katowice = api.execute(inventory_query("KATOWICE"))
    both_nodes = api.execute(inventory_query())
    success = not catalog.has_errors and not katowice.has_errors
    errors = [error.get("message") for error in both_nodes.body.get("errors", [])]
    return Measurement(
        variant=label,
        success=success,
        values={
            "katalog dostępny": not catalog.has_errors,
            "Katowice dostępne": not katowice.has_errors,
            "oba węzły dostępne": not both_nodes.has_errors,
            "błędy obu węzłów": errors,
        },
        conclusion=("Katowice są dostępne mimo awarii drugiego węzła."
                    if success else "Awaria Krakowa uniemożliwiła odczyt danych Katowic."),
    )
