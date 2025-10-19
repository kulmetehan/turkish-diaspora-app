# Automated Category Runs

Deze module vervangt de oude Render-cronjobs.  
Elke diaspora-categorie draait dagelijks via GitHub Actions.

| Categorie       | Tijd (UTC) | Daglimiet | Verwachte API-calls |
|-----------------|-------------|------------|---------------------|
| bakery          | 02:00       | ≤ 1000     | ± 900               |
| restaurant      | 02:00       | ≤ 1000     | ± 950               |
| supermarket     | 02:00       | ≤ 1000     | ± 800               |
| barber          | 02:00       | ≤ 1000     | ± 700               |
| mosque          | 02:00       | ≤ 1000     | ± 600               |
| travel_agency   | 02:00       | ≤ 1000     | ± 500               |

### Werking
1. **Matrix-strategie**: één job per categorie.  
2. **Omgeving**: Python 3.11 + `Backend/requirements.txt`.  
3. **Secrets**:
   - `DATABASE_URL`
   - `GOOGLE_API_KEY`
   - `SUPABASE_URL`
   - `SUPABASE_KEY`
4. **Limieten**:
   - `--max-total-inserts 1000`
   - `--max-per-cell-per-category 20`
5. **Output**: JSON-logs in GitHub Actions console.  
6. **State**: records worden ingevoegd met `state='CANDIDATE'`.

### Lokale test
```bash
cd Backend
source .venv/bin/activate
python -m app.workers.discovery_bot --categories bakery --max-total-inserts 50
