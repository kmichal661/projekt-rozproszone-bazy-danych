# Rozproszony sklep internetowy z oddziałami – analiza i projekt

Przedmiot: Rozproszone bazy danych – projekt

## 1. Opis problemu i architektury systemu

### 1.1. Jaki problem rozwiązuje system

System jest prostym sklepem internetowym z dwoma oddziałami: **Katowice** i **Kraków**. Umożliwia prowadzenie wspólnego katalogu produktów, śledzenie stanów magazynowych w każdym oddziale oraz składanie zamówień realizowanych przez wybrany oddział. Celem projektu jest pokazanie, jak dane mogą być rozmieszczone pomiędzy niezależnymi węzłami bazy danych i jak system zachowuje się przy takim podziale.

Problem sprowadza się do pogodzenia dwóch wymagań: produkt powinien być widoczny w obu oddziałach (katalog jest wspólny), a zmiana liczby sztuk lub złożenie zamówienia powinny dotyczyć tylko wybranego oddziału.

### 1.2. Użytkownicy aplikacji

- **Klient** – przegląda katalog produktów, sprawdza dostępność w oddziałach i składa zamówienie.
- **Pracownik oddziału** – aktualizuje stany magazynowe, przegląda zamówienia swojego oddziału, dodaje nowe produkty do katalogu i wycofuje produkty ze sprzedaży.

Role mają charakter logiczny: aplikacja nie ma logowania ani kontroli uprawnień, więc każda operacja jest dostępna dla każdego, kto ma dostęp do API.

### 1.3. Przechowywane dane

- katalog produktów (SKU, nazwa, opis, cena, status aktywności),
- stany magazynowe produktów w poszczególnych oddziałach,
- zamówienia (imię i nazwisko klienta, status, wartość) wraz z pozycjami zamówienia (produkt, liczba sztuk, cena jednostkowa).

### 1.4. Uzasadnienie rozproszonej bazy danych

Każdy oddział najczęściej pracuje na własnych stanach magazynowych i własnych zamówieniach, więc przechowywanie ich lokalnie skraca czas dostępu i pozwala oddziałom działać niezależnie. Awaria jednego węzła nie wyłącza lokalnych operacji drugiego oddziału (zamówień i stanów magazynowych). Jednocześnie katalog produktów i ceny muszą być jednakowe w całej sieci sklepów, dlatego są utrzymywane w obu węzłach. Takie połączenie podziału i powielania danych jest typowym przypadkiem użycia rozproszonej bazy danych.

### 1.5. Elementy systemu działające w różnych lokalizacjach

- baza danych oddziału Katowice (węzeł 1),
- baza danych oddziału Kraków (węzeł 2),
- warstwa aplikacji (API), która komunikuje się z obydwoma węzłami i potrafi łączyć dane z różnych węzłów w jednej odpowiedzi.

### 1.6. Architektura systemu

System składa się z trzech głównych usług uruchamianych w Docker Compose:

| Usługa              | Rola                                                                                                                                                              |
| ------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `api`               | Backend (Python, Starlette, Graphene) udostępniający endpoint GraphQL pod adresem `/graphql`, endpoint `/health` oraz raport testów pod adresem `/reports/tests`. |
| `postgres_katowice` | Instancja PostgreSQL 16 oddziału Katowice (baza `sklep_katowice`).                                                                                                |
| `postgres_krakow`   | Instancja PostgreSQL 16 oddziału Kraków (baza `sklep_krakow`).                                                                                                    |
| `seed_database`     | Usługa jednorazowa, idempotentnie zasilająca oba węzły danymi demonstracyjnymi (dodaje tylko brakujące rekordy).                                                  |
| `test_runner`       | Opcjonalny kontener (profil `tests`) uruchamiający zestaw testów bez scenariusza awarii.                                                                          |

Dostęp do baz zrealizowano przez mapowanie obiektowo-relacyjne (PonyORM). Aplikacja przechowuje po jednym połączeniu do każdego węzła i wybiera węzeł na podstawie parametru oddziału lub wykonuje operację na obu węzłach (np. dodanie produktu do katalogu). Dla wygody pracy lokalnej możliwe jest również uruchomienie na dwóch bazach SQLite.

Technologie: Python 3.11, Starlette, Uvicorn, Graphene (GraphQL), PonyORM, PostgreSQL 16, Docker Compose.

### 1.7. Rola serwera głównego i zachowanie przy awarii

Serwer główny to usługa `api`. Jest wspólnym punktem wejścia dla klientów i **koordynatorem dostępu do danych**, a nie centralną bazą danych: nie przechowuje katalogu, stanów magazynowych ani zamówień. Przyjmuje żądania GraphQL, waliduje je, wybiera węzeł wskazany parametrem `node` dla operacji lokalnych oraz koordynuje zapis katalogu do obu replik. Dane biznesowe są trwale przechowywane wyłącznie w niezależnych bazach `postgres_katowice` i `postgres_krakow`.

| Sytuacja awaryjna | Zachowanie systemu |
| --- | --- |
| Niedostępny Kraków | Odczyt katalogu (z Katowic), `inventory(node: "KATOWICE")` oraz zamówienia w Katowicach pozostają dostępne. Operacje dotyczące Krakowa i odczyty bez parametru `node`, wymagające obu węzłów, zwracają błąd. |
| Niedostępne Katowice | API działa, lecz odczyt `products` jest niedostępny, ponieważ katalog jest obecnie odczytywany z repliki Katowic. Lokalne operacje w Krakowie mogą działać, jeśli nie wymagają zapisu katalogu. |
| Niedostępny dowolny węzeł podczas zmiany katalogu | `createProduct` i `deleteProduct` są odrzucane; system nie zapisuje zmiany tylko w dostępnym węźle i nie kolejkuje jej do późniejszego wykonania. |
| Niedostępne `api` | Klient nie ma dostępu do GraphQL, choć dane w obu bazach pozostają zachowane. Po ponownym uruchomieniu usługi API dostęp wraca. |

