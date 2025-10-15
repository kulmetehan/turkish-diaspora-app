// Frontend/vite.config.ts
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Vite dev-proxy: alles wat met /api begint gaat naar FastAPI (127.0.0.1:8000)
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      "/api": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true,
        // optioneel: als jouw backend geen /api prefix heeft, kun je hier herschrijven,
        // maar in ons geval heeft backend /api/v1/locations, dus geen rewrite nodig.
        // rewrite: (path) => path.replace(/^\/api/, "")
      },
    },
  },
});
