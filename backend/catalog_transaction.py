"""Atomowe zapisy replikowanego katalogu z użyciem PostgreSQL 2PC.

PonyORM obsługuje transakcje pojedynczej bazy.  Katalog jest zapisywany do
dwóch niezależnych serwerów PostgreSQL, dlatego dla tych dwóch mutacji używamy
protokołu ``PREPARE TRANSACTION`` / ``COMMIT PREPARED``.  Decyzja o zatwierdzeniu
jest trwale zapisywana w Katowicach przed zakończeniem drugiej fazy; dzięki temu
pozostała przygotowana transakcja może zostać dokończona po awarii API.
"""

from __future__ import annotations

import os
import uuid
from contextlib import closing
from typing import Any

try:
    import psycopg2
except ModuleNotFoundError:  # Lokalny tryb SQLite nie wymaga sterownika PostgreSQL.
    psycopg2 = None


NODE_PREFIXES = ("KATOWICE", "KRAKOW")
GID_PREFIX = "distributed-store-catalog:"


class CatalogTransactionError(RuntimeError):
    """Błąd zapisu katalogu, który powinien zostać pokazany klientowi API."""


def enabled() -> bool:
    return os.getenv("DB_PROVIDER", "sqlite").lower() == "postgres"


def _connect(prefix: str, *, autocommit: bool = False):
    if psycopg2 is None:
        raise CatalogTransactionError(
            "Brakuje psycopg2; zainstaluj zależności z requirements.txt przed użyciem PostgreSQL."
        )
    connection = psycopg2.connect(
        host=os.getenv(f"{prefix}_DB_HOST", "localhost"),
        port=int(os.getenv(f"{prefix}_DB_PORT", "5432")),
        user=os.getenv(f"{prefix}_DB_USER", "sklep"),
        password=os.getenv(f"{prefix}_DB_PASSWORD", "sklep_password"),
        dbname=os.getenv(f"{prefix}_DB_NAME", f"sklep_{prefix.lower()}"),
    )
    connection.autocommit = autocommit
    return connection


def _ensure_decision_log() -> None:
    with closing(_connect("KATOWICE", autocommit=True)) as connection, connection.cursor() as cursor:
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS catalog_transaction_decisions (
                gid varchar(200) PRIMARY KEY,
                decision varchar(10) NOT NULL CHECK (decision IN ('commit')),
                created_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )


def _prepared_gids(prefix: str) -> set[str]:
    with closing(_connect(prefix, autocommit=True)) as connection, connection.cursor() as cursor:
        cursor.execute("SELECT gid FROM pg_prepared_xacts WHERE gid LIKE %s", (f"{GID_PREFIX}%",))
        return {row[0] for row in cursor.fetchall()}


def _finish_prepared(prefix: str, gid: str, action: str) -> None:
    with closing(_connect(prefix, autocommit=True)) as connection, connection.cursor() as cursor:
        cursor.execute(f"{action} PREPARED %s", (gid,))


def _commit_decision(gid: str) -> None:
    with closing(_connect("KATOWICE", autocommit=True)) as connection, connection.cursor() as cursor:
        cursor.execute(
            "INSERT INTO catalog_transaction_decisions (gid, decision) VALUES (%s, 'commit')",
            (gid,),
        )


def recover_prepared_transactions() -> None:
    """Dokańcza transakcje z decyzją commit i wycofuje bez podjętej decyzji.

    Funkcję można bezpiecznie uruchamiać wielokrotnie. Jest wywoływana przed
    każdym zapisem katalogu oraz przy starcie API. Jeśli któryś serwer jest
    niedostępny, wyjątek pozostawia przygotowaną transakcję nietkniętą do
    następnej próby odzyskania.
    """
    _ensure_decision_log()
    with closing(_connect("KATOWICE", autocommit=True)) as connection, connection.cursor() as cursor:
        cursor.execute("SELECT gid FROM catalog_transaction_decisions WHERE decision = 'commit'")
        committed = {row[0] for row in cursor.fetchall()}

    prepared_by_node = {prefix: _prepared_gids(prefix) for prefix in NODE_PREFIXES}
    all_prepared = set().union(*prepared_by_node.values())
    for gid in all_prepared:
        action = "COMMIT" if gid in committed else "ROLLBACK"
        for prefix in NODE_PREFIXES:
            if gid in prepared_by_node[prefix]:
                _finish_prepared(prefix, gid, action)