Po odzyskaniu połączenia aplikacja ponownie korzysta z uruchomionego węzła, a dane zapisane w jego wolumenie PostgreSQL pozostają dostępne. Nie ma automatycznej kolejki ani procesu uzgadniania katalogu; po awarii występującej w trakcie zatwierdzania zapisu należy porównać repliki. Szczegółowy przebieg scenariusza awarii i jego wyniki przedstawia sekcja 10.4.

## 2. Wymagania

### 2.1. Wymagania funkcjonalne

| Nr  | Wymaganie                                                                                                                                                                                                                                                                    |
| --- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| F1  | Przeglądanie katalogu aktywnych produktów (SKU, nazwa, opis, cena).                                                                                                                                                                                                          |
| F2  | Sprawdzanie stanów magazynowych w wybranym oddziale lub we wszystkich oddziałach jednocześnie.                                                                                                                                                                               |
| F3  | Dodawanie nowego produktu do katalogu; system najpierw sprawdza, czy oba węzły są dostępne i czy SKU jeszcze nie istnieje, a następnie zapisuje produkt wraz z zerowym stanem magazynowym w obu węzłach; przy niedostępnym węźle zwraca błąd i nie zmienia żadnego katalogu. |
| F4  | Wycofanie produktu ze sprzedaży (oznaczenie jako nieaktywny w obu węzłach); produkt znika z katalogu i nie można go zamówić, ale nadal jest widoczny w stanach magazynowych. Przy niedostępnym węźle operacja kończy się błędem bez zmian w katalogach.                      |
| F5  | Aktualizacja stanu magazynowego produktu w wybranym oddziale.                                                                                                                                                                                                                |
| F6  | Składanie zamówienia w wybranym oddziale z wieloma pozycjami; system sprawdza, czy ilość jest dodatnia, produkt istnieje i jest aktywny oraz czy oddział ma wystarczający stan, a następnie wylicza wartość zamówienia i zmniejsza stan magazynowy.                          |
| F7  | Przeglądanie zamówień wybranego oddziału lub wszystkich oddziałów wraz z pozycjami.                                                                                                                                                                                          |
| F8  | Zasilenie obu baz danymi demonstracyjnymi (seed); powtórne uruchomienie dodaje tylko brakujące rekordy i nie nadpisuje stanów magazynowych ani flag aktywności.                                                                                                              |
| F9  | Zestaw testów generuje raport w formatach HTML, JSON i CSV; raport HTML jest dostępny pod adresem `/reports/tests`.                                                                                                                                                          |

### 2.2. Wymagania niefunkcjonalne

| Nr  | Wymaganie                                                                                                                                                                                                                                                                                                                                                                                                            |
| --- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| N1  | **Czas odpowiedzi** – zapytania odczytu na danych demonstracyjnych (około 60 rekordów) trwają około 70 ms, a zapis zamówienia kilka milisekund; czas rośnie liniowo z liczbą rekordów (około 1,5 s dla 1 000 rekordów na węzeł, sekcja 10.1).                                                                                                                                                                        |
| N2  | **Dostępność** – awaria jednego węzła nie uniemożliwia pracy z lokalnymi danymi drugiego oddziału (zamówienia i stany magazynowe), natomiast zapytania obejmujące oba węzły zwracają błąd (sekcja 10.4).                                                                                                                                                                                                             |
| N3  | **Odporność na awarie** – po ponownym uruchomieniu węzła system wraca do poprawnego działania bez utraty danych (dane są na trwałych wolumenach), a dodanie lub wycofanie produktu przy niedostępnym węźle kończy się błędem bez zmian w katalogach (sekcja 10.4).                                                                                                                                                   |
| N4  | **Spójność danych** – katalog produktów jest zapisywany do obu węzłów w jednym żądaniu, po sprawdzeniu dostępności obu węzłów; nie jest to jednak pełna transakcja rozproszona (awaria w chwili zatwierdzania mogłaby zostawić zapis częściowy), a zmiany wykonane poza aplikacją nie są synchronizowane (sekcje 10.3 i 10.4); stany magazynowe i zamówienia są spójne w obrębie swojego węzła (transakcje lokalne). |
| N5  | **Bezpieczeństwo dostępu** – dane dostępowe do baz aplikacja pobiera ze zmiennych środowiskowych, a użytkownik korzysta z danych przez API GraphQL. System nie ma logowania ani autoryzacji, a porty baz (5433 i 5434) są w konfiguracji demonstracyjnej wystawione na hosta, więc zabezpieczenie dostępu jest ograniczone.                                                                                          |
| N6  | **Skalowalność** – czas odpowiedzi rośnie liniowo z liczbą danych i operacji (sekcja 10); dodanie kolejnego oddziału wymaga zmian w kodzie, bo węzły Katowice i Kraków są zdefiniowane na stałe w pliku models.py.                                                                                                                                                                                                   |
| N7  | **Przenośność** – całość środowiska jest skonfigurowana do uruchomienia jednym poleceniem `docker compose up --build` albo lokalnie na dwóch plikach SQLite.                                                                                                                                                                                                                                                         |
| N8  | **Obserwowalność** – dostępne są endpoint `/health`, logi Docker Compose i raport testów w HTML (`/reports/tests`).                                                                                                                                                                                                                                                                                                  |
| N9  | **Powtarzalność** – seed jest idempotentny (dodaje brakujące rekordy, nie nadpisuje stanów magazynowych ani flag `active`), a dane testowe `PERF-*` i `CONS-*` są usuwane po teście.                                                                                                                                                                                                                                 |

