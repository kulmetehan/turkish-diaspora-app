// Frontend/vite.config.ts
import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";

/**
 * - Dev: proxy naar http://127.0.0.1:8000 blijft werken
 * - Prod (GitHub Pages): base = "/turkish-diaspora-app/" via env-flag GITHUB_PAGES=true
 *   (de workflow zet die flag vóór npm run build)
 */
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), "");
  const isPages = !!env.GITHUB_PAGES;

  return {
    plugins: [react()],
    base: isPages ? "/turkish-diaspora-app/" : "/",
    server: {
      proxy: {
        "/api": {
          target: "http://127.0.0.1:8000",
          changeOrigin: true,
          // rewrite: (path) => path.replace(/^\/api/, ""),
        },
      },
    },
  };
});
