// Frontend/vite.config.ts
import react from '@vitejs/plugin-react'
import { fileURLToPath, URL } from 'node:url'
import { defineConfig } from 'vite'

// Vite config met alias '@' → 'src' en standaard React plugin.
// Configured for GitHub Pages deployment
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
  // GitHub Pages configuration
  base: process.env.NODE_ENV === 'production' ? '/Turkish-Diaspora-App/' : '/',
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