## 3. Diagram przypadków użycia UML

### 3.1. Aktorzy i przypadki użycia

| Aktor              | Przypadki użycia                                                                                                                                                                                            |
| ------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Klient             | Przeglądanie katalogu produktów (UC1); Sprawdzenie dostępności produktu w oddziałach (UC2); Złożenie zamówienia (UC3)                                                                                       |
| Pracownik oddziału | Sprawdzenie dostępności produktu w oddziałach (UC2); Aktualizacja stanu magazynowego (UC4); Przeglądanie zamówień oddziału (UC5); Dodanie produktu do katalogu (UC6); Wycofanie produktu ze sprzedaży (UC7) |

Zależności między przypadkami użycia: UC3 (Złożenie zamówienia) zawiera sprawdzenie dostępności w wybranym oddziale i aktualizację stanu magazynowego; UC6 i UC7 najpierw sprawdzają dostępność obu węzłów, a potem zapisują zmianę w obu; przy niedostępnym węźle kończą się błędem bez zmian.

&#91;embedded content: diagram przypadków użycia UML · 2 aktorów, 7 przypadków\]

Klient i pracownik oddziału korzystają wspólnie z UC2, a pracownik oddziału dodatkowo zarządza produktami w obu węzłach (UC6, UC7).

## 4. Scenariusze użycia

### Scenariusz 1: Zakup produktu

**Aktor:** Klient

**Warunek początkowy:** Produkt jest aktywny w katalogu, a wybrany oddział (np. Katowice) ma go na stanie w wystarczającej liczbie.

**Przebieg:**

1. Klient przegląda katalog i wybiera produkty oraz oddział realizujący zamówienie.
2. Klient podaje swoje dane i listę pozycji (SKU oraz liczba sztuk).
3. System odnajduje produkty w węźle wybranego oddziału i sprawdza, czy są aktywne oraz czy oddział ma ich wystarczająco dużo.
4. System zapisuje zamówienie ze statusem NEW, dodaje jego pozycje z aktualną ceną jednostkową i wylicza wartość zamówienia.
5. System zmniejsza stan magazynowy w węźle wybranego oddziału.

**Rezultat:** Zamówienie zostaje zapisane wyłącznie w węźle wybranego oddziału, a stan magazynowy tego oddziału jest pomniejszony. Jeśli produktu brakuje, jest nieaktywny, ilość nie jest dodatnia lub jest go za mało, system zwraca błąd, a zamówienie nie jest zapisane.

### Scenariusz 2: Sprawdzenie dostępności produktu w oddziałach

**Aktor:** Klient (lub pracownik oddziału)

**Warunek początkowy:** Oba węzły są dostępne, a w katalogu istnieją produkty.

**Przebieg:**

1. Użytkownik wysyła zapytanie o stany magazynowe bez wskazywania konkretnego oddziału.
2. System odpytuje węzeł Katowice oraz węzeł Kraków.
3. System łączy wyniki obu węzłów w jedną listę z informacją o oddziale, produkcie i liczbie sztuk.

**Rezultat:** Użytkownik widzi, w którym oddziale i w jakiej liczbie produkt jest dostępny. Jest to operacja wykorzystująca dane z więcej niż jednego węzła.

### Scenariusz 3: Dodanie nowego produktu do katalogu

**Aktor:** Pracownik oddziału

**Warunek początkowy:** Produkt o danym SKU nie istnieje jeszcze w katalogu.

**Przebieg:**

1. Administrator podaje SKU, nazwę, opis i cenę nowego produktu.
2. System sprawdza, czy oba węzły są dostępne i czy SKU jeszcze nie istnieje, a następnie zapisuje produkt w węźle Katowice i w węźle Kraków.
3. System tworzy w każdym węźle rekord stanu magazynowego z zerową liczbą sztuk.
4. Następnie ten sam pracownik ustawia początkowy stan magazynowy w swoim oddziale.

**Rezultat:** Nowy produkt jest widoczny w katalogu obu oddziałów, a stany magazynowe są niezależne w każdym z nich.

## 5. Diagram bazy danych

### 5.1. Encje i relacje

Każdy węzeł ma identyczny schemat tabel. Różnią się danymi: tabele `products` mają w obu węzłach tę samą treść (katalog), a tabele `inventory`, `orders` i `order_items` zawierają dane lokalne dla oddziału.

&#91;embedded content: diagram ERD · 4 tabele, 3 relacje\]

Tabela products ma tę samą treść w obu węzłach, a inventory, orders i order_items zawierają dane lokalne oddziału.

**products** – współdzielony katalog produktów.

| Pole        | Typ           | Klucz / ograniczenie     |
| ----------- | ------------- | ------------------------ |
| id          | int           | PK                       |
| sku         | varchar(50)   | UNIQUE, NOT NULL         |
| name        | varchar(200)  | NOT NULL                 |
| description | varchar(1000) |                          |
| price       | float         | NOT NULL                 |
| active      | boolean       | NOT NULL, domyślnie true |

**inventory** – liczba sztuk produktu dostępna w danym węźle (oddziale).

| Pole       | Typ | Klucz / ograniczenie  |
| ---------- | --- | --------------------- |
| id         | int | PK                    |
| product_id | int | FK → products.id      |
| quantity   | int | NOT NULL, domyślnie 0 |

**orders** – zamówienia klientów zapisane lokalnie w wybranym oddziale.

| Pole          | Typ          | Klucz / ograniczenie    |
| ------------- | ------------ | ----------------------- |
| id            | int          | PK                      |
| customer_name | varchar(200) | NOT NULL                |
| status        | varchar(30)  | NOT NULL, domyślnie NEW |
| total         | float        | NOT NULL, domyślnie 0   |

