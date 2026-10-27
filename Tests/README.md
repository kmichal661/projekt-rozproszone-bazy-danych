# Testy integracyjne

Ten katalog zawiera scenariusze wymagane w rozdziale 6 projektu. Każdy scenariusz zwraca ten sam model wyniku, więc runner, raport HTML i pliki danych nie znają szczegółów konkretnego testu.

## Uruchomienie

```bash
docker compose up -d --build
python -m Tests.run_tests
```

Możesz uruchomić scenariusze w osobnym kontenerze, bez instalowania Pythona lokalnie:

```bash
docker compose --profile tests run --rm test_runner
```

Serwis `test_runner` należy do profilu `tests`, więc **nie uruchamia się** przy zwykłym `docker compose up`. Domyślnie pomija test awarii (`6.4`), ponieważ ten test zatrzymuje kontener Docker Compose i wymaga dostępu do Docker Daemon. Uruchom go z hosta przez `python -m Tests.run_tests`, jeśli chcesz wykonać pełny zestaw.

Bez testu awarii (nie zatrzymuje kontenera Krakowa):

```bash
python -m Tests.run_tests --skip-failure
```

## Raport

Po wykonaniu testów powstają:

- `Tests/results/report.html` — główny, czytelny raport;
- `Tests/results/report.json` — pełne dane dla narzędzi;
- `Tests/results/measurements.csv` — płaskie dane pomiarowe.

Raport HTML jest dostępny również z uruchomionej aplikacji pod adresem:

```text
http://localhost:8000/reports/tests
```

Jeśli raport nie istnieje, endpoint zwróci `404`; najpierw uruchom runner.

## Podział odpowiedzialności

- `config.py` — konfiguracja adresów i baz danych;
- `common.py` — adaptory GraphQL i Docker Compose;
- `data_generator.py` — tworzenie oraz usuwanie danych tymczasowych;
- `catalog_benchmark.py` — wspólny przebieg benchmarku katalogu;
- `test_*.py` — krótkie scenariusze biznesowe;
- `test_models.py` i `test_catalog.py` — modele wyniku oraz opisy scenariuszy;
- `run_tests.py` — uruchomienie scenariuszy i obsługa błędów;
- `report_writer.py` — zapis JSON/CSV i prezentacja HTML.

Dane tymczasowe używają SKU `PERF-*` i `CONS-*`; są czyszczone w bloku `finally` po każdym scenariuszu.
