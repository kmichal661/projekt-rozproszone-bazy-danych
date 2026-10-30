from .test_models import TestDefinition


CATALOG: dict[str, TestDefinition] = {
    "response_time": TestDefinition(
        "6.1", "Czas odpowiedzi", "Pomiar odczytu katalogu dla rosnącej liczby produktów.",
        "Dodaj dane PERF-* i wykonaj jedno zapytanie katalogowe dla każdego rozmiaru.",
        "Zapytanie nie zwraca błędu i zawiera dokładnie oczekiwaną liczbę produktów PERF-*.",
    ),
    "load": TestDefinition(
        "6.2", "Test obciążenia", "Sprawdzenie stabilności API przy powtarzanych odczytach.",
        "Wykonaj zapytanie katalogowe 1, 10 i 100 razy.",
        "Wszystkie odpowiedzi są poprawne; raport zawiera czas całkowity i średni.",
    ),
    "consistency": TestDefinition(
        "6.3", "Spójność danych", "Sprawdzenie replikacji katalogu i lokalności magazynu.",
        "Utwórz produkt, zmień stan Katowic i odczytaj oba oddziały.",
        "Katalog jest w obu bazach, a zmieniony stan występuje wyłącznie w Katowicach.",
    ),
    "failure": TestDefinition(
        "6.4", "Test awarii", "Sprawdzenie dostępności Katowic przy awarii Krakowa.",
        "Zatrzymaj PostgreSQL Kraków, wykonaj odczyty, uruchom go ponownie i sprawdź odzyskanie.",
        "Katowice pozostają dostępne podczas awarii, a oba węzły działają po restarcie.",
    ),
    "scalability": TestDefinition(
        "6.5", "Skalowalność", "Porównanie czasu odczytu dla rosnącego wolumenu danych.",
        "Dodaj 100, 1 000 i 10 000 produktów oraz zmierz odczyt katalogu.",
        "Raport pokazuje czasy dla każdego rozmiaru bez błędów API.",
    ),
}
