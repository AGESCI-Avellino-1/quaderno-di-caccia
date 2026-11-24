/**
 * Long pages in groups that open and close (DEC-426): the main group open at first, one open at a
 * time, the open one kept in the address (`?gruppo=`) so «Indietro» finds it again and a link can
 * open one. The page calls `useGruppiPagina` with its groups shown, the first being the main one;
 * each `GruppoPagina` inside reads the state it provides.
 */
import { computed, inject, provide, type ComputedRef, type InjectionKey, type Ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

export interface GruppiPagina {
  /** The `name` of the `<details>`: the browser keeps one open at a time. */
  nome: string
  aperto: Ref<string | null> | ComputedRef<string | null>
  apri: (chiave: string | null) => void
}

export const CHIAVE_GRUPPI: InjectionKey<GruppiPagina> = Symbol('gruppi-pagina')
/** In the address when the person closed every group. */
const NESSUNO = 'nessuno'

export function useGruppiPagina(nome: string, chiavi: () => string[]): GruppiPagina {
  const route = useRoute()
  const router = useRouter()
  const aperto = computed<string | null>(() => {
    const scelto = route?.query.gruppo
    if (scelto === NESSUNO) return null
    if (typeof scelto === 'string' && chiavi().includes(scelto)) return scelto
    return chiavi()[0] ?? null
  })
  function apri(chiave: string | null) {
    if (chiave === aperto.value || !router) return
    const principale = chiavi()[0] ?? null
    const gruppo = chiave === principale ? undefined : (chiave ?? NESSUNO)
    router.replace({ query: { ...route.query, gruppo } })
  }
  const gruppi = { nome, aperto, apri }
  provide(CHIAVE_GRUPPI, gruppi)
  return gruppi
}

export function useGruppo(): GruppiPagina | undefined {
  return inject(CHIAVE_GRUPPI, undefined)
}
