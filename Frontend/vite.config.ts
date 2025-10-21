// Frontend/vite.config.ts
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { fileURLToPath, URL } from 'node:url'

// Vite config met alias '@' → 'src' en standaard React plugin.
// Geen extra aannames (geen base/publicPath wijzigingen).
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
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
})