**order_items** – pozycje zamówienia (produkt i liczba sztuk).

| Pole       | Typ   | Klucz / ograniczenie |
| ---------- | ----- | -------------------- |
| id         | int   | PK                   |
| order_id   | int   | FK → orders.id       |
| product_id | int   | FK → products.id     |
| quantity   | int   | NOT NULL             |
| unit_price | float | NOT NULL             |

### 5.2. Relacje między tabelami

- products 1 : N inventory – produkt ma stan magazynowy w danym węźle,
- products 1 : N order_items – produkt może występować w wielu pozycjach zamówień,
- orders 1 : N order_items – zamówienie składa się z jednej lub wielu pozycji.

### 5.3. Przeznaczenie tabel

- **products** – katalog produktów wspólny dla wszystkich oddziałów.
- **inventory** – dostępność produktów w konkretnym oddziale.
- **orders** – informacje o zakupach klientów w oddziale.
- **order_items** – szczegóły zamówienia: co i w jakiej liczbie zostało zamówione oraz po jakiej cenie.

## 6. Sposób rozproszenia danych

Dane są rozmieszczone w dwóch niezależnych instancjach PostgreSQL: **węzeł Katowice** (baza `sklep_katowice`) i **węzeł Kraków** (baza `sklep_krakow`). Zastosowano połączenie powielania katalogu i fragmentacji poziomej danych oddziału.

| Tabela      | Sposób rozmieszczenia                     | Katowice                        | Kraków                        |
| ----------- | ----------------------------------------- | ------------------------------- | ----------------------------- |
| products    | powielenie (pełna kopia w każdym węźle)   | pełny katalog                   | pełny katalog                 |
| inventory   | dane lokalne oddziału                     | stany magazynu Katowic          | stany magazynu Krakowa        |
| orders      | fragmentacja pozioma                      | zamówienia złożone w Katowicach | zamówienia złożone w Krakowie |
| order_items | fragmentacja pozioma (wraz z zamówieniem) | pozycje zamówień Katowic        | pozycje zamówień Krakowa      |

### 6.1. Jak to działa

- **Katalog produktów** jest powielany mechanizmem aplikacyjnym, a nie replikacją silnika bazy danych. Mutacje `createProduct` i `deleteProduct` najpierw odczytują dane z obu węzłów (jeśli któryś jest niedostępny, kończą się błędem i niczego nie zapisują), a następnie zapisują zmianę w obu węzłach w jednej sesji. Odczyt katalogu (`products`) korzysta z węzła Katowice.
- **Stany magazynowe i zamówienia** są zapisywane wyłącznie w węźle wskazanym parametrem `node`. Złożenie zamówienia w jednym oddziale nie zmienia stanu magazynu w drugim.
- **Zapytania wielowęzłowe:** `inventory` i `orders` wywołane bez parametru `node` odpytują oba węzły i łączą wyniki w jedną listę, w której każdy rekord ma pole `node`.
- **Identyfikatory:** każdy węzeł ma własne sekwencje, więc `id` nie jest globalnie unikalne (zamówienie nr 1 istnieje i w Katowicach, i w Krakowie). Rekordy odróżnia para (`node`, `id`), a produkty globalny klucz biznesowy `sku`.

### 6.2. Uzasadnienie

Stany magazynowe i zamówienia są najczęściej używane właśnie w oddziale, który je tworzy, więc trzymanie ich lokalnie skraca dostęp i izoluje oddziały od awarii siebie nawzajem. Katalog produktów jest potrzebny w każdym oddziale i zmienia się rzadko, więc jego kopia w każdym węźle nie jest kosztowna.

| Typ danych        | Strategia                            | Uzasadnienie                                                                |
| ----------------- | ------------------------------------ | --------------------------------------------------------------------------- |
| Katalog produktów | powielenie (mechanizm aplikacyjny)   | każdy oddział potrzebuje pełnego, jednakowego katalogu, a zmiany są rzadkie |
| Stany magazynowe  | fragmentacja pozioma według oddziału | stan fizyczny dotyczy lokalnego magazynu                                    |
| Zamówienia        | fragmentacja pozioma według oddziału | sprzedaż jest obsługiwana lokalnie                                          |

### 6.3. Ograniczenia tego podejścia

- Zapis katalogu do dwóch węzłów nie jest prawdziwą transakcją rozproszoną. Aplikacja najpierw sprawdza dostępność obu węzłów, więc przy wyłączonym węźle kończy się błędem bez zmian (sekcja 10.4), ale awaria dokładnie w chwili zatwierdzania zapisu mogłaby zostawić zmianę tylko w jednym węźle.
- Zmiana wykonana bezpośrednio w bazie jednego węzła, z pominięciem aplikacji, nie jest przenoszona do drugiego (sekcja 10.3).
- Odczyt katalogu zależy od węzła Katowice.

## 7. Implementacja

Kod projektu znajduje się w repozytorium: https://github.com/kmichal661/projekt-rozproszone-bazy-danych

### 7.1. Struktura

| Plik                       | Rola                                                                                                     |
| -------------------------- | -------------------------------------------------------------------------------------------------------- |
| `backend/models.py`        | Modele (PonyORM) i połączenia z obiema bazami; funkcje `list_products`, `list_inventory`, `list_orders`. |
| `backend/schema.py`        | Schemat GraphQL: zapytania `products`, `inventory`, `orders`.                                            |
| `backend/mutations.py`     | Mutacje `createProduct`, `updateInventory`, `createOrder`, `deleteProduct`.                              |
| `backend/seed_database.py` | Jednorazowe, powtarzalne zasilenie obu węzłów danymi przykładowymi.                                      |
| `backend/app.py`           | Aplikacja Starlette: endpoint `/graphql` i `/health`.                                                    |
| `docker-compose.yml`       | Dwa kontenery PostgreSQL 16 (porty 5433 i 5434), usługa seed i API (port 8000).                          |

