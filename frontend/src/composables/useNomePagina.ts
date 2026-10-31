import { getActivePinia } from 'pinia'
import { watchEffect, type MaybeRefOrGetter, toValue } from 'vue'
import { useRoute } from 'vue-router'

import { useNavigazioneStore } from '@/stores/navigazione'
import { useSitoStore } from '@/stores/sito'

/**
 * A page with a name of its own (a person, a unit, an event): the title's
 * [Pagina corrente] and the breadcrumb use it instead of the generic name (DEC-244).
 */
export function useNomePagina(nome: MaybeRefOrGetter<string | null | undefined>) {
  const rotta = useRoute()
  // A view mounted on its own (unit tests) has no router and no store: nothing to name.
  if (!rotta || !getActivePinia()) return
  const sito = useSitoStore()
  const navigazione = useNavigazioneStore()
  const percorso = rotta.path
  watchEffect(() => {
    const valore = toValue(nome)
    if (!valore) return
    navigazione.nomina(percorso, valore)
    if (rotta.path === percorso) sito.pagina = valore
  })
}

/**
 * A person's subpage (scheda sanitaria, fascicolo…) knows the person's name: the
 * breadcrumb shows it on the person's crumb instead of the generic "Scheda".
 */
export function useNomePersona(
  id: MaybeRefOrGetter<number>,
  nome: MaybeRefOrGetter<string | null | undefined>,
) {
  if (!getActivePinia()) return
  const navigazione = useNavigazioneStore()
  watchEffect(() => {
    const valore = toValue(nome)
    if (valore) navigazione.nomina(`/persone/${toValue(id)}`, valore)
  })
}
