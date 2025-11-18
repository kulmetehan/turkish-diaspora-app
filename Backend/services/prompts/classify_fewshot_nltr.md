---
title: Classify Prompt Few-shot (NLTR)
status: active
last_updated: 2025-11-04
scope: backend
owners: [tda-core]
---

# Classify Prompt Few-shot (NLTR)

Reference examples used when tuning the Dutch/Turkish classification prompt for `ClassifyService`. Each example is a `(name, address, type) → expected JSON` pair. Keep this list in sync with the actual prompt (`Backend/services/prompts/classify_system.txt`).

> **Note:** `expected_json` uses the schema enforced by `validate_classification_payload` (`action`, `category`, `confidence_score`, optional `reason`). Confidence scores are indicative.

| # | Name | Address | Type | Expected JSON |
| --- | --- | --- | --- | --- |
| 1 | Kaya Bakkerij | Westblaak 1, Rotterdam | bakery | `{ "action": "keep", "category": "bakery", "confidence_score": 0.90, "reason": "Turks klinkende naam + bakkerij." }` |
| 2 | Istanbul Döner & Pide | Beijerlandselaan 100, Rotterdam | restaurant | `{ "action": "keep", "category": "kebab", "confidence_score": 0.95, "reason": "Döner/Pide → kebab/pide zaak." }` |
| 3 | Saray Baklava | Den Haag | bakery | `{ "action": "keep", "category": "sweets", "confidence_score": 0.92, "reason": "Baklava → Turkse patisserie/sweets." }` |
| 4 | Kuaför Ayşe | Amsterdam | hair_care | `{ "action": "keep", "category": "barber", "confidence_score": 0.88, "reason": "TR woord 'Kuaför' → kapsalon." }` |
| 5 | Kasap Yıldız | Utrecht | butcher | `{ "action": "keep", "category": "butcher", "confidence_score": 0.93, "reason": "TR 'Kasap' → slagerij." }` |
| 6 | Anadolu Market | Schiedam | supermarket | `{ "action": "keep", "category": "supermarket", "confidence_score": 0.92, "reason": "Market/bakkal → supermarkt met TR focus." }` |
| 7 | Eyüp Sultan Camii | Vlaardingen | mosque | `{ "action": "keep", "category": "mosque", "confidence_score": 0.98, "reason": "Camii/Moskee → religieuze locatie." }` |
| 8 | Turk Hava Kargo | Rotterdam | moving_company | `{ "action": "keep", "category": "cargo", "confidence_score": 0.86, "reason": "Kargo → pakket/cargo naar TR." }` |
| 9 | Atlas Reisbureau | Rotterdam | travel_agency | `{ "action": "keep", "category": "travel_agency", "confidence_score": 0.84, "reason": "Reisbureau vaak TR routes." }` |
| 10 | Bakkerij Avrasya | Rotterdam | bakery | `{ "action": "keep", "category": "bakery", "confidence_score": 0.88, "reason": "Avrasya = Turkse naam (Eurazië)." }` |
| 11 | Bakkerij Enes | Den Haag | bakery | `{ "action": "keep", "category": "bakery", "confidence_score": 0.85, "reason": "Enes = veelvoorkomende Turkse naam." }` |
| 12 | Bakkerij Kees | Nieuw-Beijerland | bakery | `{ "action": "ignore", "category": "other", "confidence_score": 0.70, "reason": "Geen TR indicaties, generiek NL." }` |
| 13 | Pizzeria Napoli | Rotterdam | restaurant | `{ "action": "ignore", "category": "other", "confidence_score": 0.75, "reason": "Italiaans; geen TR signalen." }` |
| 14 | Barber Bros | Rotterdam | hair_care | `{ "action": "ignore", "category": "other", "confidence_score": 0.65, "reason": "Generiek Engels; geen TR signalen." }` |
| 15 | Yeni Cami | Schiedam | mosque | `{ "action": "keep", "category": "mosque", "confidence_score": 0.95, "reason": "Cami/Moskee met Turkse naam → duidelijk diaspora-relevant." }` |
| 16 | Süleymaniye Moskee | Rotterdam | mosque | `{ "action": "keep", "category": "mosque", "confidence_score": 0.97, "reason": "Moskee met Turkse religieuze naam → duidelijk Turkse gemeenschap." }` |

## Usage tips

- Keep the list concise (10–15 examples) to avoid over-influencing the prompt.
- Prefer examples that highlight edge cases (e.g., Turkish keywords vs. generic Dutch names).
- After updating this file, run a dry-run classification batch to confirm the prompt still meets acceptance criteria.
- Cross-reference category enums with `app/models/ai.py` to avoid typos.
