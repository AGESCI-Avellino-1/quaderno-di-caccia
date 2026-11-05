/**
 * The images of the animals the patrols use stay on the device (DEC-353), not the whole list.
 * They are not personal data, so they do not go through the encrypted copy: the service
 * worker keeps them in this cache (`runtimeCaching` in vite.config.ts), like the app's files.
 */
import { api } from '@/api/qdc'
import { inImpersonazione } from '@/sicurezza/impersonazione'

export const CACHE_ANIMALI = 'qdc-animali'

export async function scaricaAnimaliInUso(): Promise<void> {
  if (typeof caches === 'undefined' || !navigator.onLine || inImpersonazione()) return
  try {
    const percorsi = await api.animaliInUso()
    const cache = await caches.open(CACHE_ANIMALI)
    const presenti = new Set((await cache.keys()).map((r) => new URL(r.url).pathname))
    // One missing image must not stop the others: it comes back at the next start.
    await Promise.allSettled(percorsi.filter((p) => !presenti.has(p)).map((p) => cache.add(p)))
  } catch {
    // Without the network or the storage the name stays, without its image.
  }
}
