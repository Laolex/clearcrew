import react from '@vitejs/plugin-react'
import path from 'node:path'
import { defineConfig } from 'vite'

// Built output is served by FastAPI (replay.py), so it lands inside the package.
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: { '@': path.resolve(__dirname, './src') },
  },
  build: {
    outDir: path.resolve(__dirname, '../src/clearcrew/static/dist'),
    emptyOutDir: true,
  },
  server: {
    port: 5173,
    // Dev server proxies the API to the running FastAPI app so the frontend can
    // be iterated on without rebuilding.
    proxy: {
      '/api': 'http://127.0.0.1:8000',
    },
  },
})
