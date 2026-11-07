/** Searching on the server while one writes (DEC-397), instead of a Cerca button. */
import { onScopeDispose, shallowRef, watch, type Ref } from 'vue'

/**
 * Asks `cerca` after a short pause in the writing, once `testo` has at least `minimo`
 * characters; below that the results go back to null. An answer arriving after a newer
 * search started is dropped, and an undefined answer (a failed request) keeps the last
 * results. `subito` searches at once, for Enter.
 */
export function useRicercaMentreScrivi<T>(
  testo: Ref<string>,
  cerca: (testo: string) => Promise<T | undefined>,
  { minimo = 2, pausa = 300 }: { minimo?: number; pausa?: number } = {},
) {
  const trovati = shallowRef<T | null>(null)
  let timer: ReturnType<typeof setTimeout> | undefined
  let ultima = 0

  async function subito() {
    clearTimeout(timer)
    const scritto = testo.value.trim()
    const questa = ++ultima
    if (scritto.length < minimo) {
      trovati.value = null
      return
    }
    const risposta = await cerca(scritto)
    if (questa === ultima && risposta !== undefined) trovati.value = risposta
  }

  watch(testo, () => {
    clearTimeout(timer)
    timer = setTimeout(subito, pausa)
  })
  onScopeDispose(() => clearTimeout(timer))

  return { trovati, subito }
}
