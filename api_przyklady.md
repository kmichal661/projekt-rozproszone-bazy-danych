# Przykłady zapytań API GraphQL

Ten plik zawiera komplet aktualnie dostępnych zapytań i mutacji. Każdy blok `graphql` można wkleić osobno do interfejsu GraphiQL:

```text
http://localhost:8000/graphql
```

Nazwy argumentów w GraphQL używają formatu `camelCase`, np. `customerName`, mimo że w Pythonie pole nosi nazwę `customer_name`.

## Zapytania (`Query`)

### 1. Lista aktywnych produktów

```graphql
{
  products {
    id
    sku
    name
    description
    price
    active
  }
}
```

Katalog zwraca produkty aktywne. Produkt z `active: false` nie pojawi się na tej liście.

### 2. Wszystkie stany magazynowe

```graphql
{
  inventory {
    id
    node
    quantity
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

### 3. Stany magazynowe Katowic

```graphql
{
  inventory(node: "KATOWICE") {
    id
    node
    quantity
    product {
      sku
      name
      active
    }
  }
}
```

### 4. Stany magazynowe Krakowa

```graphql
{
  inventory(node: "KRAKOW") {
    id
    node
    quantity
    product {
      sku
      name
      active
    }
  }
}
```

### 5. Wszystkie zamówienia

```graphql
{
  orders {
    id
    node
    customerName
    status
    total
    items {
      id
      quantity
      unitPrice
      product {
        sku
        name
      }
    }
  }
}
```

### 6. Zamówienia Katowic

```graphql
{
  orders(node: "KATOWICE") {
    id
    node
    customerName
    status
    total
    items {
      quantity
      unitPrice
      product { sku name }
    }
  }
}
```

### 7. Zamówienia Krakowa

```graphql
{
  orders(node: "KRAKOW") {
    id
    node
    customerName
    status
    total
    items {
      quantity
      unitPrice
      product { sku name }
    }
  }
}
```

## Mutacje (`Mutation`)

### 8. Utworzenie produktu w obu replikach

Zmień SKU przed kolejnym uruchomieniem, ponieważ musi być unikalne w obu bazach.

```graphql
mutation {
  createProduct(product: {
    sku: "DEMO-001"
    name: "Produkt demonstracyjny"
    description: "Produkt utworzony przez GraphiQL"
    price: 99.99
  }) {
    ok
    message
    product {
      id
      sku
      name
      description
      price
      active
    }
  }
}
```

Efekt: produkt i stan `0` powstają w Katowicach oraz Krakowie.

### 9. Aktualizacja stanu magazynowego Katowic

Najpierw utwórz produkt `DEMO-001` albo użyj istniejącego, aktywnego SKU.

```graphql
mutation {
  updateInventory(
    node: "KATOWICE"
    sku: "DEMO-001"
    quantity: 25
  ) {
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

### 10. Aktualizacja stanu magazynowego Krakowa

```graphql
mutation {
  updateInventory(
    node: "KRAKOW"
    sku: "DEMO-001"
    quantity: 15
  ) {
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

### 11. Utworzenie zamówienia w Katowicach

Poniższa mutacja działa po ustawieniu stanu `DEMO-001` na co najmniej `2` w Katowicach.

```graphql
mutation {
  createOrder(
    node: "KATOWICE"
    customerName: "Jan Kowalski"
    items: [
      { sku: "DEMO-001", quantity: 2 }
    ]
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

### 12. Utworzenie zamówienia w Krakowie z wieloma pozycjami

Przed uruchomieniem ustaw odpowiednie stany dla obu SKU w Krakowie.

```graphql
mutation {
  createOrder(
    node: "KRAKOW"
    customerName: "Anna Nowak"
    items: [
      { sku: "DEMO-001", quantity: 1 }
      { sku: "LAP-001", quantity: 1 }
    ]
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

### 13. Logiczne usunięcie produktu

Ta mutacja ustawia `active: false` w obu replikach. Jest celowo nieodwracalna przez bieżące API, dlatego używaj SKU demonstracyjnego.

```graphql
mutation {
  deleteProduct(sku: "DEMO-001") {
    ok
    message
  }
}
```

Po jej wykonaniu próba utworzenia zamówienia z `DEMO-001` zwróci błąd, a produkt nie pojawi się w zapytaniu `products`.

## Gotowa sekwencja demonstracyjna

Wklej kolejno bloki **8**, **9**, **10**, **11**, **12**, **5** i **13**. Pokazuje ona kolejno: replikację katalogu, niezależne stany magazynowe, lokalne zamówienia, odczyt zamówień i logiczne usunięcie produktu.

Po ponownym wykonaniu sekwencji zmień `DEMO-001` na nowe SKU, na przykład `DEMO-002`.

## Endpointy HTTP pomocnicze

Health check:

```bash
curl http://localhost:8000/health
```

Raport z ostatniego uruchomienia testów:

```text
http://localhost:8000/reports/tests
```

Endpoint raportu zwróci `404`, dopóki testy nie wygenerują pliku `Tests/results/report.html`.
