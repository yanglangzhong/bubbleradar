import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  build: {
    rollupOptions: {
      output: {
        manualChunks(id) {
          if (id.includes('node_modules')) {
            const pkg = id.split('node_modules/').pop()?.split('/')[0] ?? ''

            if (
              pkg === 'react' ||
              pkg === 'react-dom' ||
              pkg === 'react-router' ||
              pkg === 'react-router-dom' ||
              pkg === '@remix-run' ||
              pkg === 'scheduler' ||
              pkg === 'use-sync-external-store' ||
              pkg === 'history'
            ) {
              return 'vendor-react'
            }

            if (pkg === 'echarts' || pkg === 'echarts-for-react' || pkg === 'zrender') {
              return 'vendor-charts'
            }

            if (
              pkg === 'i18next' ||
              pkg === 'react-i18next' ||
              pkg === 'i18next-browser-languagedetector'
            ) {
              return 'vendor-i18n'
            }

            if (pkg === 'lucide-react') {
              return 'vendor-icons'
            }

            if (pkg === 'axios' || pkg === 'zustand') {
              return 'vendor-state'
            }

            return 'vendor-common'
          }
        },
      },
    },
    chunkSizeWarningLimit: 600,
  },
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
})
