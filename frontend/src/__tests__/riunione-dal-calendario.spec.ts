import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { createMemoryHistory, createRouter } from 'vue-router'

import type { Profilo } from '@/api/qdc'
import { useSessioneStore } from '@/stores/sessione'
import RiunioniView from '@/views/RiunioniView.vue'

import { nuovoDatabase, risposta } from './aiuti'

// From the calendar's «+» (DEC-412): a meeting on that day, also when made a series.
afterEach(() => vi.unstubAllGlobals())

describe('meeting from the calendar', () => {
  it('turned into a series, it starts on the chosen day and weekday', async () => {
    await nuovoDatabase()
    setActivePinia(createPinia())
    useSessioneStore().profilo = {
      capo: false,
      capogruppo: false,
      squadriglie_guidate: [],
      squadriglie_delegate: [3],
      squadriglie: [],
    } as unknown as Profilo
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => risposta(200, [])),
    )
    const Vuota = { template: '<div />' }
    const router = createRouter({
      history: createMemoryHistory(),
      routes: [
        { path: '/riunioni', component: RiunioniView },
        { path: '/', component: Vuota },
      ],
    })
    await router.push('/riunioni?giorno=2026-11-20') // a Friday
    const pagina = mount(RiunioniView, { global: { plugins: [router] } })
    await flushPromises()
    expect((pagina.get('#riu-una').element as HTMLInputElement).checked).toBe(true)
    await pagina.get('#riu-ripeti').setValue(true)
    await flushPromises()
    expect((pagina.get('#riu-giorno').element as HTMLSelectElement).value).toBe('4')
    expect((pagina.get('#riu-dal').element as HTMLInputElement).value).toBe('2026-11-20')
  })
})
