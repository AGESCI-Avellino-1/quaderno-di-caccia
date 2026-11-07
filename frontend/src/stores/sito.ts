/**
 * Title and footer of the site (DEC-246, DEC-247): read from /api/v1/sito, also before
 * the login; the device copy (encrypted, only once unlocked) keeps them offline.
 *
 * Maintenance (DEC-268) comes from the server only, never from the copy: a phone offline
 * at camp is not locked by a maintenance that may be over. Any answer "manutenzione"
 * (503) switches it on at once.
 */
import { defineStore } from 'pinia'
import { computed, ref } from 'vue'

import { osservaRisposte } from '@/api/http'
import { api, type Sito } from '@/api/qdc'
import { leggiConCache } from '@/offline/cache'
import { riempi, SITO_DI_BASE } from '@/sito/segnaposto'

export const CODICE_MANUTENZIONE = 'manutenzione'

export const useSitoStore = defineStore('sito', () => {
  const sito = ref<Sito>({ ...SITO_DI_BASE })
  /** The version the server has just said, never the one of a copy on the device (DEC-380). */
  const versioneServer = ref('')

  osservaRisposte((risposta, dati) => {
    const corpo = dati as { codice?: string; detail?: string } | null
    if (risposta.status === 503 && corpo?.codice === CODICE_MANUTENZIONE) {
      sito.value = {
        ...sito.value,
        manutenzione: true,
        messaggio_manutenzione: corpo.detail ?? '',
      }
    }
  })
  /** The name of the page shown, for [Pagina corrente]; set by the router and views. */
  const pagina = ref('')

  async function carica() {
    try {
      const letto = await leggiConCache('sito', () => api.sito())
      versioneServer.value = letto.copiaDel ? '' : (letto.dati.versione ?? '')
      sito.value = letto.copiaDel
        ? { ...letto.dati, manutenzione: false, messaggio_manutenzione: '' }
        : letto.dati
    } catch {
      // Offline before unlocking, or no copy yet: the defaults.
    }
  }

  // An app left open for days asks again when it comes back in front (DEC-380).
  document.addEventListener('visibilitychange', () => {
    if (document.visibilityState === 'visible' && navigator.onLine) void carica()
  })

  function aggiorna(nuovo: Sito) {
    sito.value = nuovo
  }

  const titoloCompleto = computed(
    () => riempi(sito.value.titolo_completo, sito.value, pagina.value) || sito.value.nome_sito,
  )
  const titoloBreve = computed(
    () => riempi(sito.value.titolo_breve, sito.value, pagina.value) || sito.value.nome_sito,
  )
  const rigaPiede = computed(() => riempi(sito.value.riga_piede, sito.value, pagina.value))

  return { sito, versioneServer, pagina, carica, aggiorna, titoloCompleto, titoloBreve, rigaPiede }
})
