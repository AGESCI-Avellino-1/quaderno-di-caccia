import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it } from 'vitest'
import { createWebHistory, createRouter } from 'vue-router'

import Briciole from '@/components/Briciole.vue'
import { useSessioneStore } from '@/stores/sessione'

// "Indietro" on the detail pages (DEC-404).
const Vuota = { template: '<div />' }
const rotte = [
  { path: '/', name: 'home', component: Vuota },
  { path: '/unita', name: 'unita', component: Vuota },
  { path: '/unita/:id', name: 'unita-dettaglio', component: Vuota },
  { path: '/persone', name: 'persone', component: Vuota },
  { path: '/persone/:id', name: 'persona', component: Vuota },
  { path: '/persone/:id/sentiero', name: 'sentiero', component: Vuota },
]

async function monta(...percorsi: string[]) {
  // Each test starts as a page opened from outside: no page of the app before it.
  window.history.replaceState(null, '', '/')
  const router = createRouter({ history: createWebHistory(), routes: rotte })
  for (const p of percorsi) await router.push(p)
  const pagina = mount(Briciole, { global: { plugins: [router] } })
  await flushPromises()
  return { pagina, router }
}

beforeEach(() => {
  setActivePinia(createPinia())
  useSessioneStore().profilo = {
    email: 'x@example.invalid',
    persona: { id: 1, nome: 'Mario', cognome: 'Rossi' },
    branca: 'capi',
    capo: true,
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
  }
})

const indietro = (pagina: ReturnType<typeof mount>) =>
  pagina.findAll('button').find((b) => b.text() === 'Indietro')

describe('back button', () => {
  it('goes back to the page of the app it came from', async () => {
    const { pagina, router } = await monta('/persone/3/sentiero', '/unita/7')
    const tornato = new Promise((r) => router.afterEach(r))
    await indietro(pagina)!.trigger('click')
    await tornato
    expect(router.currentRoute.value.fullPath).toBe('/persone/3/sentiero')
  })

  it('opened from outside, goes to the page above', async () => {
    const { pagina, router } = await monta('/unita/7')
    await indietro(pagina)!.trigger('click')
    await flushPromises()
    expect(router.currentRoute.value.fullPath).toBe('/unita')
  })

  it('is not on a page with nothing above', async () => {
    const { pagina } = await monta('/unita')
    expect(indietro(pagina)).toBeUndefined()
  })
})
