from __future__ import annotations

import uuid

from .common import GraphQLClient, inventory_query
from .config import load_settings
from .data_generator import TestDataRepository
from .test_catalog import CATALOG
from .test_models import Measurement, TestResult


def run() -> TestResult:
    settings = load_settings()
    client = GraphQLClient(settings.graphql_url)
    repository = TestDataRepository(settings)
    sku = f"CONS-{uuid.uuid4().hex[:10].upper()}"
    expected_quantity = 777
    repository.cleanup()
    try:
        created = client.execute(_create_product_mutation(sku))
        updated = client.execute(_update_inventory_mutation(sku, expected_quantity))
        katowice = _quantity_for_sku(client.execute(inventory_query("KATOWICE")), sku)
        krakow = _quantity_for_sku(client.execute(inventory_query("KRAKOW")), sku)
        success = not created.has_errors and not updated.has_errors and katowice == expected_quantity and krakow == 0
        measurement = Measurement(
            variant="replikacja katalogu i lokalny stan magazynowy",
            success=success,
            values={"SKU": sku, "Katowice": katowice, "Kraków": krakow},
            conclusion=("Katalog został zreplikowany, a stan magazynowy pozostał lokalny."
                        if success else "Replikacja katalogu lub separacja magazynów nie spełnia oczekiwań."),
        )
        return TestResult(definition=CATALOG["consistency"], measurements=[measurement])
    finally:
        repository.cleanup()


def _quantity_for_sku(response, sku: str) -> int | None:
    rows = response.data("inventory", []) or []
    matches = [row["quantity"] for row in rows if row.get("product", {}).get("sku") == sku]
    return matches[0] if len(matches) == 1 else None


def _create_product_mutation(sku: str) -> str:
    return f'''mutation {{ createProduct(product: {{ sku: "{sku}", name: "Produkt spójności", description: "Dane tymczasowe", price: 12.34 }}) {{ ok }} }}'''


def _update_inventory_mutation(sku: str, quantity: int) -> str:
    return f'''mutation {{ updateInventory(node: "KATOWICE", sku: "{sku}", quantity: {quantity}) {{ ok }} }}'''
