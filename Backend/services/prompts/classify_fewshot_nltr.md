### EXAMPLE 1
Naam: "Kaya Bakkerij"
Adres: "Westblaak 1, Rotterdam"
Type: "bakery"
EXPECTED_JSON:
{"action":"keep","category":"bakery","confidence_score":0.90,"reason":"Turks klinkende naam + bakkerij."}

### EXAMPLE 2
Naam: "Istanbul Döner & Pide"
Adres: "Beijerlandselaan 100, Rotterdam"
Type: "restaurant"
EXPECTED_JSON:
{"action":"keep","category":"kebab","confidence_score":0.95,"reason":"Döner/Pide → kebab/pide zaak."}

### EXAMPLE 3
Naam: "Saray Baklava"
Adres: "Den Haag"
Type: "bakery"
EXPECTED_JSON:
{"action":"keep","category":"sweets","confidence_score":0.92,"reason":"Baklava → Turkse patisserie/sweets."}

### EXAMPLE 4
Naam: "Kuaför Ayşe"
Adres: "Amsterdam"
Type: "hair_care"
EXPECTED_JSON:
{"action":"keep","category":"barbershop","confidence_score":0.88,"reason":"TR woord 'Kuaför' → kapsalon."}

### EXAMPLE 5
Naam: "Kasap Yıldız"
Adres: "Utrecht"
Type: "butcher"
EXPECTED_JSON:
{"action":"keep","category":"butcher","confidence_score":0.93,"reason":"TR 'Kasap' → slagerij."}

### EXAMPLE 6
Naam: "Anadolu Market"
Adres: "Schiedam"
Type: "supermarket"
EXPECTED_JSON:
{"action":"keep","category":"supermarket","confidence_score":0.92,"reason":"Market/bakkal → supermarkt met TR focus."}

### EXAMPLE 7
Naam: "Eyüp Sultan Camii"
Adres: "Vlaardingen"
Type: "mosque"
EXPECTED_JSON:
{"action":"keep","category":"mosque","confidence_score":0.98,"reason":"Camii/Moskee → religieuze locatie."}

### EXAMPLE 8
Naam: "Turk Hava Kargo"
Adres: "Rotterdam"
Type: "moving_company"
EXPECTED_JSON:
{"action":"keep","category":"cargo","confidence_score":0.86,"reason":"Kargo → pakket/cargo naar TR."}

### EXAMPLE 9
Naam: "Atlas Reisbureau"
Adres: "Rotterdam"
Type: "travel_agency"
EXPECTED_JSON:
{"action":"keep","category":"travel_agency","confidence_score":0.84,"reason":"Reisbureau vaak TR routes."}

### EXAMPLE 10
Naam: "Bakkerij Kees"
Adres: "Nieuw-Beijerland"
Type: "bakery"
EXPECTED_JSON:
{"action":"ignore","category":"other","confidence_score":0.70,"reason":"Geen TR indicaties, generiek NL."}

### EXAMPLE 11
Naam: "Pizzeria Napoli"
Adres: "Rotterdam"
Type: "restaurant"
EXPECTED_JSON:
{"action":"ignore","category":"other","confidence_score":0.75,"reason":"Italiaans; geen TR signalen."}

### EXAMPLE 12
Naam: "Barber Bros"
Adres: "Rotterdam"
Type: "hair_care"
EXPECTED_JSON:
{"action":"ignore","category":"other","confidence_score":0.65,"reason":"Generiek Engels; geen TR signalen."}
