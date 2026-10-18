from __future__ import annotations

import json
import os
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any



ROOT = Path(__file__).resolve().parent.parent
GRAPHQL_URL = os.getenv("GRAPHQL_URL", "http://127.0.0.1:8000/graphql/")
COMPOSE_FILE = ROOT / "docker-compose.yml"


def graphql(query: str, variables: dict[str, Any] | None = None) -> tuple[dict[str, Any], float]:
    payload = json.dumps({"query": query, "variables": variables}).encode("utf-8")
    request = urllib.request.Request(
        GRAPHQL_URL,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    started = time.perf_counter()
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            body = response.read().decode("utf-8")
            status = response.status
    except urllib.error.HTTPError as error:
        body = error.read().decode("utf-8")
        status = error.code
    elapsed_ms = (time.perf_counter() - started) * 1000
    result = json.loads(body)
    result["_http_status"] = status
    result["_elapsed_ms"] = round(elapsed_ms, 3)
    return result, elapsed_ms


def query_products() -> str:
    return """
    {
      products {
        id
        sku
        name
        price
      }
    }
    """


def query_inventory(node: str | None = None) -> str:
    node_argument = f'(node: "{node}")' if node else ""
    return f"""
    {{
      inventory{node_argument} {{
        node
        quantity
        product {{ sku name }}
      }}
    }}
    """


def compose(*arguments: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    command = ["docker", "compose", "-f", str(COMPOSE_FILE), *arguments]
    return subprocess.run(
        command,
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=check,
    )


def wait_for_api(timeout_seconds: int = 60) -> None:
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        try:
            result, _ = graphql("{ products { id } }")
            if "data" in result:
                return
        except Exception:
            pass
        time.sleep(1)
    raise TimeoutError(f"API nie odpowiada pod {GRAPHQL_URL}")


def measure_repeated_queries(query: str, repetitions: int) -> tuple[float, float, int]:
    """Wykonuje to samo zapytanie i zwraca czas całkowity, średni oraz błędy."""
    started = time.perf_counter()
    elapsed_times = []
    errors = 0
    for _ in range(repetitions):
        result, elapsed_ms = graphql(query)
        elapsed_times.append(elapsed_ms)
        errors += int(bool(result.get("errors")))
    total_ms = (time.perf_counter() - started) * 1000
    average_ms = sum(elapsed_times) / len(elapsed_times)
    return total_ms, average_ms, errors

