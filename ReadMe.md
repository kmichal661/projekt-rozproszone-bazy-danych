# Rozproszony sklep internetowy

Aplikacja prezentuje sklep z katalogiem produktów replikowanym między dwoma oddziałami: **Katowice** i **Kraków**. Każdy oddział ma własny magazyn oraz własne zamówienia, dzięki czemu awaria jednego węzła nie blokuje odczytu danych drugiego.

## Stack technologiczny

- Python 3.11, Starlette i Uvicorn
- GraphQL: Graphene oraz GraphiQL
- PonyORM
- PostgreSQL 16 w Docker Compose
- SQLite przy uruchomieniu lokalnym

## Architektura i dane

| Dane | Katowice | Kraków | Zasada |
|---|---:|---:|---|
| Produkty | tak | tak | katalog jest replikowany |
| Stany magazynowe | tak | tak | stan jest lokalny dla oddziału |
| Zamówienia | tak | tak | zamówienie jest lokalne dla oddziału |

```mermaid
erDiagram
    PRODUCT ||--o{ INVENTORY : "ma stan"
    PRODUCT ||--o{ ORDER_ITEM : "występuje w"
    ORDER ||--|{ ORDER_ITEM : "zawiera"

    PRODUCT {
        int id PK
        string sku UK
        string name
        string description
        float price
        boolean active
    }
    INVENTORY {
        int id PK
        int product_id FK
        int quantity
    }
    ORDER {
        int id PK
        string customer_name
        string status
        float total
    }
    ORDER_ITEM {
        int id PK
        int order_id FK
        int product_id FK
        int quantity
        float unit_price
    }
```

Produkt usunięty przez `deleteProduct` nie jest fizycznie kasowany — otrzymuje `active=false` w obu replikach. Nieaktywny produkt nie może zostać dodany do nowego zamówienia.

## Usługi Docker Compose

| Usługa | Rola | Port hosta |
|---|---|---:|
| `api` | API Starlette i GraphQL | `8000` |
| `postgres_katowice` | baza oddziału Katowice | `5433` |
| `postgres_krakow` | baza oddziału Kraków | `5434` |
| `seed_database` | jednorazowe zasilenie danych | — |
| `test_runner` | ręcznie uruchamiane testy | — |

`test_runner` należy do profilu `tests`, więc zwykłe uruchomienie aplikacji go nie startuje.

## Szybki start przez Docker

Wymagane są Docker Desktop oraz Docker Compose.

```bash
docker compose up -d --build
```

Przy pierwszym uruchomieniu Compose:

1. uruchamia obie bazy PostgreSQL;
2. PonyORM tworzy tabele;
3. `seed_database` zapisuje dane demonstracyjne;
4. startuje API.

Sprawdź status:

```bash
docker compose ps
```

Adresy aplikacji:

| Zasób | Adres |
|---|---|
| GraphiQL / GraphQL | `http://localhost:8000/graphql` |
| Health check | `http://localhost:8000/health` |
| Raport testów HTML | `http://localhost:8000/reports/tests` |

Logi usług:

```bash
docker compose logs -f api
docker compose logs seed_database
```

Zatrzymanie usług bez usuwania danych:

```bash
docker compose down
```

Reset baz wraz z wolumenami — **usuwa wszystkie dane PostgreSQL**:

```bash
docker compose down -v
docker compose up -d --build
```

### Odzyskanie ręcznie usuniętej bazy PostgreSQL

Zmienne `POSTGRES_DB` tworzą bazę tylko przy inicjalizacji pustego wolumenu. Jeśli baza została usunięta w pgAdmin, wykonaj pełny reset wolumenów powyżej albo utwórz bazę ponownie w pgAdmin jako właściciel `sklep`:

```text
sklep_katowice  — serwer localhost:5433
sklep_krakow    — serwer localhost:5434
```

Następnie uruchom seed:

```bash
docker compose run --rm seed_database
```

## Seed danych

Seed jest idempotentny: tworzy brakujące rekordy, ale nie nadpisuje istniejącego stanu magazynowego ani flagi `active`.

Na świeżej bazie każdy oddział otrzymuje co najmniej 30 rekordów w tabelach:

- `products`,
- `inventory`,
- `orders`,
- `order_items`.

Ręczne uruchomienie seeda:

```bash
docker compose run --rm seed_database
```

## Lokalne uruchomienie bez Dockera

Lokalna aplikacja używa plików SQLite w `data/`.

```bash
pip install -r requirements.txt
python -m backend.seed_database
python backend/app.py
```

Lokalne API będzie dostępne pod `http://127.0.0.1:8000/graphql`.

## GraphQL — przykłady

Pełny zbiór gotowych do wklejenia zapytań i mutacji znajduje się w pliku [api_przyklady.md](api_przyklady.md).

Odczyt katalogu i stanów magazynowych:

```graphql
{
  products {
    sku
    name
    price
    active
  }
  inventory {
    node
    quantity
    product { sku name }
  }
}
```

Utworzenie produktu w obu replikach katalogu:

```graphql
mutation {
  createProduct(product: {
    sku: "LAP-999"
    name: "Laptop demonstracyjny"
    description: "Produkt testowy"
    price: 1999.99
  }) {
    ok
    message
  }
}
```

Utworzenie lokalnego zamówienia w Katowicach:

```graphql
mutation {
  createOrder(
    node: "KATOWICE"
    customerName: "Jan Kowalski"
    items: [{ sku: "LAP-001", quantity: 1 }]
  ) {
    ok
    order { id node total status }
  }
}
```

## Testy i raport HTML

Testy integracyjne obejmują czas odpowiedzi, obciążenie, spójność danych, awarię Krakowa oraz skalowalność.

### Z hosta — pełny zestaw

```bash
python -m Tests.run_tests
```

To uruchomienie zawiera test awarii, który tymczasowo zatrzymuje kontener `postgres_krakow`.

### W kontenerze — profil opcjonalny

```bash
docker compose --profile tests run --rm test_runner
```

Kontener `test_runner` nie jest uruchamiany domyślnie i wykonuje bezpieczny zestaw bez testu awarii (`6.4`).

Po zakończeniu testów powstają:

```text
Tests/results/report.html
Tests/results/report.json
Tests/results/measurements.csv
```

Raport HTML jest responsywny, zawiera podsumowanie PASS/FAIL, cel i metodę każdego scenariusza, wyniki pomiarów oraz wnioski. Jest dostępny w przeglądarce pod `http://localhost:8000/reports/tests`. Gdy raport nie został jeszcze wygenerowany, endpoint zwraca `404`.

Szczegóły organizacji testów znajdują się w [Tests/README.md](Tests/README.md).
