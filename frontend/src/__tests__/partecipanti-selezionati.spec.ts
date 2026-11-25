import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { createMemoryHistory, createRouter } from 'vue-router'

import type { Profilo } from '@/api/qdc'
import LegendaMiei from '@/components/LegendaMiei.vue'
import { useSessioneStore } from '@/stores/sessione'
import RiunioniView from '@/views/RiunioniView.vue'

import { nuovoDatabase, risposta } from './aiuti'

afterEach(() => vi.unstubAllGlobals())

describe('meeting of people chosen one by one', () => {
  it('wants a title, has the user chosen already and tells the invited', async () => {
    await nuovoDatabase()
    setActivePinia(createPinia())
    useSessioneStore().profilo = {
      capo: true,
      capogruppo: false,
      persona: { id: 1, nome: 'Anna', cognome: 'Bianchi' },
      squadriglie_guidate: [],
      squadriglie_delegate: [],
      squadriglie: [],
    } as unknown as Profilo
    const inviati: Record<string, unknown>[] = []
    vi.stubGlobal(
      'fetch',
      vi.fn(async (url: string, opzioni?: RequestInit) => {
        if (String(url).endsWith('/selezionabili'))
          return risposta(200, [
            { id: 1, nome: 'Anna', cognome: 'Bianchi', unita: 'Co.Ca.' },
            { id: 2, nome: 'Luca', cognome: 'Verdi', unita: 'Reparto' },
          ])
        if (opzioni?.method === 'POST') inviati.push(JSON.parse(String(opzioni.body)))
        return risposta(200, [])
      }),
    )
    const router = createRouter({
      history: createMemoryHistory(),
      routes: [
        { path: '/riunioni', component: RiunioniView },
        { path: '/', component: { template: '<div />' } },
      ],
    })
    await router.push('/riunioni?giorno=2026-11-27')
    const pagina = mount(RiunioniView, { global: { plugins: [router] } })
    await flushPromises()
    await pagina.get('#riu-per').setValue('scelti')
    await flushPromises()
    expect(pagina.get('#riu-titolo').attributes('required')).toBeDefined()
    expect((pagina.get('#riu-persone-1').element as HTMLInputElement).checked).toBe(true)
    await pagina.get('#riu-persone-cerca').setValue('verd')
    expect(pagina.find('#riu-persone-1').exists()).toBe(false)
    await pagina.get('#riu-persone-2').setValue(true)
    await pagina.get('#riu-titolo').setValue('Route')
    await pagina.get('#riu-inizio').setValue('20:30')
    await flushPromises()
    expect((pagina.get('#riu-fine').element as HTMLInputElement).value).toBe('22:30')
    expect((pagina.get('#riu-avvisa').element as HTMLInputElement).checked).toBe(true)
    await pagina.get('form').trigger('submit')
    await flushPromises()
    expect(inviati[0]).toMatchObject({
      cerchia: 'SCELTI',
      titolo: 'Route',
      persone: [1, 2],
      unita: [],
      avvisa: true,
    })
  })
})

describe('legend of one’s own events', () => {
  it('only where there are others too', () => {
    const legenda = (eventi: { mio?: boolean }[]) =>
      mount(LegendaMiei, { props: { eventi } }).text()
    expect(legenda([{ mio: true }, {}])).toBe('')
    expect(legenda([{ mio: false }])).toBe('')
    expect(legenda([{ mio: true }, { mio: false }])).not.toBe('')
  })
})
