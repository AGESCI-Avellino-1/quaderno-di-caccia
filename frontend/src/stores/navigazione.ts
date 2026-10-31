/**
 * What the menu and the breadcrumb need beyond the profile (DEC-241, DEC-244): the
 * names of pages that have one of their own (a person, a unit, an event), and the
 * counters read online. Nothing here is saved on the device.
 */
import { defineStore } from 'pinia'
import { computed, ref } from 'vue'

import { api } from '@/api/qdc'
import type { Contatori } from '@/navigazione/menu'

import { useSitoStore } from './sito'

export const useNavigazioneStore = defineStore('navigazione', () => {
  /** Name of a page by its path, e.g. '/persone/12' → 'Giulia Rossi'. */
  const nomi = ref<Record<string, string>>({})
  const letti = ref<Contatori>({})
  const sito = useSitoStore()
  const contatori = computed<Contatori>(() => ({
    ...letti.value,
    email_di_prova: !!sito.sito.email_di_prova,
  }))

  function nomina(percorso: string, nome: string) {
    nomi.value = { ...nomi.value, [percorso]: nome }
  }

  /** Corrections waiting to be forwarded (capigruppo, technical administrator). */
  async function caricaContatori(gestisceCorrezioni: boolean) {
    if (!gestisceCorrezioni || !navigator.onLine) return
    try {
      const correzioni = (await api.correzioni()).filter((c) => c.stato === 'IN_ATTESA').length
      letti.value = { ...letti.value, correzioni }
    } catch {
      letti.value = { ...letti.value, correzioni: null }
    }
  }

  return { nomi, contatori, nomina, caricaContatori }
})
