# Testy systemu rozproszonego

Folder zawiera testy wymagane w punkcie 6 projektu.

## Uruchomienie

Najpierw uruchom aplikację i bazy:

```bash
docker compose up -d --build
```

Zainstaluj zależności lokalnego środowiska:

```bash
pip install -r requirements.txt
```

Uruchom cały zestaw testów:

```bash
python -m Tests.run_tests
```

Można też uruchomić skrypt bezpośrednio:

```bash
python Tests/run_tests.py
```

Jeżeli nie chcesz zatrzymywać kontenera PostgreSQL Kraków:

```bash
python -m Tests.run_tests --skip-failure
```

## Zakres testów

- `test_response_time.py` – czas odpowiedzi dla 100, 1 000 i 10 000 produktów.
- `test_load.py` – wykonanie 1, 10 i 100 zapytań GraphQL.
- `test_consistency.py` – aktualizacja magazynu w Katowicach oraz sprawdzenie katalogu i magazynu w Krakowie.
- `test_failure.py` – zatrzymanie PostgreSQL Kraków, sprawdzenie działania Katowic, ponowne uruchomienie węzła i odtworzenie danych.
- `test_scalability.py` – pomiar wpływu liczby rekordów na czas odpowiedzi.

## Organizacja kodu

Kod testów jest podzielony według odpowiedzialności:

- `test_models.py` – wspólne modele `Measurement` i `TestResult`,
- `test_catalog.py` – opisy celu, metody i oczekiwanego wyniku testów,
- `common.py` – wspólny klient GraphQL, pomiary powtarzalnych zapytań i obsługa Docker Compose,
- `data_generator.py` – generowanie i usuwanie danych testowych,
- `report_writer.py` – zapis raportu Markdown, JSON i CSV,
- `test_*.py` – pojedyncze scenariusze testowe,
- `run_tests.py` – orkiestracja uruchomienia bez logiki szczegółowych testów.

Każdy test zwraca ujednolicony `TestResult`. Dzięki temu raport ma ten sam format dla wszystkich sekcji, a logika pomiarów i raportowania nie jest powielana.

Dane wydajnościowe mają SKU zaczynające się od `PERF-` i są usuwane po każdym teście. Test spójności używa tymczasowego SKU zaczynającego się od `CONS-`.

## Raporty

Po zakończeniu testów powstają:

```text
Tests/results/report.md
Tests/results/report.json
Tests/results/measurements.csv
```

Raport Markdown nadaje się bezpośrednio do wklejenia do dokumentacji projektu. Dla każdego testu zawiera cel, metodę, oczekiwany rezultat, tabelę wariantów, konkretne pomiary, status i wniosek. Raport JSON zawiera pełne dane pomiarowe, a CSV można wykorzystać do przygotowania wykresu.

## Zmienne środowiskowe

Domyślne wartości odpowiadają `docker-compose.yml`:

```text
GRAPHQL_URL=http://127.0.0.1:8000/graphql/
TEST_KATOWICE_DB_HOST=127.0.0.1
TEST_KATOWICE_DB_PORT=5433
TEST_KRAKOW_DB_HOST=127.0.0.1
TEST_KRAKOW_DB_PORT=5434
TEST_DB_NAME=...
TEST_DB_USER=sklep
TEST_DB_PASSWORD=sklep_password
```

Test awarii zmienia stan kontenera `postgres_krakow`, dlatego należy uruchamiać go z uprawnieniami pozwalającymi na wykonanie poleceń Docker Compose.