/**
 * Title and footer of the site (DEC-246, DEC-247): read from /api/v1/sito, also before
 * the login; the device copy (encrypted, only once unlocked) keeps them offline.
 */
import { defineStore } from 'pinia'
import { computed, ref } from 'vue'

import { api, type Sito } from '@/api/qdc'
import { leggiConCache } from '@/offline/cache'
import { riempi, SITO_DI_BASE } from '@/sito/segnaposto'

export const useSitoStore = defineStore('sito', () => {
  const sito = ref<Sito>({ ...SITO_DI_BASE })
  /** The name of the page shown, for [Pagina corrente]; set by the router and views. */
  const pagina = ref('')

  async function carica() {
    try {
      sito.value = (await leggiConCache('sito', () => api.sito())).dati
    } catch {
      // Offline before unlocking, or no copy yet: the defaults.
    }
  }

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

  return { sito, pagina, carica, aggiorna, titoloCompleto, titoloBreve, rigaPiede }
})
