import { fileURLToPath, URL } from 'node:url'

import vue from '@vitejs/plugin-vue'
import { defineConfig } from 'vite'
import { VitePWA } from 'vite-plugin-pwa'

// Paths served by Django. In dev Vite proxies them, so the PWA and the API share the
// same origin (session cookie + CSRF, no CORS). In production nginx does the same.
const DJANGO_PATHS = ['/api', '/_allauth', '/accounts', '/admin', '/static', '/mailpit']
const DJANGO_URL = process.env.QDC_DJANGO_URL ?? 'http://localhost:8000'

export default defineConfig({
  plugins: [
    vue(),
    VitePWA({
      registerType: 'prompt',
      injectRegister: false,
      includeAssets: ['favicon-16x16.png', 'favicon-32x32.png', 'apple-touch-icon.png'],
      manifest: {
        name: 'Quaderno di Caccia',
        short_name: 'QdC',
        description: 'Anagrafica, quote e Progressione Personale del Gruppo',
        lang: 'it',
        theme_color: '#6689cc',
        background_color: '#ffffff',
        display: 'standalone',
        start_url: '/',
        icons: [
          { src: 'icons/icon-192.png', sizes: '192x192', type: 'image/png' },
          { src: 'icons/icon-512.png', sizes: '512x512', type: 'image/png' },
          {
            src: 'icons/icon-512-maskable.png',
            sizes: '512x512',
            type: 'image/png',
            purpose: 'maskable',
          },
        ],
      },
      workbox: {
        // The service worker caches the app shell only. Data for offline use lives in
        // IndexedDB (src/offline), never in the HTTP cache.
        globPatterns: ['**/*.{js,css,html,png,svg,woff2}'],
        navigateFallback: '/index.html',
        navigateFallbackDenylist: DJANGO_PATHS.map((p) => new RegExp(`^${p}`)),
      },
    }),
  ],
  resolve: {
    alias: { '@': fileURLToPath(new URL('./src', import.meta.url)) },
  },
  server: {
    port: 5173,
    proxy: Object.fromEntries(DJANGO_PATHS.map((p) => [p, { target: DJANGO_URL }])),
  },
})
