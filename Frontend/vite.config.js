import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";
import path from "node:path";
export default defineConfig(function (_a) {
    var _b, _c;
    var mode = _a.mode;
    var env = loadEnv(mode, process.cwd(), "");
    // Base-path voor prod builds (GitHub Pages project site): bv. "/turkish-diaspora-app/"
    // Zet dit in je CI of .env.production: VITE_BASE_PATH=/turkish-diaspora-app/
    var BASE_PATH = ((_b = env.VITE_BASE_PATH) === null || _b === void 0 ? void 0 : _b.trim()) || "/";
    // Dev proxy target (FastAPI)
    var API_TARGET = ((_c = env.VITE_API_PROXY_TARGET) === null || _c === void 0 ? void 0 : _c.trim()) || "http://127.0.0.1:8000";
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
