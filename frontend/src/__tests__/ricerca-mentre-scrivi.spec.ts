import { flushPromises, mount } from '@vue/test-utils'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { defineComponent, nextTick, ref } from 'vue'

import { useRicercaMentreScrivi } from '@/composables/useRicercaMentreScrivi'
import BuonaCacciaView from '@/views/BuonaCacciaView.vue'

// Search while writing (DEC-397).
function prova(cerca: (testo: string) => Promise<string[] | undefined>, minimo?: number) {
  const testo = ref('')
  let risultato!: ReturnType<typeof useRicercaMentreScrivi<string[]>>
  mount(
    defineComponent({
      setup() {
        risultato = useRicercaMentreScrivi(testo, cerca, minimo === undefined ? {} : { minimo })
        return () => null
      },
    }),
  )
  return { testo, ...risultato }
}

afterEach(() => {
  vi.useRealTimers()
  vi.unstubAllGlobals()
})

describe('ricerca mentre si scrive', () => {
  it('searches after a pause, from two letters, once per pause', async () => {
    vi.useFakeTimers()
    const cerca = vi.fn(async (t: string) => [t])
    const { testo, trovati } = prova(cerca)
    testo.value = 'r'
    await nextTick()
    await vi.advanceTimersByTimeAsync(500)
    expect(cerca).not.toHaveBeenCalled()
    expect(trovati.value).toBeNull()

    testo.value = 'ro'
    await nextTick()
    testo.value = 'ros '
    await nextTick()
    await vi.advanceTimersByTimeAsync(100)
    expect(cerca).not.toHaveBeenCalled()
    await vi.advanceTimersByTimeAsync(300)
    expect(cerca).toHaveBeenCalledExactlyOnceWith('ros')
    expect(trovati.value).toEqual(['ros'])

    testo.value = 'r'
    await nextTick()
    await vi.advanceTimersByTimeAsync(300)
    expect(trovati.value).toBeNull()
  })

  it('drops an answer that arrives after a newer search', async () => {
    const attese: Record<string, (r: string[]) => void> = {}
    const cerca = (t: string) => new Promise<string[]>((fatto) => (attese[t] = fatto))
    const { testo, trovati, subito } = prova(cerca)
    testo.value = 'ros'
    void subito()
    testo.value = 'rossi'
    void subito()
    attese.rossi!(['nuova'])
    await flushPromises()
    attese.ros!(['vecchia'])
    await flushPromises()
    expect(trovati.value).toEqual(['nuova'])
  })

  it('keeps the last results when a request fails, and with no minimum searches empty', async () => {
    let fallisce = false
    const cerca = vi.fn(async (t: string) => (fallisce ? undefined : [`tutti${t}`]))
    const { testo, trovati, subito } = prova(cerca, 0)
    await subito()
    expect(trovati.value).toEqual(['tutti'])
    fallisce = true
    testo.value = 'x'
    await subito()
    expect(trovati.value).toEqual(['tutti'])
  })

  it('finds BuonaCaccia events without a button, and offers to add one', async () => {
    vi.useFakeTimers()
    const chiamate: string[] = []
    vi.stubGlobal(
      'fetch',
      vi.fn(async (url: string) => {
        chiamate.push(url)
        const dati = url.includes('cerca=')
          ? [
              {
                id: 7,
                titolo: 'Capi Squadriglia - Zona Hirpinia',
                inizio: '2026-12-04T00:00:00+01:00',
                fine: '2026-12-06T23:59:00+01:00',
                luogo: 'Atripalda',
                formazione_capi: false,
                piccole_orme: false,
              },
            ]
          : []
        return new Response(JSON.stringify(dati), {
          headers: { 'Content-Type': 'application/json' },
        })
      }),
    )
    const { setActivePinia, createPinia } = await import('pinia')
    setActivePinia(createPinia())
    const { useSessioneStore } = await import('@/stores/sessione')
    const sessione = useSessioneStore()
    sessione.profilo = { eventi_buonacaccia: true } as typeof sessione.profilo
    const vista = mount(BuonaCacciaView, {
      global: { stubs: { RouterLink: { template: '<a><slot /></a>' } } },
    })
    expect(vista.find('form[role="search"] button').exists()).toBe(false)
    expect(vista.text()).not.toContain("Non c'è: aggiungilo")
    await vista.get('#cerca-bc').setValue('capi squ')
    expect(vista.text()).toContain("Non c'è: aggiungilo")
    await vi.advanceTimersByTimeAsync(300)
    await flushPromises()
    expect(chiamate.at(-1)).toBe('/api/v1/buonacaccia/eventi?cerca=capi%20squ')
    expect(vista.text()).toContain('Capi Squadriglia - Zona Hirpinia')
  })
})
