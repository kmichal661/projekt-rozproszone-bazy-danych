"""Jednorazowe, idempotentne zasilenie obu węzłów przykładowymi danymi."""

from __future__ import annotations

import sys
from pathlib import Path

from pony.orm import db_session

try:
    from .models import KATOWICE, KRAKOW, NODES
except ImportError:
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


# Keep the six named examples above and add enough deterministic examples to
# make a fresh database useful for demos and load tests.  The same SKU is
# created in both catalog replicas, while inventory remains node-local.
PRODUCTS.extend(
    {
        "sku": f"SEED-{index:03d}",
        "name": f"Produkt demonstracyjny {index:03d}",
        "description": "Produkt wygenerowany przez seed",
        "price": round(49.99 + index * 7.5, 2),
        "katowice_quantity": 20 + index,
        "krakow_quantity": 15 + index,
    }
    for index in range(1, 25)
)

MIN_SEED_ROWS = 30


def seed_orders(node) -> tuple[int, int]:
    """Add deterministic local orders until both order tables have 30 rows.

    Existing orders are never edited or deleted.  Each order added by this
    function has one item, so a fresh node receives 30 orders and 30 items.
    """
    orders = list(node.Order.select())
    created_orders = 0
    created_order_items = 0
    order_items_count = sum(len(order.items) for order in orders)
    next_number = len(orders) + 1

    while len(orders) < MIN_SEED_ROWS or order_items_count < MIN_SEED_ROWS:
        product_data = PRODUCTS[(next_number - 1) % len(PRODUCTS)]
        product = node.Product.get(sku=product_data["sku"])
        order = node.Order(
            customer_name=f"Seed klient {node.name} {next_number:03d}",
            status="NEW",
            total=product.price,
        )
        node.OrderItem(
            order=order,
            product=product,
            quantity=1,
            unit_price=product.price,
        )
        orders.append(order)
        created_orders += 1
        created_order_items += 1
        order_items_count += 1
        next_number += 1

    return created_orders, created_order_items


def seed_node(node, quantity_key: str) -> int:
    """Zapisuje katalog i magazyn dla jednego węzła."""
    created_products = 0
    created_inventory = 0
    created_orders = 0
    created_order_items = 0

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

            inventory = node.Inventory.get(product=product)
            if inventory is None:
                node.Inventory(
                    product=product,
                    quantity=product_data[quantity_key],
                )
                created_inventory += 1

        # Seeding may be run again after a restart. It only supplies missing
        # demo rows, so it never overwrites a deactivated product or stock.
        created_orders, created_order_items = seed_orders(node)

    return created_products + created_inventory + created_orders + created_order_items


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
