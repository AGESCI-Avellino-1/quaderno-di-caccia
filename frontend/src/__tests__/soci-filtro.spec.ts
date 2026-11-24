import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { createMemoryHistory, createRouter } from 'vue-router'

import type { Profilo } from '@/api/qdc'
import { useSessioneStore } from '@/stores/sessione'
import PersoneView from '@/views/PersoneView.vue'

import { nuovoDatabase, risposta } from './aiuti'

const UNITA = [
  { id: 3, nome: 'Hirpinia', codice: 'T1', tipo: 'CLAN_FUOCO', branca: 'RS', attiva: true },
]

const SOCI = [
  { id: 1, nome: 'Zeno', cognome: 'Bianchi', codice_socio: '2000' },
  { id: 2, nome: 'Anna', cognome: 'Verdi', codice_socio: null },
  { id: 3, nome: 'Marco', cognome: 'Abate', codice_socio: '100' },
]

async function monta(percorso: string) {
  await nuovoDatabase()
  vi.stubGlobal(
    'fetch',
    vi.fn(async (url: string) => risposta(200, url.includes('/unita') ? UNITA : SOCI)),
  )
  const Vuota = { template: '<div />' }
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/soci', name: 'persone', component: PersoneView, props: { tipo: 'soci' } },
      { path: '/persone/:id', name: 'persona', component: Vuota },
    ],
  })
  await router.push(percorso)
  const pagina = mount(PersoneView, { props: { tipo: 'soci' }, global: { plugins: [router] } })
  await flushPromises()
  return { pagina, router }
}

describe('Soci', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    useSessioneStore().profilo = { capo: true, tutelati: [] } as unknown as Profilo
  })
  afterEach(() => vi.unstubAllGlobals())

  it('keeps the unit and the search in the address, for the way back', async () => {
    const { pagina, router } = await monta('/soci')
    await pagina
      .findAll('button')
      .find((b) => b.text().includes('Hirpinia'))!
      .trigger('click')
    await pagina.find('input[type="search"]').setValue('ross')
    await flushPromises()
    expect(router.currentRoute.value.query).toEqual({ unita: '3', cerca: 'ross' })
  })

  it('starts from the unit and the search in the address', async () => {
    const { pagina } = await monta('/soci?unita=3&cerca=ross')
    expect(pagina.find<HTMLInputElement>('input[type="search"]').element.value).toBe('ross')
    const scelto = pagina.findAll('button').find((b) => b.text().includes('Hirpinia'))!
    expect(scelto.attributes('aria-checked')).toBe('true')
  })

  // DEC-427
  it('orders by surname, by name or by codice socio, and keeps it in the address', async () => {
    const { pagina, router } = await monta('/soci')
    const righe = () => pagina.findAll('.list-group-item .me-auto').map((r) => r.text())
    expect(righe()).toEqual(['Abate Marco', 'Bianchi Zeno', 'Verdi Anna'])
    const chip = (nome: string) => pagina.findAll('button').find((b) => b.text() === nome)!
    await chip('Nome').trigger('click')
    expect(righe()).toEqual(['Anna Verdi', 'Marco Abate', 'Zeno Bianchi'])
    await chip('Codice socio').trigger('click')
    await flushPromises()
    // Numbers in order, who has none last.
    expect(righe()).toEqual(['Abate Marco', 'Bianchi Zeno', 'Verdi Anna'])
    expect(router.currentRoute.value.query.ordine).toBe('codice')
  })
})
