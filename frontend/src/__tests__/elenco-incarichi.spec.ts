import { flushPromises, mount } from '@vue/test-utils'
import { afterEach, describe, expect, it, vi } from 'vitest'

import ElencoIncarichi from '@/components/ElencoIncarichi.vue'

const json = (dati: unknown, stato = 200) =>
  new Response(JSON.stringify(dati), {
    status: stato,
    headers: { 'Content-Type': 'application/json' },
  })

const incarico = (id: number, ruolo: string, ruolo_nome: string, nome: string) => ({
  id,
  ruolo,
  ruolo_nome,
  persona: { id: id * 10, nome, cognome: 'Prova' },
  data_inizio: '2025-10-01',
  data_fine: null,
})

const props = (altro: object = {}) => ({
  incarichi: [
    incarico(1, 'CAPO_UNITA', 'Capo unità', 'Anna'),
    incarico(2, 'TESORIERE_UNITA', 'Tesoriere di unità', 'Bea'),
  ],
  nomina: [{ valore: 'TESORIERE_UNITA', etichetta: 'Tesoriere di unità' }],
  dove: { unita_id: 7 },
  candidati: async () => [{ id: 99, nome: 'Carlo', cognome: 'Capo' }],
  ...altro,
})

afterEach(() => vi.unstubAllGlobals())

describe('ElencoIncarichi', () => {
  it('offers actions only for the roles the server allows', () => {
    const elenco = mount(ElencoIncarichi, { props: props() })
    const righe = elenco.findAll('li')
    expect(righe[0]!.text()).not.toContain('chiudi') // capo unità: not this user's call
    expect(righe[1]!.text()).toContain('chiudi')
    expect(elenco.findAll('option').map((o) => o.text())).toContain('Tesoriere di unità')
  })

  it('shows no form when the user may assign nothing', () => {
    const elenco = mount(ElencoIncarichi, { props: props({ nomina: [] }) })
    expect(elenco.find('form').exists()).toBe(false)
    expect(elenco.text()).not.toContain('chiudi')
  })

  it('assigns a role and closes one, then asks to reload', async () => {
    const chiamate: { url: string; corpo: unknown }[] = []
    vi.stubGlobal(
      'fetch',
      vi.fn(async (url: string, opzioni?: RequestInit) => {
        chiamate.push({ url, corpo: JSON.parse((opzioni?.body as string) ?? 'null') })
        return json({ id: 3, rimosso: false }, 201)
      }),
    )
    const elenco = mount(ElencoIncarichi, { props: props() })

    await elenco.get('select[aria-label="Incarico"]').setValue('TESORIERE_UNITA')
    await flushPromises()
    await elenco.get('select[aria-label="Persona"]').setValue(99)
    await elenco.get('form').trigger('submit')
    await flushPromises()

    // Closing asks for confirmation inline (no browser dialog).
    await elenco.findAll('li')[1]!.get('button').trigger('click')
    expect(elenco.text()).toContain('Chiudere da oggi?')
    await elenco.get('button.theme-danger').trigger('click')
    await flushPromises()

    expect(chiamate).toEqual([
      {
        url: '/api/v1/incarichi',
        corpo: { persona_id: 99, ruolo: 'TESORIERE_UNITA', unita_id: 7 },
      },
      { url: '/api/v1/incarichi/2/termina', corpo: {} },
    ])
    expect(elenco.emitted('cambiato')).toHaveLength(2)
  })
})
