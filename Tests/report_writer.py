from __future__ import annotations

import csv
import html
import json
from pathlib import Path
from typing import Any


class ReportWriter:
    def __init__(self, output_dir: Path):
        self.output_dir = output_dir

    def write(self, report: dict[str, Any]) -> Path:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self._write_json(report)
        self._write_csv(report)
        html_path = self.output_dir / "report.html"
        html_path.write_text(self._render_html(report), encoding="utf-8")
        return html_path

    def _write_json(self, report: dict[str, Any]) -> None:
        (self.output_dir / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    def _write_csv(self, report: dict[str, Any]) -> None:
        with (self.output_dir / "measurements.csv").open("w", newline="", encoding="utf-8") as file:
            writer = csv.writer(file)
            writer.writerow(["sekcja", "test", "wariant", "wartości", "status", "wniosek"])
            for test in report["tests"]:
                for measurement in test["measurements"]:
                    writer.writerow([
                        test["section"], test["name"], measurement["variant"],
                        json.dumps(measurement["values"], ensure_ascii=False),
                        "PASS" if measurement["success"] else "FAIL", measurement["conclusion"],
                    ])

    def _render_html(self, report: dict[str, Any]) -> str:
        tests = report["tests"]
        passed = sum(test["success"] for test in tests)
        status = "PASS" if passed == len(tests) else "FAIL"
        rows = "".join(self._summary_row(test) for test in tests)
        sections = "".join(self._test_section(test) for test in tests)
        return f"""<!doctype html>
<html lang="pl"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Raport testów — Distributed Store</title><style>{self._styles()}</style></head><body>
<main><header><p class="eyebrow">DISTRIBUTED STORE · RAPORT INTEGRACYJNY</p><h1>Raport testów</h1>
<p>Wygenerowano: <strong>{html.escape(report['generated_at'])}</strong> · API: <code>{html.escape(report['api'])}</code></p>
<div class="score {status.lower()}"><strong>{status}</strong><span>{passed}/{len(tests)} scenariuszy zakończonych powodzeniem</span></div></header>
<section><h2>Podsumowanie</h2><table><thead><tr><th>Sekcja</th><th>Scenariusz</th><th>Status</th><th>Czas</th></tr></thead><tbody>{rows}</tbody></table></section>
{sections}<footer>Źródła danych: <code>report.json</code> i <code>measurements.csv</code>.</footer></main></body></html>"""

    @staticmethod
    def _summary_row(test: dict[str, Any]) -> str:
        status = "PASS" if test["success"] else "FAIL"
        return f"<tr><td>{html.escape(test['section'])}</td><td>{html.escape(test['name'])}</td><td><span class='badge {status.lower()}'>{status}</span></td><td>{test['duration_ms']:.3f} ms</td></tr>"

    def _test_section(self, test: dict[str, Any]) -> str:
        measurements = "".join(self._measurement_row(measurement) for measurement in test["measurements"])
        error = f"<p class='error'><strong>Błąd techniczny:</strong> {html.escape(test['error'])}</p>" if test["error"] else ""
        return f"""<section class="scenario"><h2>{html.escape(test['section'])}. {html.escape(test['name'])}</h2>
<dl><dt>Cel</dt><dd>{html.escape(test['purpose'])}</dd><dt>Metoda</dt><dd>{html.escape(test['method'])}</dd><dt>Oczekiwany rezultat</dt><dd>{html.escape(test['expected'])}</dd></dl>
{error}<table><thead><tr><th>Wariant</th><th>Wyniki</th><th>Status</th><th>Wniosek</th></tr></thead><tbody>{measurements}</tbody></table></section>"""

    @staticmethod
    def _measurement_row(measurement: dict[str, Any]) -> str:
        values = "<br>".join(f"<strong>{html.escape(str(key))}:</strong> {html.escape(str(value))}" for key, value in measurement["values"].items()) or "—"
        status = "PASS" if measurement["success"] else "FAIL"
        return f"<tr><td>{html.escape(measurement['variant'])}</td><td>{values}</td><td><span class='badge {status.lower()}'>{status}</span></td><td>{html.escape(measurement['conclusion'] or '—')}</td></tr>"

    @staticmethod
    def _styles() -> str:
        return """*{box-sizing:border-box}body{margin:0;background:#f4f7fb;color:#172033;font:15px/1.55 system-ui,sans-serif}main{max-width:1120px;margin:auto;padding:44px 22px 70px}header{margin-bottom:36px}.eyebrow{font-size:12px;letter-spacing:.12em;color:#46648f;font-weight:700}h1{font-size:38px;margin:4px 0}h2{margin:0 0 16px}section{background:#fff;border:1px solid #dce3ef;border-radius:12px;padding:24px;margin:22px 0;box-shadow:0 3px 14px #1720330a}.score{display:flex;gap:14px;align-items:center;padding:14px 18px;border-radius:9px;width:max-content}.score.pass{background:#e8f7ee;color:#146c3a}.score.fail{background:#fff0f0;color:#a51d2d}.badge{font-size:12px;font-weight:700;padding:3px 8px;border-radius:99px}.badge.pass{background:#dff5e6;color:#146c3a}.badge.fail{background:#ffe0e2;color:#a51d2d}table{border-collapse:collapse;width:100%}th,td{text-align:left;padding:12px;border-bottom:1px solid #e5eaf2;vertical-align:top}th{background:#f8faff;font-size:12px;text-transform:uppercase;letter-spacing:.05em}dl{display:grid;grid-template-columns:180px 1fr;gap:8px;margin:0 0 20px}dt{font-weight:700}dd{margin:0}.error{color:#a51d2d}code{background:#edf1f7;padding:2px 5px;border-radius:4px}footer{color:#5c687d;margin-top:26px}@media(max-width:700px){main{padding:24px 12px}h1{font-size:30px}dl{grid-template-columns:1fr}table{font-size:13px}th,td{padding:8px}}"""
