import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { createMemoryHistory, createRouter } from 'vue-router'

import type { Compleanno } from '@/api/qdc'
import { compleanniDelGiorno, leggiModo, salvaModo } from '@/eventi/calendario'
import CalendarioView from '@/views/CalendarioView.vue'

import { risposta } from './aiuti'

// The birthdays on the calendar page (DEC-417).
const compleanno = (persona_id: number, giorno: string, coca = false): Compleanno => ({
  persona_id,
  nome: `Nome${persona_id}`,
  cognome: 'Prova',
  giorno,
  anni: 12,
  unita: 'Reparto Prova (E1)',
  coca,
  scheda: persona_id === 1,
})

const ELENCO = [compleanno(1, '2026-11-14'), compleanno(2, '2026-11-20', true)]

async function monta(conCompleanni: boolean, indirizzo = '/calendario') {
  setActivePinia(createPinia())
  const chiamate: string[] = []
  vi.stubGlobal(
    'fetch',
    vi.fn(async (url: string) => {
      chiamate.push(url)
      if (url.includes('/calendario/compleanni')) return risposta(200, ELENCO)
      if (url.includes('/calendario/eventi')) return risposta(200, [])
      return risposta(200, { url: '', viste: [], compleanni: conCompleanni })
    }),
  )
  const Vuota = { template: '<div />' }
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/calendario', component: Vuota },
      { path: '/persone/:id', component: Vuota },
    ],
  })
  await router.push(indirizzo)
  const pagina = mount(CalendarioView, {
    global: { plugins: [router], stubs: { MioCalendario: true } },
  })
  await flushPromises()
  return { pagina, chiamate }
}

beforeEach(() => {
  localStorage.clear()
  vi.useFakeTimers({ toFake: ['Date'] })
  vi.setSystemTime(new Date(2026, 10, 14, 10, 0)) // Saturday 14 November 2026
})
afterEach(() => {
  vi.useRealTimers()
  vi.unstubAllGlobals()
})

describe('birthdays', () => {
  it('a cake on the days of the month, the names under the chosen day', async () => {
    const { pagina, chiamate } = await monta(true)
    expect(chiamate.some((u) => u.includes('/calendario/compleanni?dal=2026-10-26'))).toBe(true)
    const oggi = pagina.find('button[aria-label="14 novembre, un compleanno"]')
    expect(oggi.exists()).toBe(true)
    expect(pagina.find('[aria-label="Compleanni"]').text()).toContain('Nome1 Prova compie 12 anni')
  })

  it('the list of the next ones, the Co.Ca. marked, from the notification', async () => {
    const { pagina } = await monta(true, '/calendario?mostra=compleanni')
    const righe = pagina.findAll('[aria-label="Prossimi compleanni"] li')
    expect(righe).toHaveLength(2)
    expect(righe[0]!.text()).toContain('oggi · compie 12 anni · Reparto Prova (E1)')
    expect(righe[0]!.find('a').attributes('href')).toBe('/persone/1')
    expect(righe[1]!.find('a').exists()).toBe(false)
    expect(righe[1]!.classes()).toContain('qdc-compleanno-coca')
    expect(righe[1]!.text()).toContain('Co.Ca.')
  })

  it('nothing for who does not get them, not even a remembered choice', async () => {
    salvaModo('compleanni')
    const { pagina, chiamate } = await monta(false, '/calendario?mostra=compleanni')
    expect(pagina.text()).not.toContain('Prossimi compleanni')
    expect(chiamate.some((u) => u.includes('/calendario/compleanni'))).toBe(false)
    expect(pagina.find('.qdc-calendario').exists()).toBe(true)
  })

  it('the day and the remembered mode', () => {
    expect(compleanniDelGiorno(ELENCO, new Date(2026, 10, 20))).toHaveLength(1)
    salvaModo('compleanni')
    expect(leggiModo()).toBe('compleanni')
  })
})