Repozytorium zawiera też katalog `Tests/` z automatycznym zestawem testów. Zapisuje on wyniki w `Tests/results/` (`report.html`, `report.json`, `measurements.csv`), a raport HTML jest dostępny pod adresem `/reports/tests`. Komendy uruchamiania testów podano w sekcji 7.2.

### 7.2. Uruchomienie

```bash
docker compose up -d --build
docker compose ps
```

Po starcie interfejs GraphiQL jest dostępny pod adresem `http://localhost:8000/graphql`, a sprawdzenie stanu usługi pod adresem `http://localhost:8000/health`.

Reset danych PostgreSQL (usuwa wolumeny):

```bash
docker compose down -v
docker compose up -d --build
```

Uruchomienie lokalne bez Dockera (dwa pliki SQLite: `data/katowice/katowice.db` i `data/krakow/krakow.db`):

```bash
pip install -r requirements.txt
python -m backend.seed_database
python backend/app.py
```

Uruchomienie testów (pełny zestaw albo w kontenerze, bez testu awarii):

```bash
python -m Tests.run_tests
docker compose --profile tests run --rm test_runner
```

### 7.3. Operacje CRUD

| Operacja | Funkcja w API                                                        |
| -------- | -------------------------------------------------------------------- |
| CREATE   | `createProduct` (oba węzły), `createOrder` (wybrany węzeł)           |
| READ     | `products`, `inventory`, `orders` (jeden węzeł lub oba)              |
| UPDATE   | `updateInventory`; `createOrder` dodatkowo zmniejsza stan magazynowy |
| DELETE   | `deleteProduct` (usunięcie logiczne: `active = false` w obu węzłach) |

Operacja wykorzystująca dane z więcej niż jednego węzła: `inventory` bez parametru `node` (sprawdzenie, gdzie produkt jest dostępny).

### 7.4. Środowisko, w którym wykonano testy

Testy z sekcji 9 i 10 wykonano lokalnie na dwóch niezależnych instancjach PostgreSQL 16 (porty 5433 i 5434, takie same jak w `docker-compose.yml`) i Pythonie 3.11, z danymi, użytkownikiem i nazwami baz z pliku `docker-compose.yml`. Kontenerów Docker w tym środowisku nie uruchamiano. Pony ORM 0.7.17 nie działa na Pythonie 3.12, więc należy zachować wersję 3.11 z pliku `Dockerfile`.

Zestaw `Tests/` z repozytorium (bez testu awarii, który wymaga Dockera) przeszedł w tym środowisku w całości: czas odpowiedzi, obciążenie, spójność i skalowalność. Test awarii wykonano ręcznie, wyłączając bazę Krakowa (sekcja 10.4).

### 7.5. Usterki znalezione i poprawione

Podczas testów wykryto trzy usterki, które poprawiono w aktualnej wersji kodu. Endpoint `/health` zwracał błąd 500 z powodu brakującego importu `JSONResponse` w `backend/app.py`. Mutacja `createOrder` nie sprawdzała flagi `active`, więc produkt wycofany przez `deleteProduct` można było zamówić. Mutacje `createProduct` i `deleteProduct` przy niedostępnym węźle zostawiały zmianę tylko w Katowicach, a teraz kończą się błędem bez zmian w katalogach (sekcja 10.4).

## 8. Przykładowe dane

Skrypt `seed_database.py` wprowadza do każdego węzła ten sam katalog 30 produktów i osobne stany magazynowe. W tabeli pokazano 6 produktów nazwanych:

| SKU     | Nazwa                   | Cena (zł) | Stan Katowice | Stan Kraków |
| ------- | ----------------------- | --------- | ------------- | ----------- |
| LAP-001 | Laptop biznesowy        | 3499,99   | 10            | 7           |
| MON-001 | Monitor 27 cali         | 1199,00   | 15            | 9           |
| KEY-001 | Klawiatura mechaniczna  | 299,00    | 20            | 12          |
| MOU-001 | Mysz bezprzewodowa      | 149,99    | 25            | 18          |
| HED-001 | Słuchawki bezprzewodowe | 399,00    | 8             | 11          |
| WEB-001 | Kamera internetowa      | 249,00    | 14            | 6           |

Seed tworzy 240 rekordów: w każdym węźle 30 produktów (6 z tabeli powyżej i 24 wygenerowane o SKU od `SEED-001` do `SEED-024`), 30 stanów magazynowych, 30 zamówień i 30 pozycji zamówień. Ponowne uruchomienie seeda niczego nie dubluje (w sprawdzeniu utworzył 0 nowych rekordów), więc już po starcie liczba rekordów przekracza około 30 wymaganych w wytycznych. Do testów wydajnościowych dane generowano skryptem (sekcja 10.1).

Seed jest idempotentny: dodaje tylko brakujące rekordy, nie przywraca flagi `active = true` dla wcześniej wycofanego produktu i nie zmienia istniejących stanów magazynowych.

## 9. Zapytania testowe

Zapytania wysyłano do endpointu `/graphql` na danych z sekcji 8. Wyniki poniżej są skrócone tam, gdzie lista byłaby długa.

### 9.1. Odczyt katalogu

```graphql
{
  products {
    sku
    name
    price
    active
  }
}
```

**Cel:** pobranie aktywnych produktów z katalogu (odczyt z węzła Katowice).

**Wynik:** 30 produktów (36 ms), np.

