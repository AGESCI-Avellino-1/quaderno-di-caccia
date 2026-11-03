/**
 * Phone numbers into the phone's contacts (DEC-302): the capi and the capo squadriglia
 * choose people and download a vCard file the phone offers to save. Online only: the
 * file comes from the server, with only the numbers they already see; it lands on the
 * device outside the PIN protection, so nothing but name and numbers goes in it.
 */
import { computed, ref } from 'vue'

import { api } from '@/api/qdc'
import { useErrore } from '@/composables/useErrore'
import { useRete } from '@/composables/useRete'
import { useSessioneStore } from '@/stores/sessione'

export function useRubrica() {
  const sessione = useSessioneStore()
  const { online } = useRete()
  const { errore, inCorso, esegui } = useErrore()
  const attiva = ref(false)
  const scelti = ref(new Set<number>())

  const disponibile = computed(
    () =>
      online.value &&
      !sessione.profilo?.impersonazione &&
      (sessione.capo || (sessione.profilo?.squadriglie_guidate?.length ?? 0) > 0),
  )

  function alterna(id: number) {
    const nuovi = new Set(scelti.value)
    if (nuovi.has(id)) nuovi.delete(id)
    else nuovi.add(id)
    scelti.value = nuovi
  }

  function chiudi() {
    attiva.value = false
    scelti.value = new Set()
  }

  async function scarica() {
    const testo = await esegui(() => api.rubrica([...scelti.value]))
    if (testo === undefined) return
    const link = document.createElement('a')
    link.href = URL.createObjectURL(new Blob([testo], { type: 'text/vcard' }))
    link.download = 'contatti.vcf'
    link.click()
    URL.revokeObjectURL(link.href)
    chiudi()
  }

  return { disponibile, attiva, scelti, alterna, chiudi, scarica, errore, inCorso }
}

export type Rubrica = ReturnType<typeof useRubrica>
