from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True)
class TestDefinition:
    section: str
    name: str
    purpose: str
    method: str
    expected: str


@dataclass(frozen=True)
class Measurement:
    variant: str
    success: bool
    values: dict[str, Any] = field(default_factory=dict)
    conclusion: str = ""


@dataclass
class TestResult:
    definition: TestDefinition
    measurements: list[Measurement] = field(default_factory=list)
    duration_ms: float = 0.0
    error: str | None = None

    @property
    def success(self) -> bool:
        return self.error is None and bool(self.measurements) and all(
            measurement.success for measurement in self.measurements
        )

    @classmethod
    def failed(
        cls, definition: TestDefinition, error: Exception, duration_ms: float
    ) -> "TestResult":
        return cls(
            definition=definition,
            error=f"{type(error).__name__}: {error}",
            duration_ms=duration_ms,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            **asdict(self.definition),
            "success": self.success,
            "duration_ms": round(self.duration_ms, 3),
            "error": self.error,
            "measurements": [asdict(measurement) for measurement in self.measurements],
        }
