/**
 * Push notifications on this browser (DEC-345). The yes is the browser's; what the person wants
 * is on the server. On iPhone they exist only in the app added to the Home screen.
 */
import { api } from '@/api/qdc'

const CHIAVE_INVITO = 'qdc-invito-notifiche'
const GIORNI_INVITO = 30

export function notificheSupportate(): boolean {
  return (
    typeof window !== 'undefined' &&
    'serviceWorker' in navigator &&
    'PushManager' in window &&
    'Notification' in window
  )
}

export function permesso(): NotificationPermission | null {
  return notificheSupportate() ? Notification.permission : null
}

function chiaveInByte(chiave: string): Uint8Array<ArrayBuffer> {
  const normale = chiave.replace(/-/g, '+').replace(/_/g, '/')
  const testo = atob(normale.padEnd(Math.ceil(normale.length / 4) * 4, '='))
  return Uint8Array.from(testo, (c) => c.charCodeAt(0))
}

function inBase64(dati: ArrayBuffer | null): string {
  if (!dati) return ''
  return btoa(String.fromCharCode(...new Uint8Array(dati)))
    .replace(/\+/g, '-')
    .replace(/\//g, '_')
    .replace(/=+$/, '')
}

async function iscrizioneDelBrowser(): Promise<PushSubscription | null> {
  if (!notificheSupportate()) return null
  const registrazione = await navigator.serviceWorker.getRegistration()
  return registrazione ? registrazione.pushManager.getSubscription() : null
}

/** Is this browser subscribed for the account in use? Its yes may outlive a session. */
export async function attiveQui(): Promise<boolean> {
  const iscrizione = await iscrizioneDelBrowser()
  if (!iscrizione) return false
  return (await api.statoPush(iscrizione.endpoint)).questo_browser
}

/** Only from a tap: the browsers refuse the permission asked for by itself. */
export async function attiva(chiavePubblica: string): Promise<boolean> {
  if ((await Notification.requestPermission()) !== 'granted') return false
  const registrazione = await navigator.serviceWorker.ready
  const iscrizione =
    (await registrazione.pushManager.getSubscription()) ??
    (await registrazione.pushManager.subscribe({
      userVisibleOnly: true,
      applicationServerKey: chiaveInByte(chiavePubblica),
    }))
  await api.iscriviPush({
    endpoint: iscrizione.endpoint,
    p256dh: inBase64(iscrizione.getKey('p256dh')),
    auth: inBase64(iscrizione.getKey('auth')),
  })
  return true
}

export async function disattiva(): Promise<void> {
  const iscrizione = await iscrizioneDelBrowser()
  if (!iscrizione) return
  await api.togliPush(iscrizione.endpoint)
  await iscrizione.unsubscribe()
}

/** On logging out, before the session goes; the server would end it by itself anyway. */
export async function dimenticaIscrizione(): Promise<void> {
  try {
    await disattiva()
  } catch {
    // Offline or already gone: it ends with the session on the server.
  }
}

export function invitoChiuso(adesso = Date.now()): boolean {
  try {
    const chiuso = localStorage.getItem(CHIAVE_INVITO)
    return !!chiuso && adesso - Date.parse(chiuso) < GIORNI_INVITO * 24 * 60 * 60 * 1000
  } catch {
    return false
  }
}

export function chiudiInvito(adesso = new Date()): void {
  try {
    localStorage.setItem(CHIAVE_INVITO, adesso.toISOString())
  } catch {
    // Private browsing: it shows again next time.
  }
}
