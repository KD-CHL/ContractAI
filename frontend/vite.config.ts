import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { resolve } from 'path'

export default defineConfig({
  plugins: [vue()],
  base: '/',
  build: {
    outDir: 'dist',
    assetsDir: 'assets',
  },
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8010',
        changeOrigin: true,
      },
      '/health': {
        target: 'http://127.0.0.1:8010',
        changeOrigin: true,
      },
      '/live': {
        target: 'http://127.0.0.1:8010',
        changeOrigin: true,
      },
      '/ready': {
        target: 'http://127.0.0.1:8010',
        changeOrigin: true,
      },
    },
  },
  resolve: {
    alias: {
      '@': resolve(__dirname, './src'),
    },
  },
})
