/** Turns any failure into a sentence a capo (or a parent) can understand. */
import { ref } from 'vue'

import { messaggiAllauth } from '@/api/allauth'
import { ErroreApi } from '@/api/http'

export function testoErrore(errore: unknown): string {
  if (errore instanceof ErroreApi) {
    const allauth = messaggiAllauth(errore.dati)
    if (allauth.length) return allauth.join(' ')
    const dettaglio = (errore.dati as { detail?: unknown } | null)?.detail
    if (typeof dettaglio === 'string') return dettaglio
    if (errore.stato === 403) return 'Non hai i permessi per questa operazione.'
    if (errore.stato === 404) return 'Non trovato, oppure non visibile con il tuo profilo.'
    if (errore.stato === 429) return 'Troppi tentativi: riprova tra qualche minuto.'
    return `Errore del server (${errore.stato}).`
  }
  return 'Connessione assente: riprova quando sei online.'
}

export function useErrore() {
  const errore = ref<string | null>(null)
  const inCorso = ref(false)

  /** Runs `azione`, tracking progress and storing a readable error. */
  async function esegui<T>(azione: () => Promise<T>): Promise<T | undefined> {
    errore.value = null
    inCorso.value = true
    try {
      return await azione()
    } catch (e) {
      errore.value = testoErrore(e)
      return undefined
    } finally {
      inCorso.value = false
    }
  }

  return { errore, inCorso, esegui }
}
