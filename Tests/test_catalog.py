from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TestDescription:
    section: str
    name: str
    purpose: str
    method: str
    expected: str


DESCRIPTIONS = {
    "response_time": TestDescription(
        "6.1",
        "Czas odpowiedzi",
        "Sprawdzenie wpływu liczby produktów na czas wykonania zapytania GraphQL.",
        "Generowanie 100, 1 000 i 10 000 produktów, a następnie jednokrotny odczyt katalogu przez API.",
        "Zapytanie kończy się bez błędu, a liczba zwróconych produktów testowych PERF-* odpowiada liczbie wygenerowanych produktów. Katalog może zawierać również dane demonstracyjne.",
    ),
    "load": TestDescription(
        "6.2",
        "Test obciążenia",
        "Sprawdzenie zachowania API przy rosnącej liczbie identycznych operacji.",
        "Wykonanie zapytania katalogu 1, 10 i 100 razy oraz pomiar czasu całkowitego i średniego.",
        "Wszystkie zapytania kończą się poprawnie; raport pokazuje zmianę czasu wraz z obciążeniem.",
    ),
    "consistency": TestDescription(
        "6.3",
        "Spójność danych",
        "Sprawdzenie replikacji katalogu oraz lokalności stanów magazynowych.",
        "Utworzenie produktu w obu bazach, zmiana magazynu Katowic i odczyt obu oddziałów.",
        "Produkt jest widoczny w obu bazach, ale zmiana magazynu Katowic nie zmienia magazynu Krakowa.",
    ),
    "failure": TestDescription(
        "6.4",
        "Test awarii",
        "Sprawdzenie działania systemu po wyłączeniu bazy Krakowa.",
        "Zatrzymanie kontenera PostgreSQL Kraków, odczyt danych Katowic, ponowne uruchomienie i odczyt obu węzłów.",
        "Dane Katowic są dostępne podczas awarii; po restarcie Krakowa system wraca do działania.",
    ),
    "scalability": TestDescription(
        "6.5",
        "Skalowalność",
        "Ocena wpływu wzrostu liczby danych na czas odpowiedzi API.",
        "Porównanie pomiarów dla 100, 1 000 i 10 000 rekordów.",
        "Raport pokazuje trend czasu odpowiedzi i pozwala ocenić wpływ rozmiaru danych.",
    ),
}