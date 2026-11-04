import { flushPromises, mount } from '@vue/test-utils'
import { afterEach, describe, expect, it, vi } from 'vitest'

import IncarichiSquadriglia from '@/components/IncarichiSquadriglia.vue'

const json = (corpo: unknown, status = 200) =>
  new Response(JSON.stringify(corpo), {
    status,
    headers: { 'Content-Type': 'application/json' },
  })

const DATI = {
  id: 7,
  nome: 'Pantere',
  incarichi: [
    {
      id: 1,
      ruolo: 'CRONISTA',
      ruolo_nome: 'Cronista',
      persona: { id: 3, nome: 'Alice', cognome: 'Marino' },
      data_inizio: '2026-10-01',
      data_fine: null,
    },
  ],
  nomina: [{ valore: 'CRONISTA', etichetta: 'Cronista' }],
}

afterEach(() => vi.unstubAllGlobals())

describe('gli incarichi di squadriglia', () => {
  it('il capo squadriglia li assegna dalla sua pagina', async () => {
    const fetch = vi.fn(async () => json(DATI))
    vi.stubGlobal('fetch', fetch)
    const pagina = mount(IncarichiSquadriglia, {
      props: { squadriglia: 7, membri: [{ id: 3, nome: 'Alice', cognome: 'Marino' }] },
    })
    await flushPromises()
    expect(fetch).toHaveBeenCalledWith('/api/v1/squadriglie/7/incarichi', expect.anything())
    expect(pagina.text()).toContain('Cronista')
    expect(pagina.text()).toContain('Alice Marino')
    expect(pagina.find('form').exists()).toBe(true)
  })

  it('il genitore li legge dalla scheda del figlio, senza assegnarli', async () => {
    const fetch = vi.fn(async () => json({ ...DATI, nomina: [] }))
    vi.stubGlobal('fetch', fetch)
    const pagina = mount(IncarichiSquadriglia, { props: { persona: 3 } })
    await flushPromises()
    expect(fetch).toHaveBeenCalledWith('/api/v1/persone/3/incarichi-squadriglia', expect.anything())
    expect(pagina.text()).toContain('Incarichi nella squadriglia Pantere')
    expect(pagina.find('form').exists()).toBe(false)
  })

  it('chi non può leggerli non vede il riquadro', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => json({ detail: 'Non trovato.' }, 404)),
    )
    const pagina = mount(IncarichiSquadriglia, { props: { persona: 3 } })
    await flushPromises()
    expect(pagina.find('section').exists()).toBe(false)
  })
})
