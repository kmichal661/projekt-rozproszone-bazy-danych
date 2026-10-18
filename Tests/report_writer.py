from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from .test_models import TestResult


class ReportWriter:
    """Zapisuje jeden wynik testów w trzech formatach."""

    def __init__(self, output_dir: Path):
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def write(self, report: dict[str, Any]) -> None:
        self._write_json(report)
        self._write_csv(report)
        self._write_markdown(report)

    def _write_json(self, report: dict[str, Any]) -> None:
        (self.output_dir / "report.json").write_text(
            json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    def _write_csv(self, report: dict[str, Any]) -> None:
        with (self.output_dir / "measurements.csv").open(
            "w", newline="", encoding="utf-8"
        ) as file:
            writer = csv.writer(file)
            writer.writerow(["sekcja", "test", "wariant", "wartości", "status"])
            for test in report["tests"]:
                for measurement in test["measurements"]:
                    writer.writerow(
                        [
                            test["section"],
                            test["name"],
                            measurement["variant"],
                            json.dumps(measurement["values"], ensure_ascii=False),
                            "OK" if measurement["success"] else "BŁĄD",
                        ]
                    )

    def _write_markdown(self, report: dict[str, Any]) -> None:
        tests = report["tests"]
        successful = sum(test["success"] for test in tests)
        lines = [
            "# Raport testów systemu rozproszonego",
            "",
            f"**Data wykonania:** `{report['generated_at']}`  ",
            f"**API:** `{report['api']}`  ",
            f"**Wynik ogólny:** `{successful}/{len(tests)} testów zakończonych poprawnie`",
            "",
            "## 1. Cel testów",
            "",
            "Testy weryfikują czas odpowiedzi, obciążenie, spójność danych, zachowanie podczas awarii oraz skalowalność.",
            "Dane testowe są usuwane po zakończeniu testów, dlatego nie powinny zmieniać danych demonstracyjnych.",
            "",
            "## 2. Podsumowanie",
            "",
            "| Sekcja | Test | Status | Czas wykonania |",
            "|---|---|---|---:|",
        ]
        for test in tests:
            status = "OK" if test["success"] else "BŁĄD"
            lines.append(
                f"| {test['section']} | {test['name']} | {status} | {test['duration_ms']} ms |"
            )

        for index, test in enumerate(tests, start=3):
            lines.extend(
                [
                    "",
                    f"## {index}. {test['section']} – {test['name']}",
                    "",
                    f"**Cel:** {test['purpose']}",
                    "",
                    f"**Metoda:** {test['method']}",
                    "",
                    f"**Oczekiwany rezultat:** {test['expected']}",
                    "",
                    "### Wyniki",
                    "",
                    "| Wariant | Pomiary | Status | Wniosek |",
                    "|---|---|---|---|",
                ]
            )
            for measurement in test["measurements"]:
                values = "; ".join(
                    f"{key}: {value}" for key, value in measurement["values"].items()
                ) or "-"
                status = "OK" if measurement["success"] else "BŁĄD"
                lines.append(
                    f"| {measurement['variant']} | {values} | {status} | {measurement['conclusion'] or '-'} |"
                )
            if test.get("error"):
                lines.extend(["", f"**Błąd techniczny:** `{test['error']}`"])

        lines.extend(
            [
                "",
                "## Wnioski końcowe",
                "",
                self._final_conclusion(tests),
                "",
                "## Pliki pomocnicze",
                "",
                "- `report.json` – pełne dane maszynowe,",
                "- `measurements.csv` – dane do wykresów,",
                "- `report.md` – raport do dokumentacji projektu.",
                "",
            ]
        )
        (self.output_dir / "report.md").write_text("\n".join(lines), encoding="utf-8")

    @staticmethod
    def _final_conclusion(tests: list[dict[str, Any]]) -> str:
        if all(test["success"] for test in tests):
            return "Wszystkie wykonane testy zakończyły się poprawnie. System odpowiada, obsługuje zwiększone obciążenie, zachowuje założoną spójność danych i odzyskuje działanie po ponownym uruchomieniu węzła Kraków."
        failed = [test["name"] for test in tests if not test["success"]]
        return f"Nie wszystkie testy zakończyły się poprawnie. Należy przeanalizować wyniki sekcji: {', '.join(failed)}."