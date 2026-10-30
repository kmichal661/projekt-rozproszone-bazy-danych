from __future__ import annotations

import json
import subprocess
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any

from .config import TestSettings


@dataclass(frozen=True)
class ApiResponse:
    body: dict[str, Any]
    elapsed_ms: float

    @property
    def has_errors(self) -> bool:
        return bool(self.body.get("errors"))

    def data(self, key: str, default: Any = None) -> Any:
        return self.body.get("data", {}).get(key, default)


class GraphQLClient:
    def __init__(self, url: str, timeout_seconds: int = 60):
        self.url = url
        self.timeout_seconds = timeout_seconds

    def execute(self, query: str, variables: dict[str, Any] | None = None) -> ApiResponse:
        payload = json.dumps({"query": query, "variables": variables}).encode("utf-8")
        request = urllib.request.Request(
            self.url, data=payload, headers={"Content-Type": "application/json"}, method="POST"
        )
        started = time.perf_counter()
        try:
            with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                raw_body = response.read().decode("utf-8")
        except urllib.error.HTTPError as error:
            raw_body = error.read().decode("utf-8")
        return ApiResponse(json.loads(raw_body), (time.perf_counter() - started) * 1000)

    def wait_until_ready(self, timeout_seconds: int = 60) -> None:
        deadline = time.monotonic() + timeout_seconds
        while time.monotonic() < deadline:
            try:
                if not self.execute("{ products { id } }").has_errors:
                    return
            except (OSError, ValueError, urllib.error.URLError):
                pass
            time.sleep(1)
        raise TimeoutError(f"API nie odpowiada: {self.url}")

    def measure_repeated(self, query: str, repetitions: int) -> tuple[float, float, int]:
        started = time.perf_counter()
        responses = [self.execute(query) for _ in range(repetitions)]
        total_ms = (time.perf_counter() - started) * 1000
        errors = sum(response.has_errors for response in responses)
        average_ms = sum(response.elapsed_ms for response in responses) / repetitions
        return total_ms, average_ms, errors


class ComposeClient:
    def __init__(self, settings: TestSettings):
        self.settings = settings

    def run(self, *arguments: str) -> None:
        subprocess.run(
            ["docker", "compose", "-f", str(self.settings.compose_file), *arguments],
            cwd=self.settings.compose_file.parent,
            check=True,
            text=True,
            capture_output=True,
        )


def products_query() -> str:
    return "{ products { id sku name price } }"


def inventory_query(node: str | None = None) -> str:
    selector = f'(node: "{node}")' if node else ""
    return f"{{ inventory{selector} {{ node quantity product {{ sku name }} }} }}"
