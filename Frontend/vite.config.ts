// Frontend/vite.config.ts
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import path from "node:path";

/**
 * Belangrijk:
 * - In production (npm run build op CI) hardcoden we base naar je repo-pad.
 * - In dev is base altijd "/", Vite negeert base grotendeels voor de dev server.
 */
const BASE_PROD = "/turkish-diaspora-app/";

export default defineConfig(({ mode }) => {
  const isProd = mode === "production";

  return {
    plugins: [react()],
    base: isProd ? BASE_PROD : "/",
    resolve: {
      alias: { "@": path.resolve(__dirname, "./src") },
    },
    server: {
      port: 5173,
      proxy: {
        "/api": {
          target: "http://127.0.0.1:8000",
          changeOrigin: true,
          secure: false,
        },
      },
    },
    build: {
      outDir: "dist",
      sourcemap: true,
      chunkSizeWarningLimit: 1200,
    },
  };
});
