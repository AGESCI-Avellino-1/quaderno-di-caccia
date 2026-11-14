import { flushPromises, mount } from '@vue/test-utils'
import { afterEach, describe, expect, it, vi } from 'vitest'

import TurniGruppoView from '@/views/TurniGruppoView.vue'

import { risposta } from './aiuti'

// Turns of the group round the units (DEC-406).
const unita = [
  { id: 1, nome: 'Branco Prova' },
  { id: 2, nome: 'Reparto Prova' },
  { id: 3, nome: 'Clan Prova' },
]
const dati = (puo_gestire: boolean) => ({
  turni: [
    {
      id: 9,
      nome: 'Pulizia della sede',
      periodo: 'MESE',
      dal: '2027-01-15',
      unita: unita.slice(0, 2),
      prossimi: [
        {
          indice: 0,
          dal: '2027-01-15',
          al: '2027-01-31',
          unita_id: 1,
          unita: 'Branco Prova',
          cambiato: false,
        },
        {
          indice: 1,
          dal: '2027-02-01',
          al: '2027-02-28',
          unita_id: 1,
          unita: 'Branco Prova',
          cambiato: true,
        },
      ],
    },
  ],
  unita: puo_gestire ? unita : [],
  puo_gestire,
})

async function monta(
  puo: boolean,
  chiamate: { metodo: string; url: string; corpo: unknown }[] = [],
) {
  vi.stubGlobal(
    'fetch',
    vi.fn(async (url: string, opzioni?: RequestInit) => {
      if (opzioni?.method && opzioni.method !== 'GET') {
        chiamate.push({ metodo: opzioni.method, url, corpo: JSON.parse(opzioni.body as string) })
      }
      return risposta(200, dati(puo))
    }),
  )
  const pagina = mount(TurniGruppoView)
  await flushPromises()
  return pagina
}

afterEach(() => vi.unstubAllGlobals())

const bottone = (pagina: Awaited<ReturnType<typeof monta>>, testo: string) =>
  pagina.findAll('button').find((b) => b.text() === testo)!

describe('group turns', () => {
  it('creates a turn with the units in the order they were ticked', async () => {
    const chiamate: { metodo: string; url: string; corpo: unknown }[] = []
    const pagina = await monta(true, chiamate)
    await bottone(pagina, 'Nuovo turno').trigger('click')
    await pagina.get('#turno-nome').setValue('Preghiera')
    await pagina.get('#turno-unita-3').setValue(true)
    await pagina.get('#turno-unita-1').setValue(true)
    await pagina.get('button[aria-label="Sposta su Branco Prova"]').trigger('click')
    await pagina.get('form').trigger('submit')
    await flushPromises()
    expect(chiamate).toEqual([
      {
        metodo: 'POST',
        url: '/api/v1/turni-gruppo',
        corpo: expect.objectContaining({ nome: 'Preghiera', unita: [1, 3], periodo: 'MESE' }),
      },
    ])
  })

  it('gives one period to another unit, and back to the rotation', async () => {
    const chiamate: { metodo: string; url: string; corpo: unknown }[] = []
    const pagina = await monta(true, chiamate)
    const scelte = pagina.findAll('select[aria-label^="Chi ha il turno"]')
    expect(scelte[1]!.findAll('option').map((o) => o.text())).toContain('Come da rotazione')
    await scelte[0]!.setValue('2')
    await flushPromises()
    await pagina.findAll('select[aria-label^="Chi ha il turno"]')[1]!.setValue('rotazione')
    await flushPromises()
    expect(chiamate).toEqual([
      { metodo: 'PUT', url: '/api/v1/turni-gruppo/9/periodi/0', corpo: { unita_id: 2 } },
      { metodo: 'PUT', url: '/api/v1/turni-gruppo/9/periodi/1', corpo: { unita_id: null } },
    ])
  })

  it('only shows them to who may not change them', async () => {
    const pagina = await monta(false)
    expect(pagina.text()).toContain('Pulizia della sede')
    expect(pagina.text()).not.toContain('Nuovo turno')
    expect(pagina.find('select').exists()).toBe(false)
  })
})
