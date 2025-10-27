# Frontend Dev Setup

1. Open a terminal in the Frontend directory:

   ```bash
   cd "Turkish Diaspora App/Frontend"
   ```

2. Install dependencies (this is required especially for recharts used by the Metrics dashboard tab):

   ```bash
   npm install
   ```

3. Start the dev server:

   ```bash
   npm run dev
   ```

4. In the browser, go to:

   http://localhost:5173/#/admin

   - The “Locations” tab should load without issues.
   - The “Metrics” tab lazy-loads the MetricsDashboard component. That component imports recharts.

   If you see an error like:

   Failed to resolve import "recharts" ...

   it usually means npm install didn’t run in the Frontend directory, so Frontend/node_modules/recharts is missing.

   NOTE:
   - Do NOT run npm install from the monorepo root. You must be inside the Frontend folder.
   - The backend (uvicorn app.main:app --reload) must be running separately so that /admin/metrics/snapshot resolves.
