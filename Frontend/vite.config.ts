import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";
import path from "node:path";

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), "");
  // Gebruik altijd dit base-pad voor GitHub Pages project site:
  const BASE_PATH = mode === "production"
    ? "/turkish-diaspora-app/"
    : "/";

  const API_TARGET = env.VITE_API_PROXY_TARGET?.trim() || "http://127.0.0.1:8000";

  return {
    plugins: [react()],
    base: BASE_PATH,
    resolve: { alias: { "@": path.resolve(__dirname, "./src") } },
    server: {
      proxy: {
        "/api": {
          target: API_TARGET,
          changeOrigin: true,
          secure: false,
        },
      },
    },
    build: { outDir: "dist", sourcemap: true },
  };
});
