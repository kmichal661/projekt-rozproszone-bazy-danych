from __future__ import annotations

import os
from dataclasses import dataclass


TEST_PREFIX = "PERF-"
TEMP_PREFIXES = ("PERF-", "CONS-")


@dataclass
class DatabaseConfig:
    host: str
    port: int
    database: str
    user: str
    password: str


def database_configs() -> dict[str, DatabaseConfig]:
    return {
        "KATOWICE": DatabaseConfig(
            os.getenv("TEST_KATOWICE_DB_HOST", "127.0.0.1"),
            int(os.getenv("TEST_KATOWICE_DB_PORT", "5433")),
            os.getenv("TEST_KATOWICE_DB_NAME", "sklep_katowice"),
            os.getenv("TEST_DB_USER", "sklep"),
            os.getenv("TEST_DB_PASSWORD", "sklep_password"),
        ),
        "KRAKOW": DatabaseConfig(
            os.getenv("TEST_KRAKOW_DB_HOST", "127.0.0.1"),
            int(os.getenv("TEST_KRAKOW_DB_PORT", "5434")),
            os.getenv("TEST_KRAKOW_DB_NAME", "sklep_krakow"),
            os.getenv("TEST_DB_USER", "sklep"),
            os.getenv("TEST_DB_PASSWORD", "sklep_password"),
        ),
    }


def _connect(config: DatabaseConfig):
    try:
        import psycopg2
    except ImportError as error:
        raise RuntimeError(
            "Testy wymagają psycopg2-binary. Uruchom: pip install -r requirements.txt"
        ) from error

    return psycopg2.connect(
        host=config.host,
        port=config.port,
        dbname=config.database,
        user=config.user,
        password=config.password,
    )


def cleanup_generated_data() -> None:
    for config in database_configs().values():
        with _connect(config) as connection:
            with connection.cursor() as cursor:
                for prefix in TEMP_PREFIXES:
                    cursor.execute(
                        """
                        DELETE FROM inventory
                        WHERE product IN (
                            SELECT id FROM products WHERE sku LIKE %s
                        )
                        """,
                        (f"{prefix}%",),
                    )
                    cursor.execute(
                        "DELETE FROM products WHERE sku LIKE %s",
                        (f"{prefix}%",),
                    )


def generate_products(count: int) -> int:
    """Tworzy count produktów testowych w obu węzłach."""
    try:
        import psycopg2
        from psycopg2.extras import execute_values
    except ImportError as error:
        raise RuntimeError(
            "Testy wymagają psycopg2-binary. Uruchom: pip install -r requirements.txt"
        ) from error

    cleanup_generated_data()
    rows = [
        (
            f"{TEST_PREFIX}{index:06d}",
            f"Produkt testowy {index}",
            "Produkt wygenerowany na potrzeby testów wydajności",
            round(10.0 + index / 100, 2),
            True,
        )
        for index in range(count)
    ]

    for node_name, config in database_configs().items():
        with _connect(config) as connection:
            with connection.cursor() as cursor:
                execute_values(
                    cursor,
                    """
                    INSERT INTO products (sku, name, description, price, active)
                    VALUES %s
                    """,
                    rows,
                    page_size=1000,
                )
                cursor.execute(
                    """
                    INSERT INTO inventory (product, quantity)
                    SELECT id, %s FROM products WHERE sku LIKE %s
                    """,
                    (100, f"{TEST_PREFIX}%"),
                )
        print(f"Wygenerowano {count} produktów w węźle {node_name}.")
    return count