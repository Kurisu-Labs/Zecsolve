import { fileURLToPath, URL } from 'node:url'
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import tailwindcss from '@tailwindcss/vite'

// Same-origin in production (FastAPI serves dist/); Vite proxies the API in development.
export default defineConfig({
  plugins: [vue(), tailwindcss()],
  resolve: {
    alias: { '@': fileURLToPath(new URL('./src', import.meta.url)) },
  },
  server: {
    port: 5173,
    proxy: {
      '/api': 'http://127.0.0.1:8000',
      '/health': 'http://127.0.0.1:8000',
    },
  },
  build: {
    target: 'es2022',
    rollupOptions: {
      output: {
        // Keep WebGL and scroll libraries out of the app's critical path.
        manualChunks: { three: ['three'], motion: ['gsap', 'lenis'] },
      },
    },
  },
})