```json
{"data": {"products": [
  {"sku": "LAP-001", "name": "Laptop biznesowy", "price": 3499.99, "active": true},
  {"sku": "MON-001", "name": "Monitor 27 cali", "price": 1199.0, "active": true},
  ...
  {"sku": "SEED-024", "name": "Produkt demonstracyjny 024", "price": 229.99, "active": true}
]}}
```

### 9.2. Dostępność produktów w obu oddziałach (dane z dwóch węzłów)

```graphql
{
  inventory {
    node
    quantity
    product {
      sku
    }
  }
}
```

**Cel:** sprawdzenie, gdzie i w jakiej liczbie produkty są dostępne. Zapytanie bez parametru `node` odpytuje oba węzły i łączy wyniki w jedną listę.

**Wynik:** 60 rekordów (74 ms), po 30 z węzła KATOWICE i z węzła KRAKOW, np.

```json
{"node": "KATOWICE", "quantity": 10, "product": {"sku": "LAP-001"}}
{"node": "KRAKOW", "quantity": 7, "product": {"sku": "LAP-001"}}
```

### 9.3. Dodanie produktu do katalogu (CREATE, oba węzły)

```graphql
mutation {
  createProduct(
    product: {
      sku: "SSD-001"
      name: "Dysk SSD 1 TB"
      description: "Dysk NVMe"
      price: 449.0
    }
  ) {
    ok
    message
    product {
      id
      sku
      name
      price
      active
    }
  }
}
```

**Cel:** dodanie nowego produktu do katalogu w obu węzłach.

**Wynik:** `ok = true`, produkt zapisany w obu węzłach.

```json
{
  "data": {
    "createProduct": {
      "ok": true,
      "message": "Produkt zapisano w obu węzłach",
      "product": {
        "id": 31,
        "sku": "SSD-001",
        "name": "Dysk SSD 1 TB",
        "price": 449.0,
        "active": true
      }
    }
  }
}
```

### 9.4. Zmiana stanu magazynowego (UPDATE)

```graphql
mutation {
  updateInventory(node: "KATOWICE", sku: "SSD-001", quantity: 20) {
    ok
    message
    inventory {
      node
      sku
      quantity
    }
  }
}
```

```graphql
mutation {
  updateInventory(node: "KRAKOW", sku: "SSD-001", quantity: 5) {
    ok
    message
    inventory {
      node
      sku
      quantity
    }
  }
}
```

**Cel:** ustawienie początkowych stanów nowego produktu osobno w każdym oddziale.

**Wynik:** `ok = true` dla obu zapytań, a stan zmienia się tylko w wskazanym węźle.

```json
{"updateInventory": {"ok": true, "message": "Stan magazynowy zaktualizowany", "inventory": {"node": "KATOWICE", "sku": "SSD-001", "quantity": 20}}}
{"updateInventory": {"ok": true, "message": "Stan magazynowy zaktualizowany", "inventory": {"node": "KRAKOW", "sku": "SSD-001", "quantity": 5}}}
```

### 9.5. Złożenie zamówienia (CREATE i UPDATE w jednym węźle)

```graphql
mutation {
  createOrder(
    node: "KRAKOW"
    customerName: "Anna Nowak"
    items: [{ sku: "LAP-001", quantity: 2 }, { sku: "MOU-001", quantity: 3 }]
  ) {
    ok
    message
    order {
      id
      node
      total
      status
    }
  }
}
```

**Cel:** zapisanie zamówienia w Krakowie i zmniejszenie stanu magazynowego w Krakowie.

**Wynik:** `ok = true`, zamówienie o wartości 7449,95 zł.

```json
{
  "data": {
    "createOrder": {
      "ok": true,
      "message": "Zamówienie utworzone",
      "order": { "id": 31, "node": "KRAKOW", "total": 7449.95, "status": "NEW" }
    }
  }
}
```

Po zamówieniu stany w Krakowie spadły: LAP-001 z 7 do 5, MOU-001 z 18 do 15, a w Katowicach pozostały bez zmian. Zamówienie na 500 sztuk LAP-001 zostało odrzucone błędem `Brak wystarczającej ilości produktu LAP-001` i nie zostawiło w bazie żadnego zamówienia.

### 9.6. Zamówienia z całego systemu (dane z dwóch węzłów)

```graphql
{
  orders {
    id
    node
    customerName
    status
    total
    items {
      quantity
      unitPrice
      product {
        sku
      }
    }
  }
}
```

**Cel:** zestawienie zamówień ze wszystkich oddziałów. Drugie zamówienie (4 szt. SSD-001) złożono w Katowicach.

**Wynik:** 62 zamówienia, po 31 z każdego węzła. Poniżej dwa nowo dodane:

```json
{"id": 31, "node": "KATOWICE", "customerName": "Jan Kowalski", "status": "NEW", "total": 1796.0,
 "items": [{"quantity": 4, "unitPrice": 449.0, "product": {"sku": "SSD-001"}}]}
{"id": 31, "node": "KRAKOW", "customerName": "Anna Nowak", "status": "NEW", "total": 7449.95,
 "items": [{"quantity": 3, "unitPrice": 149.99, ...}, {"quantity": 2, "unitPrice": 3499.99, ...}]}
```

### 9.7. Zapytania agregujące (COUNT, SUM) w każdym węźle

```sql
SELECT COUNT(*) AS zamowienia, COALESCE(SUM(total), 0) AS przychod FROM orders;
SELECT SUM(quantity) AS sztuk_w_magazynie FROM inventory;
```

**Cel:** liczba zamówień, przychód i liczba sztuk w magazynie. Zapytanie SQL wykonano osobno na każdej bazie.

**Wynik:**

| Węzeł    | Zamówienia | Przychód (zł) | Sztuk w magazynie |
| -------- | ---------- | ------------- | ----------------- |
| Katowice | 31         | 11 041,74     | 888               |
| Kraków   | 31         | 16 695,69     | 723               |
| Razem    | 62         | 27 737,43     | 1 611             |

