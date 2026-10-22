/**
 * Locks the vault after a few minutes without use, or when the app comes back after
 * being in the background for that long (DEC-97).
 */
import { onScopeDispose } from 'vue'
import { useRouter } from 'vue-router'

import { blocca, stato } from '@/sicurezza/cassaforte'

export const MINUTI_BLOCCO = 5

export function useBloccoAutomatico() {
  const router = useRouter()
  let ultimaAttivita = Date.now()

  const segna = () => {
    ultimaAttivita = Date.now()
  }
  const controlla = () => {
    if (stato.value !== 'sbloccata') return
    if (Date.now() - ultimaAttivita < MINUTI_BLOCCO * 60_000) return
    blocca()
    void router.push({ name: 'sblocco', query: { prossima: router.currentRoute.value.fullPath } })
  }
  const visibilita = () => {
    if (document.visibilityState === 'visible') controlla()
  }

  const eventi = ['pointerdown', 'keydown', 'scroll'] as const
  for (const evento of eventi) window.addEventListener(evento, segna, { passive: true })
  document.addEventListener('visibilitychange', visibilita)
  const timer = window.setInterval(controlla, 15_000)

  onScopeDispose(() => {
    for (const evento of eventi) window.removeEventListener(evento, segna)
    document.removeEventListener('visibilitychange', visibilita)
    window.clearInterval(timer)
  })
}
