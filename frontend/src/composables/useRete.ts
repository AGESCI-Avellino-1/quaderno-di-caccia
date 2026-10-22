/** Reactive online/offline state; sends the offline queue when the network returns. */
import { liveQuery } from 'dexie'
import { onScopeDispose, ref } from 'vue'

import { db } from '@/offline/db'
import { inviaCoda } from '@/offline/outbox'

const online = ref(typeof navigator === 'undefined' ? true : navigator.onLine)
const inCoda = ref(0)
const conErrori = ref(0)
let avviato = false

function avvia() {
  if (avviato) return
  avviato = true
  window.addEventListener('online', () => {
    online.value = true
    void inviaCoda()
  })
  window.addEventListener('offline', () => {
    online.value = false
  })
  liveQuery(() => db.coda.where('stato').equals('in_attesa').count()).subscribe((n) => {
    inCoda.value = n
  })
  liveQuery(() => db.coda.where('stato').equals('errore').count()).subscribe((n) => {
    conErrori.value = n
  })
  if (online.value) void inviaCoda()
}

export function useRete() {
  avvia()
  const timer = window.setInterval(() => {
    if (online.value && inCoda.value > 0) void inviaCoda()
  }, 60_000)
  onScopeDispose(() => window.clearInterval(timer))
  return { online, inCoda, conErrori, invia: inviaCoda }
}
