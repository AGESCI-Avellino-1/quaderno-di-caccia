import { cp, readFile, rm } from 'node:fs/promises'
import { isAbsolute, join } from 'node:path'
import { fileURLToPath, URL } from 'node:url'

import vue from '@vitejs/plugin-vue'
import { defineConfig, type Plugin } from 'vite'
import { VitePWA } from 'vite-plugin-pwa'

import { escapeHtml, generaAvvio, immaginiAvvio } from './scripts/avvio'
import { generaIcone, LOGO_AGESCI, RADICE } from './scripts/icone'

// Paths served by Django. In dev Vite proxies them, so the PWA and the API share the
// same origin (session cookie + CSRF, no CORS). In production nginx does the same.
const DJANGO_PATHS = ['/api', '/_allauth', '/accounts', '/admin', '/static', '/mailpit']
const DJANGO_URL = process.env.QDC_DJANGO_URL ?? 'http://localhost:8000'

/**
 * The group's own logo (DEC-294): `QDC_LOGO` in `.env`, a path from the repository root
 * (e.g. `resources/logo-gruppo.svg`). Its icons go into a copy of `public/`, so the files
 * in git keep the AGESCI ones. The images of the start screen (DEC-332) go there too, at
 * every build; in development there are none and `public/` stays as it is.
 */
async function cartellaPubblica(costruzione: boolean): Promise<string> {
  const logo = process.env.QDC_LOGO?.trim()
  if (!logo && !costruzione) return 'public'
  const percorso = !logo ? LOGO_AGESCI : isAbsolute(logo) ? logo : join(RADICE, logo)
  const contenuto = await readFile(percorso).catch(() => {
    throw new Error(`Il logo indicato in QDC_LOGO non c'è: ${percorso}`)
  })
  const copia = fileURLToPath(new URL('./node_modules/.qdc-public', import.meta.url))
  await rm(copia, { recursive: true, force: true })
  await cp(fileURLToPath(new URL('./public', import.meta.url)), copia, { recursive: true })
  if (logo) await generaIcone(contenuto, copia)
  if (costruzione) await generaAvvio(contenuto, nomeGruppoAvvio(), copia)
  return copia
}

/** Under the app's name on the start screen: fixed at build, as the logo (DEC-332). */
function nomeGruppoAvvio(): string {
  return process.env.QDC_NOME_AVVIO?.trim() ?? ''
}

/** The group's name in the page shown while the app loads, and at build the iPhone's images. */
function paginaDiAvvio(costruzione: boolean): Plugin {
  return {
    name: 'qdc-pagina-di-avvio',
    transformIndexHtml(html) {
      const nome = nomeGruppoAvvio()
      return {
        html: html.replace(
          '<!-- qdc-gruppo-avvio -->',
          nome ? `<div class="avvio-gruppo">${escapeHtml(nome)}</div>` : '',
        ),
        tags: costruzione
          ? immaginiAvvio().map((i) => ({
              tag: 'link',
              attrs: { rel: 'apple-touch-startup-image', media: i.media, href: `/${i.file}` },
              injectTo: 'head' as const,
            }))
          : [],
      }
    },
  }
}

export default defineConfig(async ({ command }) => ({
  publicDir: await cartellaPubblica(command === 'build'),
  plugins: [
    vue(),
    paginaDiAvvio(command === 'build'),
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
        // One device needs one image, and iOS keeps it by itself: not worth two more MB each.
        globIgnores: ['avvio/**'],
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
}))
