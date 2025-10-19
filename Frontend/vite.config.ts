import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";
import path from "node:path";

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), "");

  // Base-path voor prod builds (GitHub Pages project site): bv. "/turkish-diaspora-app/"
  // Zet dit in je CI of .env.production: VITE_BASE_PATH=/turkish-diaspora-app/
  const BASE_PATH = env.VITE_BASE_PATH?.trim() || "/";

  // Dev proxy target (FastAPI)
  const API_TARGET = env.VITE_API_PROXY_TARGET?.trim() || "http://127.0.0.1:8000";

  return {
    plugins: [react()],
    base: BASE_PATH,
    resolve: {
      alias: { "@": path.resolve(__dirname, "./src") },
    },
    server: {
      port: 5173,
      proxy: {
        "/api": {
          target: API_TARGET,
          changeOrigin: true,
          secure: false,
        },
      },
    },
    build: {
      outDir: "dist",
      sourcemap: true,
    },
  };
});
