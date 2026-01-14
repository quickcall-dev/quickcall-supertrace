/**
 * Vite config for QuickCall SuperTrace frontend.
 *
 * Configures React, Tailwind, and API proxy to backend server.
 *
 * Related: src/main.tsx (entry), tailwind.config.js
 */

import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    port: 2255,
    proxy: {
      '/api': {
        target: 'http://localhost:7845',
        changeOrigin: true,
      },
      '/ws': {
        target: 'ws://localhost:7845',
        ws: true,
      },
    },
  },
})
