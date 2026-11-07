import { flushPromises, mount } from '@vue/test-utils'
import { afterEach, describe, expect, it, vi } from 'vitest'

import type { EventoBCIn, TipologiaBC } from '@/api/qdc'
import ModuloEventoBC from '@/components/ModuloEventoBC.vue'

import { scegliPersona } from './aiuti-scelta'

// The type of a BuonaCaccia event brings its constraints, changed for the event (DEC-398).
const TIPOLOGIE: TipologiaBC[] = [
  {
    id: 3,
    codice: '2010102',
    nome: 'Capi Squadriglia',
    categoria: 'EG',
    categoria_nome: 'E/G',
    attiva: true,
    altro: false,
    branche: ['EG'],
    eta_minima: 13,
    eta_massima: 16,
    livello_minimo: null,
    massimo_per_unita: 4,
    massimo_per_gruppo: null,
    eventi: 0,
  },
]

TIPOLOGIE.unshift({
  ...TIPOLOGIE[0]!,
  id: 1,
  codice: '',
  nome: 'Altro',
  categoria: 'ALTRO',
  categoria_nome: 'Altro',
  altro: true,
  branche: [],
  eta_minima: null,
  eta_massima: null,
  massimo_per_unita: null,
})

afterEach(() => vi.unstubAllGlobals())

describe('modulo di un evento su BuonaCaccia', () => {
  it('requires a type, copies its constraints, sends them changed', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(
        async () =>
          new Response(JSON.stringify(TIPOLOGIE), {
            headers: { 'Content-Type': 'application/json' },
          }),
      ),
    )
    const w = mount(ModuloEventoBC, { props: { etichetta: 'Aggiungi' }, attachTo: document.body })
    await flushPromises()
    const tipo = w.get<HTMLInputElement>('#bc-tipologia')
    expect(tipo.element.validationMessage).toBe("Scegli il tipo dall'elenco.")
    await scegliPersona(w, '#bc-tipologia', 'capi squ')
    const numeri = w.findAll<HTMLInputElement>('input[type=number]')
    expect(numeri.map((n) => n.element.value)).toEqual(['13', '16', '', '4', ''])
    await numeri[1]!.setValue('15')
    await w.get('#bc-titolo').setValue('Capi Squadriglia di Zona')
    await w.get('#bc-inizio').setValue('2026-12-04')
    await w.get('form').trigger('submit')
    const [dati] = w.emitted('salva')![0] as [EventoBCIn]
    expect(dati).toMatchObject({
      tipologia_id: 3,
      branche: ['EG'],
      eta_minima: 13,
      eta_massima: 15,
      massimo_per_unita: 4,
    })
    w.unmount()
  })
})
