import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'node:path'

export default defineConfig({
  plugins: [react()],
  resolve: { alias: { '@': path.resolve(__dirname, './src') } },
  // SPA 라우팅(/artifacts/12 등)에서 자산 경로가 깨지지 않도록 절대경로로 빌드
  base: '/',
  build: { outDir: 'dist', sourcemap: false, chunkSizeWarningLimit: 1200 },
  server: {
    port: 5173,
    proxy: { '/api': { target: 'http://127.0.0.1:8000', changeOrigin: true } },
  },
})
