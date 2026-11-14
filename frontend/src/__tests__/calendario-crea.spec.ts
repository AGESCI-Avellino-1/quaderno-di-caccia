import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { createMemoryHistory, createRouter } from 'vue-router'

import type { Profilo } from '@/api/qdc'
import { giornoDaQuery } from '@/eventi/creazione'
import { useSessioneStore } from '@/stores/sessione'
import CalendarioView from '@/views/CalendarioView.vue'

import { risposta } from './aiuti'

// The calendar's «+» to create a meeting or an event on a day (DEC-412).
const BASE = {
  email: 'x@example.invalid',
  persona: { id: 1, nome: 'Mario', cognome: 'Rossi' },
  branca: 'capi',
  capo: false,
  capogruppo: false,
  tesoriere: false,
  amministratore_tecnico: false,
  squadriglie_guidate: [],
  squadriglie: [],
  mie_iscrizioni: 0,
  iscrizioni_da_decidere: 0,
  capo_in_attesa: false,
  tutelati: [],
  gestisce_quote: false,
  unita_quote: [],
  vede_cassa: false,
  squadriglie_delegate: [],
  eventi_buonacaccia: false,
  formazione_capi: false,
  puo_impersonare: false,
  impersonazione: null,
  imprese_reparto: null,
  unita_servizio: [],
  ambiente: null,
} as Profilo

async function monta(profilo: Partial<Profilo>) {
  setActivePinia(createPinia())
  useSessioneStore().profilo = { ...BASE, ...profilo }
  vi.stubGlobal(
    'fetch',
    vi.fn(async (url: string) =>
      risposta(
        200,
        url.includes('/calendario/eventi') ? [] : { viste: [{ vista: '', nome: 'Tutti' }] },
      ),
    ),
  )
  const Vuota = { template: '<div />' }
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/', component: Vuota },
      { path: '/riunioni', component: Vuota },
      { path: '/eventi', component: Vuota },
      { path: '/eventi/:id', component: Vuota },
    ],
  })
  await router.push('/')
  const pagina = mount(CalendarioView, {
    global: { plugins: [router], stubs: { MioCalendario: true } },
  })
  await flushPromises()
  return { pagina, router }
}

beforeEach(() => {
  vi.useFakeTimers({ toFake: ['Date'] })
  vi.setSystemTime(new Date(2026, 10, 14, 10, 0)) // Saturday 14 November 2026
})
afterEach(() => {
  vi.useRealTimers()
  vi.unstubAllGlobals()
})

const piu = (pagina: ReturnType<typeof mount>, giorno: string) =>
  pagina.find(`button[aria-label="Crea il ${giorno}"]`)

describe('creating from a day', () => {
  it('a capo: from today on, a menu with both, the day passed on', async () => {
    const { pagina } = await monta({ capo: true })
    expect(piu(pagina, '13 novembre').exists()).toBe(false) // past
    expect(piu(pagina, '14 novembre').exists()).toBe(true)
    expect(piu(pagina, '1 dicembre').exists()).toBe(false) // a grey day of the next month
    await piu(pagina, '20 novembre').trigger('click')
    const voci = pagina.findAll('[role="menuitem"]')
    expect(voci.map((v) => v.text())).toEqual(['Nuova riunione', 'Nuovo evento'])
    expect(voci[0]!.attributes('href')).toBe('/riunioni?giorno=2026-11-20')
    expect(voci[1]!.attributes('href')).toBe('/eventi?giorno=2026-11-20')
  })

  it('who may create meetings only goes straight to the form', async () => {
    const { pagina, router } = await monta({ squadriglie_delegate: [3] })
    await piu(pagina, '21 novembre').trigger('click')
    await flushPromises()
    expect(pagina.find('[role="menu"]').exists()).toBe(false)
    expect(router.currentRoute.value.fullPath).toBe('/riunioni?giorno=2026-11-21')
  })

  it('a capo squadriglia sees it too', async () => {
    const { pagina } = await monta({ branca: 'eg', squadriglie_guidate: [3] })
    expect(piu(pagina, '14 novembre').exists()).toBe(true)
  })

  it('not who may create nothing', async () => {
    const { pagina } = await monta({ branca: 'generico' })
    expect(pagina.find('.qdc-piu').exists()).toBe(false)
  })

  it('only a real date comes from the address', () => {
    expect(giornoDaQuery('2026-11-20')).toBe('2026-11-20')
    expect(giornoDaQuery('20/11/2026')).toBeNull()
    expect(giornoDaQuery(['2026-11-20'])).toBeNull()
  })
})
