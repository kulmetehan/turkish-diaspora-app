// Frontend/vite.config.ts
import react from '@vitejs/plugin-react'
import { fileURLToPath, URL } from 'node:url'
import { defineConfig, loadEnv, type PluginOption } from 'vite'

// Vite config met alias '@' → 'src' en standaard React plugin.
// Configured for Render deployment (root path) - can be overridden with VITE_BASE_PATH env var
export default defineConfig(({ mode }) => {
  // Load env file based on `mode` in the current working directory.
  // Only load variables with VITE_ prefix for security.
  const env = loadEnv(mode, process.cwd(), 'VITE_')
  
  return {
    plugins: [react()] as PluginOption[],
    resolve: {
      alias: {
        '@': fileURLToPath(new URL('./src', import.meta.url)),
      },
    },
    // Base path configuration - use environment variable or default to root
    // For Render deployment, use root path "/"
    // For GitHub Pages, set VITE_BASE_PATH="/turkish-diaspora-app/"
    base: env.VITE_BASE_PATH || '/',
    // Optioneel: wat vriendelijkere build warnings
    build: {
      sourcemap: false,
      chunkSizeWarningLimit: 1200,
    },
    server: {
      // Handig bij mobiel/devices testen; commentaar weg te halen indien gewenst:
      // host: true,
      // port: 5173,
    },
  }
})
