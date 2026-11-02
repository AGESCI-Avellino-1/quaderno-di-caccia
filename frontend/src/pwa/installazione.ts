/**
 * The banner suggesting to install the app (DEC-283), wherever the PWA can be installed.
 *
 * Chromium browsers (Chrome, Edge, Samsung Internet) fire `beforeinstallprompt` when the
 * app can be installed and not yet installed: the banner then has an "Installa" button.
 * Nothing fires elsewhere, so the banner gives the steps where installing is possible:
 * iPhone and iPad (any browser: all are WebKit and share to the Home screen), Safari on
 * the Mac (Add to Dock), Firefox on Android. Never once the app runs from its icon.
 *
 * Closing it is remembered in the browser, only the date, like the cookie notice
 * (DEC-266): after the days set by the server (`QDC_BANNER_INSTALLAZIONE_GIORNI`) the
 * banner may show again.
 */
import { ref } from 'vue'

export type ModoInstallazione = 'pulsante' | 'ios' | 'mac' | 'firefox-android'

/** Not in the DOM typings: Chromium only. */
interface EventoInstallazione extends Event {
  prompt(): Promise<void>
  userChoice: Promise<{ outcome: 'accepted' | 'dismissed' }>
}

export const CHIAVE_CHIUSURA = 'qdc-installazione-chiusa'
const GIORNO_MS = 24 * 60 * 60 * 1000

/** How the app can be installed in this browser; null: it cannot, or it already is. */
export function modoInstallazione(
  userAgent: string,
  puntiTocco: number,
  { installata, pulsante }: { installata: boolean; pulsante: boolean },
): ModoInstallazione | null {
  if (installata) return null
  if (pulsante) return 'pulsante'
  // iPadOS presents itself as a Mac, but with a touch screen.
  if (/iPhone|iPad|iPod/.test(userAgent) || (/Macintosh/.test(userAgent) && puntiTocco > 1)) {
    return 'ios'
  }
  if (/Android/.test(userAgent)) return /Firefox\//.test(userAgent) ? 'firefox-android' : null
  if (/Macintosh/.test(userAgent) && /Version\/[\d.]+ Safari\//.test(userAgent)) {
    return /Chrome|Chromium|Edg|Firefox|OPR/.test(userAgent) ? null : 'mac'
  }
  return null
}

/** Whether a banner closed on `chiusaIl` (ISO date, or nothing) may show again. */
export function ricompare(chiusaIl: string | null, giorni: number, adesso = Date.now()): boolean {
  if (!chiusaIl) return true
  const quando = Date.parse(chiusaIl)
  if (Number.isNaN(quando)) return true
  return adesso - quando >= giorni * GIORNO_MS
}

export function leggiChiusura(): string | null {
  try {
    return localStorage.getItem(CHIAVE_CHIUSURA)
  } catch {
    return null
  }
}

export function salvaChiusura(adesso = new Date()): void {
  try {
    localStorage.setItem(CHIAVE_CHIUSURA, adesso.toISOString())
  } catch {
    // Private browsing: it shows again next time.
  }
}

export function appInstallata(): boolean {
  const ios = (navigator as Navigator & { standalone?: boolean }).standalone === true
  return ios || window.matchMedia?.('(display-mode: standalone)').matches === true
}

// Listened to from the first import: Chromium may fire it before the banner is mounted.
let evento: EventoInstallazione | null = null
export const pulsanteDisponibile = ref(false)
export const installata = ref(false)

window.addEventListener('beforeinstallprompt', (e) => {
  // Our banner instead of the browser's own mini-infobar.
  e.preventDefault()
  evento = e as EventoInstallazione
  pulsanteDisponibile.value = true
})
window.addEventListener('appinstalled', () => {
  evento = null
  pulsanteDisponibile.value = false
  installata.value = true
})

/** Opens the browser's own install dialog; true if the user installed the app. */
export async function installa(): Promise<boolean> {
  if (!evento) return false
  const daUsare = evento
  // The event can prompt once only.
  evento = null
  pulsanteDisponibile.value = false
  await daUsare.prompt()
  const { outcome } = await daUsare.userChoice
  if (outcome === 'accepted') installata.value = true
  return outcome === 'accepted'
}
