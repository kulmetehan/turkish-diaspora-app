# Environment Config – Developer Guide

Dit document legt uit hoe je `.env` correct instelt voor lokale ontwikkeling, Render-deployments en Supabase-connecties.

---

## 1️⃣ Bestandenstructuur

| Bestand | Omschrijving |
|----------|---------------|
| `.env.template` | Basissjabloon met alle vereiste variabelen |
| `.env` | Lokale kopie met eigen waarden |
| Render Secrets | Productie/staging secrets in Render dashboard |

### Kopieer voor lokale setup:
```bash
cp .env.template .env
# Vul je eigen waarden in