Sumę „Razem” wyliczono ręcznie z wyników obu węzłów, ponieważ aplikacja nie ma gotowego zapytania zbiorczego.

### 9.8. Wycofanie produktu (DELETE, oba węzły)

```graphql
mutation {
  deleteProduct(sku: "WEB-001") {
    ok
    message
  }
}
```

**Cel:** wycofanie produktu ze sprzedaży (usunięcie logiczne).

**Wynik:** `ok = true`, komunikat `Produkt oznaczono jako nieaktywny w obu węzłach`. Kolejne zapytanie `products` zwróciło 30 aktywnych produktów (bez WEB-001, z dodanym SSD-001).

## 10. Wyniki testów systemu rozproszonego

Każdy test wykonano na lokalnych instancjach opisanych w sekcji 7.4. Czasy mierzono po stronie klienta, od wysłania zapytania do otrzymania odpowiedzi.

Wyniki liczbowe zależą od sprzętu, bieżącego obciążenia i konfiguracji (w Dockerze mogą być inne). Zestaw `Tests/` zapisuje wyniki własnego uruchomienia w plikach `report.html`, `report.json` i `measurements.csv`, więc na innym komputerze można je łatwo powtórzyć.

### 10.1. Test czasu odpowiedzi

Do obu węzłów wygenerowano skryptem N dodatkowych produktów ze stanami magazynowymi na węzeł (100, 1 000 i 10 000). Zapytanie wykonano 3 razy (dla 10 000 jeden raz) i podano medianę.

| Dane na węzeł | Zapytanie               | Zwrócone rekordy | Czas      |
| ------------- | ----------------------- | ---------------- | --------- |
| 100           | `inventory` (oba węzły) | 262              | 190 ms    |
| 1 000         | `inventory` (oba węzły) | 2 062            | 1 466 ms  |
| 10 000        | `inventory` (oba węzły) | 20 062           | 13 660 ms |
| 100           | `products` (Katowice)   | 131              | 63 ms     |
| 1 000         | `products` (Katowice)   | 1 031            | 531 ms    |
| 10 000        | `products` (Katowice)   | 10 031           | 4 493 ms  |

Wniosek: czas rośnie w przybliżeniu liniowo z liczbą rekordów (około 0,7 ms na rekord w zapytaniu inventory i 0,5 ms w products). Wynika to z budowy kodu: każdy rekord i każde jego pole jest pobierane osobno, w osobnej sesji bazodanowej, zamiast jednym zapytaniem zbiorczym.

### 10.2. Test obciążenia

Porównano 1, 10 i 100 zapytań na danych z sekcji 8 (62 rekordy w zapytaniu `inventory`), wysyłanych kolejno oraz równolegle przez 10 wątków. Wszystkie zapytania zakończyły się powodzeniem.

| Zapytanie                    | Liczba zapytań | Wątki | Czas całkowity | Średni czas zapytania | Maks.  |
| ---------------------------- | -------------- | ----- | -------------- | --------------------- | ------ |
| odczyt `inventory` (2 węzły) | 1              | 1     | 67 ms          | 66 ms                 | 66 ms  |
| odczyt `inventory` (2 węzły) | 10             | 1     | 727 ms         | 73 ms                 | 104 ms |
| odczyt `inventory` (2 węzły) | 100            | 1     | 6 393 ms       | 64 ms                 | 105 ms |
| odczyt `inventory` (2 węzły) | 10             | 10    | 566 ms         | 296 ms                | 560 ms |
| odczyt `inventory` (2 węzły) | 100            | 10    | 6 436 ms       | 617 ms                | 803 ms |
| zapis `createOrder`          | 1              | 1     | 8 ms           | 8 ms                  | 8 ms   |
| zapis `createOrder`          | 10             | 1     | 47 ms          | 5 ms                  | 5 ms   |
| zapis `createOrder`          | 100            | 1     | 516 ms         | 5 ms                  | 26 ms  |
| zapis `createOrder`          | 10             | 10    | 46 ms          | 25 ms                 | 41 ms  |
| zapis `createOrder`          | 100            | 10    | 462 ms         | 44 ms                 | 58 ms  |

Wniosek: przy zapytaniach wysyłanych kolejno czas całkowity rośnie liniowo z ich liczbą (około 65 ms na odczyt i 5 ms na zapis). Równoległość 10 wątków nie skróciła czasu całkowitego odczytów (100 odczytów: 6 393 ms kolejno i 6 436 ms równolegle), a średni czas pojedynczego zapytania wzrósł z 64 do 617 ms. Sugeruje to, że pojedynczy proces API przetwarza zapytania odczytu głównie szeregowo. Zapisy są szybsze i przy 10 wątkach skróciły czas całkowity tylko nieznacznie (516 ms kolejno, 462 ms równolegle).

### 10.3. Test spójności danych

| Test | Działanie                                                                | Wynik                                                                                                                                                       |
| ---- | ------------------------------------------------------------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------- |
| T1   | `createProduct` z SKU CON-001                                            | Produkt natychmiast widoczny w obu bazach (cena 100 w Katowicach i w Krakowie). Zapis do obu węzłów odbywa się w tym samym żądaniu, więc nie ma opóźnienia. |
| T2   | `updateInventory` w Katowicach na 42 szt.                                | Katowice: 42, Kraków: 0. Stany magazynowe są lokalne, więc tak ma być.                                                                                      |
| T3   | Zmiana ceny CON-001 na 120 bezpośrednio w bazie Katowic (poza aplikacją) | Katowice: 120, Kraków: nadal 100. Brak automatycznej synchronizacji, a API (czytające katalog z Katowic) pokazuje 120.                                      |
| T4   | Zamówienie przekraczające stan magazynowy                                | Błąd, w tabeli `orders` nie został żadny rekord (transakcja wycofana).                                                                                      |

