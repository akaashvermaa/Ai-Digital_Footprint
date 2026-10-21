import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Everything uses 127.0.0.1 (IPv4) on purpose: on Windows "localhost" can resolve to IPv6 (::1)
// while the backend listens on IPv4, which made the app unreachable or the launcher hang.
// /api requests are forwarded to the FastAPI backend during development.
export default defineConfig({
  plugins: [react()],
  server: {
    host: '127.0.0.1',
    port: 5173,
    strictPort: true,
    proxy: {
      '/api': 'http://127.0.0.1:8000',
    },
  },
})
