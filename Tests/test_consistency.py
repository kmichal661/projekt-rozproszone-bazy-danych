from __future__ import annotations

import uuid

from .common import graphql, query_inventory
from .data_generator import cleanup_generated_data
from .test_catalog import DESCRIPTIONS
from .test_models import Measurement, TestResult


def run() -> TestResult:
    sku = f"CONS-{uuid.uuid4().hex[:10].upper()}"
    quantity = 777
    cleanup_generated_data()
    create_query = f"""
    mutation {{
      createProduct(product: {{
        sku: "{sku}"
        name: "Produkt spójności"
        description: "Produkt do testu spójności"
        price: 12.34
      }}) {{ ok message }}
    }}
    """
    create_result, _ = graphql(create_query)
    update_query = f"""
    mutation {{
      updateInventory(node: "KATOWICE", sku: "{sku}", quantity: {quantity}) {{
        ok
        inventory {{ node sku quantity }}
      }}
    }}
    """
    update_result, _ = graphql(update_query)
    katowice_result, _ = graphql(query_inventory("KATOWICE"))
    krakow_result, _ = graphql(query_inventory("KRAKOW"))

    katowice_values = [
        row["quantity"]
        for row in katowice_result.get("data", {}).get("inventory", [])
        if row.get("product", {}).get("sku") == sku
    ]
    krakow_values = [
        row["quantity"]
        for row in krakow_result.get("data", {}).get("inventory", [])
        if row.get("product", {}).get("sku") == sku
    ]
    cleanup_generated_data()

    success = (
        not create_result.get("errors")
        and not update_result.get("errors")
        and quantity in katowice_values
        and krakow_values == [0]
    )
    description = DESCRIPTIONS["consistency"]
    return TestResult(
        **description.__dict__,
        measurements=[
            Measurement(
                variant="produkt utworzony i zmieniony w Katowicach",
                success=success,
                values={
                    "SKU": sku,
                    "Katowice": katowice_values[0] if katowice_values else None,
                    "Kraków": krakow_values[0] if krakow_values else None,
                    "katalog w obu bazach": not create_result.get("errors"),
                },
                conclusion=(
                    "Katalog jest replikowany, a stan magazynowy pozostaje lokalny."
                    if success
                    else "Nie zachowano oczekiwanej spójności katalogu lub magazynu."
                ),
            )
        ],
    )