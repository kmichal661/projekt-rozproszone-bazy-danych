"""Jednorazowe, idempotentne zasilenie obu węzłów przykładowymi danymi."""

from __future__ import annotations

import sys
from pathlib import Path

from pony.orm import db_session

try:
    from .models import KATOWICE, KRAKOW, NODES
except ImportError:
    # Pozwala uruchomić plik bezpośrednio, np. przez F5.
    project_root = Path(__file__).resolve().parent.parent
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))
    from backend.models import KATOWICE, KRAKOW, NODES


PRODUCTS = [
    {
        "sku": "LAP-001",
        "name": "Laptop biznesowy",
        "description": "Laptop do pracy biurowej",
        "price": 3499.99,
        "katowice_quantity": 10,
        "krakow_quantity": 7,
    },
    {
        "sku": "MON-001",
        "name": "Monitor 27 cali",
        "description": "Monitor IPS 27 cali",
        "price": 1199.00,
        "katowice_quantity": 15,
        "krakow_quantity": 9,
    },
    {
        "sku": "KEY-001",
        "name": "Klawiatura mechaniczna",
        "description": "Klawiatura USB z podświetleniem",
        "price": 299.00,
        "katowice_quantity": 20,
        "krakow_quantity": 12,
    },
    {
        "sku": "MOU-001",
        "name": "Mysz bezprzewodowa",
        "description": "Mysz bezprzewodowa do pracy i domu",
        "price": 149.99,
        "katowice_quantity": 25,
        "krakow_quantity": 18,
    },
    {
        "sku": "HED-001",
        "name": "Słuchawki bezprzewodowe",
        "description": "Słuchawki Bluetooth z mikrofonem",
        "price": 399.00,
        "katowice_quantity": 8,
        "krakow_quantity": 11,
    },
    {
        "sku": "WEB-001",
        "name": "Kamera internetowa",
        "description": "Kamera Full HD do wideokonferencji",
        "price": 249.00,
        "katowice_quantity": 14,
        "krakow_quantity": 6,
    },
]


def seed_node(node, quantity_key: str) -> int:
    """Zapisuje katalog i magazyn dla jednego węzła."""
    created_products = 0
    created_inventory = 0

    with db_session:
        for product_data in PRODUCTS:
            product = node.Product.get(sku=product_data["sku"])
            if product is None:
                product = node.Product(
                    sku=product_data["sku"],
                    name=product_data["name"],
                    description=product_data["description"],
                    price=product_data["price"],
                    active=True,
                )
                created_products += 1
            else:
                product.name = product_data["name"]
                product.description = product_data["description"]
                product.price = product_data["price"]
                product.active = True

            inventory = node.Inventory.get(product=product)
            if inventory is None:
                node.Inventory(
                    product=product,
                    quantity=product_data[quantity_key],
                )
                created_inventory += 1
            else:
                inventory.quantity = product_data[quantity_key]

    return created_products + created_inventory


def main() -> None:
    total_changes = 0
    total_changes += seed_node(KATOWICE, "katowice_quantity")
    total_changes += seed_node(KRAKOW, "krakow_quantity")

    print(
        "Seed zakończony poprawnie. "
        f"Węzły: {', '.join(NODES)}. "
        f"Liczba utworzonych rekordów: {total_changes}."
    )


if __name__ == "__main__":
    main()