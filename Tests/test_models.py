from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class Measurement:
    """Jeden wynik pomiaru lub sprawdzenia."""

    variant: str
    success: bool
    values: dict[str, Any] = field(default_factory=dict)
    conclusion: str = ""


@dataclass
class TestResult:
    """Wynik pojedynczego testu wraz z opisem metodologii."""

    section: str
    name: str
    purpose: str
    method: str
    expected: str
    measurements: list[Measurement] = field(default_factory=list)
    duration_ms: float = 0.0
    error: str | None = None

    @property
    def success(self) -> bool:
        return self.error is None and bool(self.measurements) and all(
            measurement.success for measurement in self.measurements
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "section": self.section,
            "name": self.name,
            "purpose": self.purpose,
            "method": self.method,
            "expected": self.expected,
            "success": self.success,
            "duration_ms": round(self.duration_ms, 3),
            "error": self.error,
            "measurements": [
                {
                    "variant": measurement.variant,
                    "success": measurement.success,
                    "values": measurement.values,
                    "conclusion": measurement.conclusion,
                }
                for measurement in self.measurements
            ],
        }