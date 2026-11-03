import { fileURLToPath } from 'node:url'

import { configDefaults, defineConfig, mergeConfig } from 'vitest/config'

import viteConfig from './vite.config'

export default defineConfig(async (env) =>
  mergeConfig(await viteConfig(env), {
    test: {
      environment: 'jsdom',
      globals: true,
      setupFiles: ['fake-indexeddb/auto'],
      exclude: [...configDefaults.exclude],
      root: fileURLToPath(new URL('./', import.meta.url)),
    },
  }),
)
