/**
 * What the menu and the breadcrumb need beyond the profile (DEC-241, DEC-244): the
 * names of pages that have one of their own (a person, a unit, an event), and the
 * counters read online. Nothing here is saved on the device.
 */
import { defineStore } from 'pinia'
import { ref } from 'vue'

import { api } from '@/api/qdc'
import type { Contatori } from '@/navigazione/menu'

export const useNavigazioneStore = defineStore('navigazione', () => {
  /** Name of a page by its path, e.g. '/persone/12' → 'Giulia Rossi'. */
  const nomi = ref<Record<string, string>>({})
  const contatori = ref<Contatori>({})

  function nomina(percorso: string, nome: string) {
    nomi.value = { ...nomi.value, [percorso]: nome }
  }

  /** Corrections waiting to be forwarded (capigruppo, technical administrator). */
  async function caricaContatori(gestisceCorrezioni: boolean) {
    if (!gestisceCorrezioni || !navigator.onLine) return
    try {
      const correzioni = (await api.correzioni()).filter((c) => c.stato === 'IN_ATTESA').length
      contatori.value = { ...contatori.value, correzioni }
    } catch {
      contatori.value = { ...contatori.value, correzioni: null }
    }
  }

  return { nomi, contatori, nomina, caricaContatori }
})
