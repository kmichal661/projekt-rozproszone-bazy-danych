from __future__ import annotations

from .common import compose, graphql, query_inventory, query_products, wait_for_api
from .test_catalog import DESCRIPTIONS
from .test_models import Measurement, TestResult


def run() -> TestResult:
    measurements: list[Measurement] = []
    stopped = False
    try:
        compose("stop", "postgres_krakow")
        stopped = True
        measurements.append(_check("po wyłączeniu węzła Kraków"))
    finally:
        if stopped:
            compose("start", "postgres_krakow")
            compose("run", "--rm", "seed_database")
            wait_for_api()
            measurements.append(_check("po ponownym uruchomieniu węzła Kraków"))
    description = DESCRIPTIONS["failure"]
    return TestResult(**description.__dict__, measurements=measurements)


def _check(label: str) -> dict:
    products, _ = graphql(query_products())
    katowice, _ = graphql(query_inventory("KATOWICE"))
    all_inventory, _ = graphql(query_inventory())
    products_available = not products.get("errors")
    katowice_available = not katowice.get("errors")
    all_nodes_available = not all_inventory.get("errors")
    return Measurement(
        variant=label,
        success=products_available and katowice_available,
        values={
            "katalog dostępny": products_available,
            "Katowice dostępne": katowice_available,
            "zapytanie do obu węzłów": all_nodes_available,
            "błędy zapytania obu węzłów": [
                error.get("message") for error in all_inventory.get("errors", [])
            ],
        },
        conclusion=(
            "Dane Katowic są dostępne; po restarcie można ponownie odczytać oba węzły."
            if products_available and katowice_available
            else "Aplikacja nie zapewniła dostępności danych lokalnego węzła."
        ),
    )