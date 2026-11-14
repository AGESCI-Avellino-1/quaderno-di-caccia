/**
 * The page of a tapped notification, with the app already open (#74). The service worker no
 * longer moves the window with `WindowClient.navigate()`, which fails on a window it does not
 * control (after an update, in prompt mode) and on some iPhones: it sends the page here. The
 * router guard does the rest: locked, the page becomes the one after unlocking.
 */
import type { Router } from 'vue-router'

export const MESSAGGIO_APRI = 'qdc-apri'

/** Only a path of the app: never another site, nor `//host`. */
export function percorsoInterno(valore: unknown): string | null {
  if (typeof valore !== 'string' || !valore.startsWith('/')) return null
  if (valore.startsWith('//') || valore.startsWith('/\\')) return null
  return valore
}

export async function apri(router: Router, percorso: string): Promise<void> {
  // On the unlock page the guard sends back to it with the page as the one after: replace,
  // so going back does not land on the PIN again.
  if (router.currentRoute.value.name === 'sblocco') await router.replace(percorso)
  else await router.push(percorso)
}

export function ascoltaAperture(router: Router): void {
  if (typeof navigator === 'undefined' || !('serviceWorker' in navigator)) return
  navigator.serviceWorker.addEventListener('message', (evento: MessageEvent) => {
    if (evento.data?.tipo !== MESSAGGIO_APRI) return
    const percorso = percorsoInterno(evento.data.percorso)
    if (percorso) void apri(router, percorso)
  })
}