def _rollback_after_failed_prepare(gid: str, prepared_nodes: list[str]) -> None:
    for prefix in prepared_nodes:
        try:
            _finish_prepared(prefix, gid, "ROLLBACK")
        except psycopg2.Error:
            # Brak decyzji commit oznacza, że recovery bezpiecznie wycofa tę
            # transakcję, gdy dany węzeł odzyska połączenie.
            pass


def _run_two_phase(operation: str, callback) -> Any:
    recover_prepared_transactions()
    gid = f"{GID_PREFIX}{operation}:{uuid.uuid4()}"
    connections = {prefix: _connect(prefix) for prefix in NODE_PREFIXES}
    prepared_nodes: list[str] = []
    try:
        result = callback(connections)
        for prefix in NODE_PREFIXES:
            with connections[prefix].cursor() as cursor:
                cursor.execute("PREPARE TRANSACTION %s", (gid,))
            prepared_nodes.append(prefix)
        _commit_decision(gid)
    except Exception:
        _rollback_after_failed_prepare(gid, prepared_nodes)
        raise
    finally:
        for connection in connections.values():
            connection.close()

    try:
        for prefix in NODE_PREFIXES:
            _finish_prepared(prefix, gid, "COMMIT")
    except psycopg2.Error as exc:
        # Decyzja commit jest już trwała. Spróbuj dokończyć ją natychmiast;
        # jeśli węzeł nadal jest niedostępny, kolejna próba recovery ją wznowi.
        try:
            recover_prepared_transactions()
        except psycopg2.Error:
            pass
        remaining = set().union(*(_prepared_gids(prefix) for prefix in NODE_PREFIXES))
        if gid in remaining:
            raise CatalogTransactionError(
                "Decyzja zapisu katalogu została zapisana, ale oczekuje na odzyskanie węzła."
            ) from exc
    return result


def create_product(product: dict[str, Any]) -> dict[str, Any]:
    """Tworzy produkt w obu replikach jako jedną rozproszoną transakcję."""

    def insert(connections):
        created: dict[str, Any] | None = None
        for prefix in NODE_PREFIXES:
            with connections[prefix].cursor() as cursor:
                cursor.execute("SELECT 1 FROM products WHERE sku = %s", (product["sku"],))
                if cursor.fetchone() is not None:
                    raise CatalogTransactionError(f"Produkt o SKU {product['sku']} już istnieje")
                cursor.execute(
                    """
                    INSERT INTO products (sku, name, description, price, active)
                    VALUES (%s, %s, %s, %s, true)
                    RETURNING id, sku, name, description, price, active
                    """,
                    (
                        product["sku"], product["name"], product.get("description", ""), product["price"],
                    ),
                )
                row = cursor.fetchone()
                cursor.execute("INSERT INTO inventory (product, quantity) VALUES (%s, 0)", (row[0],))
                if created is None:
                    created = dict(zip(("id", "sku", "name", "description", "price", "active"), row))
        return created

    return _run_two_phase("create", insert)


def deactivate_product(sku: str) -> None:
    """Ustawia ``active=false`` w obu replikach jako jedną transakcję 2PC."""

    def deactivate(connections):
        for prefix in NODE_PREFIXES:
            with connections[prefix].cursor() as cursor:
                cursor.execute("UPDATE products SET active = false WHERE sku = %s", (sku,))
                if cursor.rowcount != 1:
                    raise CatalogTransactionError(f"Produkt {sku} nie istnieje w obu replikach katalogu")

    _run_two_phase("deactivate", deactivate)