Wniosek: dane są spójne, dopóki zmiany przechodzą przez aplikację. Zmiana katalogu wykonana poza nią powoduje rozbieżność między węzłami.

### 10.4. Test awarii

Węzeł Kraków wyłączono poleceniem `pg_ctlcluster 16 krk stop`, a następnie wykonano po kolei zapytania.

| Operacja przy wyłączonym Krakowie                    | Wynik                                                                                |
| ---------------------------------------------------- | ------------------------------------------------------------------------------------ |
| `products` (katalog)                                 | Działa (odczyt z Katowic).                                                           |
| `inventory(node:"KATOWICE")`                         | Działa.                                                                              |
| `createOrder` w Katowicach                           | Działa.                                                                              |
| `inventory(node:"KRAKOW")`, `createOrder` w Krakowie | Błąd `connection refused`.                                                           |
| `inventory` i `orders` bez `node` (oba węzły)        | Błąd całego zapytania, bez częściowych wyników z działających Katowic.               |
| `createProduct` (oba węzły)                          | Błąd. Produkt FAIL-001 nie został zapisany w żadnym węźle (0 rekordów w Katowicach). |
| `deleteProduct` (oba węzły)                          | Błąd. Produkt KEY-001 nadal ma `active = true` w Katowicach.                         |

Po ponownym uruchomieniu Krakowa (bez restartu API):

- `inventory` dla Krakowa, `orders` z obu węzłów i `createOrder` w Krakowie działają poprawnie, a dane Krakowa nie zostały utracone.
- Ponowne `createProduct` (FAIL-001) i `deleteProduct` (KEY-001) kończą się powodzeniem, a katalogi w obu węzłach są identyczne (porównanie SKU, flagi `active` i ceny nie pokazało różnic).

### 10.5. Podsumowanie testów i skalowalność

| Test            | Wariant                                                   | Wynik                                             | Wniosek                                                 |
| --------------- | --------------------------------------------------------- | ------------------------------------------------- | ------------------------------------------------------- |
| Czas odpowiedzi | 100 / 1 000 / 10 000 rekordów na węzeł                    | 190 ms / 1,5 s / 13,7 s                           | Wzrost liniowy, brak przyspieszenia przy dużych danych. |
| Obciążenie      | 1 / 10 / 100 odczytów                                     | 67 ms / 727 ms / 6,4 s                            | Wzrost liniowy.                                         |
| Obciążenie      | 100 odczytów, 10 wątków                                   | 6,4 s                                             | Równoległość nie poprawia czasu całkowitego.            |
| Spójność        | zapis katalogu przez aplikację                            | natychmiast w obu węzłach                         | Poprawnie.                                              |
| Spójność        | zmiana poza aplikacją                                     | rozbieżność                                       | Brak replikacji na poziomie bazy.                       |
| Awaria          | Kraków wyłączony                                          | Katowice działają, zapytania wielowęzłowe zawodzą | Izolacja operacji lokalnych działa.                     |
| Awaria          | `createProduct` i `deleteProduct` przy niedostępnym węźle | błąd, brak zmian w katalogach                     | Zapis chroniony sprawdzeniem obu węzłów przed zapisem.  |

## 11. Wnioski końcowe

- **Czy rozproszenie danych działa poprawnie?** Tak. Zamówienia i stany magazynowe są zapisywane lokalnie w węźle oddziału, a zapytania `inventory` i `orders` bez parametru `node` poprawnie łączą dane z obu węzłów.
- **Czy dane pozostają spójne?** W normalnej pracy tak, bo katalog jest zapisywany do obu węzłów w jednym żądaniu, a przy niedostępnym węźle zapis jest odrzucany bez zmian. Spójność nie jest gwarantowana przy zmianach wykonanych poza aplikacją ani przy awarii w chwili zatwierdzania zapisu.
- **Jak zmienia się czas odpowiedzi?** Rośnie liniowo z liczbą danych (13,7 s dla 20 tys. rekordów w zapytaniu `inventory`) i liczbą zapytań. Główną przyczyną jest pobieranie każdego rekordu i pola osobno.
- **Co dzieje się przy awarii jednego węzła?** Operacje lokalne w drugim węźle i odczyt katalogu działają dalej. Zapytania obejmujące oba węzły zwracają błąd zamiast częściowych wyników, a dodanie i wycofanie produktu kończą się błędem bez zmian w katalogach. Po ponownym uruchomieniu węzła system wraca do działania bez ręcznej naprawy.

**Zalety:** prosta architektura, niezależne działanie oddziałów, izolacja awarii dla danych lokalnych, łatwe uruchomienie jednym poleceniem, powtarzalna demonstracja dzięki idempotentnemu seedowi i automatycznemu raportowi testów (HTML, JSON, CSV) oraz flaga `active`, która chroni przed zamówieniem wycofanych produktów.

**Ograniczenia:** brak pełnej transakcji rozproszonej (zapis chroniony tylko sprawdzeniem obu węzłów przed zapisem) i brak replikacji na poziomie bazy, brak logowania i autoryzacji, odczyt katalogu zależny od Katowic, brak częściowych wyników przy awarii, identyfikatory niepowtarzalne tylko w obrębie węzła, wydajność ograniczona sposobem pobierania danych.

**Możliwe usprawnienia:** replikacja logiczna PostgreSQL (albo kolejka zdarzeń z asynchroniczną replikacją) dla tabeli `products`, zwracanie częściowych wyników z działających węzłów, pobieranie danych jednym zapytaniem zbiorczym zamiast osobno dla każdego pola oraz uwierzytelnianie użytkowników.
