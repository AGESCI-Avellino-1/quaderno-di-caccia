/// <reference types="vite-plugin-pwa/vue" />
/**
 * Updating the app. The service worker is in "prompt" mode: a new version is installed only
 * when the user agrees, so nobody loses a half-filled form at camp. `aggiornaOra` is the
 * Aggiorna button of the footer (DEC-380): the browser checks at once, instead of at its own
 * pace, and the app reloads; it starts only from a touch.
 */
import { useRegisterSW } from 'virtual:pwa-register/vue'
import { watch } from 'vue'

const ATTESA_MS = 30_000

let registrazione: ServiceWorkerRegistration | undefined

export const { needRefresh, updateServiceWorker } = useRegisterSW({
  onRegisteredSW(_indirizzo, trovata) {
    registrazione = trovata
  },
})

/** Is `locale` earlier than `server`? Both X.Y.Z; anything else is no reason to update. */
export function versioneInferiore(locale: string, server: string): boolean {
  const FORMA = /^\d+\.\d+\.\d+$/
  if (!FORMA.test(locale) || !FORMA.test(server)) return false
  const a = locale.split('.').map(Number)
  const b = server.split('.').map(Number)
  for (let i = 0; i < 3; i++) {
    if (a[i] !== b[i]) return a[i]! < b[i]!
  }
  return false
}

/** Until the new version is installed, or the time is up. */
function attendiNuovaVersione(): Promise<void> {
  return new Promise((risolvi) => {
    const fine = () => {
      clearTimeout(limite)
      smetti()
      risolvi()
    }
    const limite = setTimeout(fine, ATTESA_MS)
    const smetti = watch(needRefresh, (pronta) => {
      if (pronta) fine()
    })
  })
}

export async function aggiornaOra(): Promise<void> {
  // A version already waiting, even if someone answered «Più tardi».
  let pronta = needRefresh.value || !!registrazione?.waiting
  if (!pronta && registrazione) {
    const attesa = attendiNuovaVersione()
    try {
      await registrazione.update()
      await attesa
    } catch {
      // No network or no answer: the reload below is still the best there is.
    }
    pronta = needRefresh.value || !!registrazione.waiting
  }
  // The new service worker takes over and the page reloads by itself.
  if (pronta) await updateServiceWorker(true)
  else window.location.reload()
}
