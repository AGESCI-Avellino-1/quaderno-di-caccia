import { flushPromises, mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import { defineComponent, h } from 'vue'
import { createMemoryHistory, createRouter } from 'vue-router'

import GruppoPagina from '@/components/GruppoPagina.vue'
import { useGruppiPagina } from '@/composables/useGruppiPagina'

// DEC-426: the main group open, one at a time, the open one in the address.
const Pagina = defineComponent({
  setup() {
    useGruppiPagina('prova', () => ['dati', 'quote', 'note'])
    return () =>
      h('div', { class: 'accordion' }, [
        h(GruppoPagina, { chiave: 'dati', titolo: 'Dati' }, () => 'D'),
        h(GruppoPagina, { chiave: 'quote', titolo: 'Quote' }, () => 'Q'),
        h(GruppoPagina, { chiave: 'note', titolo: 'Note' }, () => 'N'),
      ])
  },
})

async function monta(percorso: string) {
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [{ path: '/pagina', component: Pagina }],
  })
  await router.push(percorso)
  const pagina = mount(Pagina, { global: { plugins: [router] } })
  await flushPromises()
  const aperti = () =>
    pagina.findAll('details').filter((d) => (d.element as HTMLDetailsElement).open)
  return { pagina, router, aperti }
}

async function apri(dettaglio: Element, aperto: boolean) {
  ;(dettaglio as HTMLDetailsElement).open = aperto
  dettaglio.dispatchEvent(new Event('toggle'))
  await flushPromises()
}

describe('Pagine a gruppi', () => {
  it('opens the main group, all with the same name', async () => {
    const { pagina, aperti } = await monta('/pagina')
    expect(aperti().map((d) => d.attributes('data-gruppo'))).toEqual(['dati'])
    expect(new Set(pagina.findAll('details').map((d) => d.attributes('name')))).toEqual(
      new Set(['prova']),
    )
  })

  it('opens the group in the address, and keeps there the one opened', async () => {
    const { pagina, router, aperti } = await monta('/pagina?gruppo=note')
    expect(aperti().map((d) => d.attributes('data-gruppo'))).toEqual(['note'])
    await apri(pagina.find('[data-gruppo="quote"]').element, true)
    expect(router.currentRoute.value.query.gruppo).toBe('quote')
    expect(aperti().map((d) => d.attributes('data-gruppo'))).toEqual(['quote'])
    // Back to the main one: the address stays clean.
    await apri(pagina.find('[data-gruppo="dati"]').element, true)
    expect(router.currentRoute.value.query.gruppo).toBeUndefined()
  })

  it('remembers that every group was closed; an unknown group opens the main one', async () => {
    const { pagina, router, aperti } = await monta('/pagina')
    await apri(pagina.find('[data-gruppo="dati"]').element, false)
    expect(router.currentRoute.value.query.gruppo).toBe('nessuno')
    expect(aperti()).toHaveLength(0)
    const altra = await monta('/pagina?gruppo=sconosciuto')
    expect(altra.aperti().map((d) => d.attributes('data-gruppo'))).toEqual(['dati'])
  })
})
