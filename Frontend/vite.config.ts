// Frontend/vite.config.ts
import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";
import path from "node:path";

// Zorg dat base in productie (GitHub Pages) altijd "/<repo>/" is.
// Lokaal blijft base gewoon "/".
function resolveBase(mode: string, envBase?: string) {
  const repo = (process.env.GITHUB_REPOSITORY || "").split("/")[1] || "";
  const inCI = !!process.env.GITHUB_ACTIONS; // True op GitHub Actions
  // Als we in CI bouwen én een repo-naam hebben, aannemen dat het Pages (project site) is
  if (mode === "production" && inCI && repo) {
    return `/${repo.replace(/^\/+|\/+$/g, "")}/`;
  }
  // Val terug op VITE_BASE_PATH of "/"
  const raw = (envBase || "/").trim();
  const norm = `/${raw.replace(/^\/+|\/+$/g, "")}/`;
  return norm === "//" ? "/" : norm;
}

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), "");

  // Dev proxy target (FastAPI)
  const API_TARGET = (env.VITE_API_PROXY_TARGET || "http://127.0.0.1:8000").trim();

  // Base pad bepalen (CI/GitHub Pages -> /<repo>/, anders env of "/")
  const BASE_PATH = resolveBase(mode, env.VITE_BASE_PATH);

  return {
    plugins: [react()],
    base: BASE_PATH,
    resolve: {
      alias: {
        "@": path.resolve(__dirname, "./src"),
      },
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
      // optioneel: kleinere assets warning minder streng maken
      chunkSizeWarningLimit: 1200,
    },
  };
});
