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
import { readFileSync } from 'fs'

const pkg = JSON.parse(readFileSync('./package.json', 'utf-8'))

export default defineConfig({
  plugins: [react(), tailwindcss()],
  define: {
    __APP_VERSION__: JSON.stringify(pkg.version),
  },
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
