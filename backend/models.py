import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pony.orm import Database, Optional, PrimaryKey, Required, Set, db_session, select


@dataclass
class Node:
    name: str
    database: Database
    Product: Any
    Inventory: Any
    Order: Any
    OrderItem: Any


def _create_node(name: str, node_prefix: str, sqlite_path: str) -> Node:
    database = Database()

    class Product(database.Entity):
        _table_ = "products"
        id = PrimaryKey(int, auto=True)
        sku = Required(str, 50, unique=True)
        name = Required(str, 200)
        description = Optional(str, 1000, default="")
        price = Required(float)
        active = Required(bool, default=True)
        inventories = Set("Inventory", reverse="product")
        order_items = Set("OrderItem", reverse="product")

    class Inventory(database.Entity):
        _table_ = "inventory"
        id = PrimaryKey(int, auto=True)
        product = Required(Product, reverse="inventories")
        quantity = Required(int, default=0)

    class Order(database.Entity):
        _table_ = "orders"
        id = PrimaryKey(int, auto=True)
        customer_name = Required(str, 200)
        status = Required(str, 30, default="NEW")
        total = Required(float, default=0.0)
        items = Set("OrderItem", reverse="order")

    class OrderItem(database.Entity):
        _table_ = "order_items"
        id = PrimaryKey(int, auto=True)
        order = Required(Order, reverse="items")
        product = Required(Product, reverse="order_items")
        quantity = Required(int)
        unit_price = Required(float)

    provider = os.getenv("DB_PROVIDER", "sqlite").lower()
    if provider == "postgres":
        database.bind(
            provider="postgres",
            host=os.getenv(f"{node_prefix}_DB_HOST", "localhost"),
            port=int(os.getenv(f"{node_prefix}_DB_PORT", "5432")),
            user=os.getenv(f"{node_prefix}_DB_USER", "sklep"),
            password=os.getenv(f"{node_prefix}_DB_PASSWORD", "sklep_password"),
            database=os.getenv(f"{node_prefix}_DB_NAME", f"sklep_{name.lower()}"),
        )
    elif provider == "sqlite":
        project_root = Path(__file__).resolve().parent.parent
        local_path = project_root / sqlite_path
        local_path.parent.mkdir(parents=True, exist_ok=True)
        database.bind(provider="sqlite", filename=str(local_path), create_db=True)
    else:
        raise ValueError("DB_PROVIDER musi mieć wartość 'sqlite' albo 'postgres'")

    database.generate_mapping(create_tables=True)
    return Node(name, database, Product, Inventory, Order, OrderItem)


KATOWICE = _create_node(
    "KATOWICE",
    "KATOWICE",
    "data/katowice/katowice.db",
)
KRAKOW = _create_node(
    "KRAKOW",
    "KRAKOW",
    "data/krakow/krakow.db",
)
NODES = {KATOWICE.name: KATOWICE, KRAKOW.name: KRAKOW}


def get_node(node_name: str) -> Node:
    try:
        return NODES[node_name.upper()]
    except KeyError as exc:
        raise ValueError("Nieznany węzeł. Dostępne wartości: KATOWICE, KRAKOW") from exc


@dataclass
class ProductRecord:
    node: str
    entity_id: int

    def _entity(self):
        with db_session:
            return get_node(self.node).Product.get(id=self.entity_id)

    @property
    def id(self):
        return self.entity_id

    @property
    def sku(self):
        return self._entity().sku

    @property
    def name(self):
        return self._entity().name

    @property
    def description(self):
        return self._entity().description

    @property
    def price(self):
        return self._entity().price

    @property
    def active(self):
        return self._entity().active


@dataclass
class InventoryRecord:
    node: str
    entity_id: int

    @property
    def id(self):
        return self.entity_id

    def _entity(self):
        with db_session:
            return get_node(self.node).Inventory.get(id=self.entity_id)

    @property
    def product(self):
        entity = self._entity()
        return ProductRecord(self.node, entity.product.id)

    @property
    def quantity(self):
        return self._entity().quantity


@dataclass
class OrderRecord:
    node: str
    entity_id: int

    @property
    def id(self):
        return self.entity_id

    def _entity(self):
        with db_session:
            return get_node(self.node).Order.get(id=self.entity_id)

    @property
    def customer_name(self):
        return self._entity().customer_name

    @property
    def status(self):
        return self._entity().status

    @property
    def total(self):
        return self._entity().total

    @property
    def items(self):
        with db_session:
            order = self._entity()
            return [OrderItemRecord(self.node, item.id) for item in order.items]


@dataclass
class OrderItemRecord:
    node: str
    entity_id: int

    def _entity(self):
        with db_session:
            return get_node(self.node).OrderItem.get(id=self.entity_id)

    @property
    def id(self):
        return self.entity_id

    @property
    def product(self):
        entity = self._entity()
        return ProductRecord(self.node, entity.product.id)

    @property
    def quantity(self):
        return self._entity().quantity

    @property
    def unit_price(self):
        return self._entity().unit_price


def list_products():
    with db_session:
        products = select(product for product in KATOWICE.Product if product.active)
        return [ProductRecord(KATOWICE.name, product.id) for product in products]


def list_inventory(node_name: str | None = None):
    nodes = [get_node(node_name)] if node_name else list(NODES.values())
    result = []
    for node in nodes:
        with db_session:
            inventories = select(inventory for inventory in node.Inventory)
            result.extend(InventoryRecord(node.name, inventory.id) for inventory in inventories)
    return result


def list_orders(node_name: str | None = None):
    nodes = [get_node(node_name)] if node_name else list(NODES.values())
    result = []
    for node in nodes:
        with db_session:
            orders = select(order for order in node.Order)
            result.extend(OrderRecord(node.name, order.id) for order in orders)
    return result