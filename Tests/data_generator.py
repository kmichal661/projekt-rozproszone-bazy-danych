"""PostgreSQL test-data lifecycle, isolated by SKU prefixes."""

from __future__ import annotations

from contextlib import closing

from .config import DatabaseSettings, TestSettings


PERFORMANCE_PREFIX = "PERF-"
TEMPORARY_PREFIXES = ("PERF-", "CONS-")


class TestDataRepository:
    def __init__(self, settings: TestSettings):
        self.settings = settings

    def cleanup(self) -> None:
        for database in self.settings.databases.values():
            with closing(self._connect(database)) as connection:
                with connection, connection.cursor() as cursor:
                    for prefix in TEMPORARY_PREFIXES:
                        cursor.execute(
                            "DELETE FROM inventory WHERE product IN "
                            "(SELECT id FROM products WHERE sku LIKE %s)",
                            (f"{prefix}%",),
                        )
                        cursor.execute("DELETE FROM products WHERE sku LIKE %s", (f"{prefix}%",))

    def create_performance_products(self, count: int) -> None:
        rows = [
            (
                f"{PERFORMANCE_PREFIX}{index:06d}",
                f"Produkt testowy {index}",
                "Produkt wygenerowany na potrzeby testu wydajności",
                round(10.0 + index / 100, 2),
                True,
            )
            for index in range(count)
        ]
        for database in self.settings.databases.values():
            with closing(self._connect(database)) as connection:
                with connection, connection.cursor() as cursor:
                    self._insert_products(cursor, rows)
                    cursor.execute(
                        "INSERT INTO inventory (product, quantity) "
                        "SELECT id, %s FROM products WHERE sku LIKE %s",
                        (100, f"{PERFORMANCE_PREFIX}%"),
                    )

    @staticmethod
    def _connect(settings: DatabaseSettings):
        try:
            import psycopg2
        except ImportError as error:
            raise RuntimeError("Brakuje psycopg2-binary. Uruchom: pip install -r requirements.txt") from error
        return psycopg2.connect(
            host=settings.host, port=settings.port, dbname=settings.name,
            user=settings.user, password=settings.password,
        )

    @staticmethod
    def _insert_products(cursor, rows) -> None:
        try:
            from psycopg2.extras import execute_values
        except ImportError as error:
            raise RuntimeError("Brakuje psycopg2-binary. Uruchom: pip install -r requirements.txt") from error
        execute_values(
            cursor,
            "INSERT INTO products (sku, name, description, price, active) VALUES %s",
            rows,
            page_size=1000,
        )
