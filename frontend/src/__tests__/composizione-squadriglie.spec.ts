import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import UnitaDettaglioView from '@/views/UnitaDettaglioView.vue'

import { nuovoDatabase, risposta } from './aiuti'

beforeEach(() => setActivePinia(createPinia())) // the page reads the profile

const persona = (id: number, nome: string) => ({ id, nome, cognome: 'Prova' })
const squadriglia = (id: number, nome: string, membri: object[], unita_id = 5) => ({
  id,
  unita_id,
  nome,
  sesso: 'F',
  attiva: true,
  membri,
  incarichi: [],
  nomina: [],
})

const dettaglio = (puo_gestire_squadriglie: boolean) => ({
  unita: {
    id: 5,
    nome: 'Reparto Prova',
    tipo: 'REPARTO',
    branca: 'EG',
    composizione: 'F',
    ambiente: 'NESSUNO',
    attiva: true,
    collegata_a: null,
    nota_collegamento: '',
  },
  incarichi: [],
  squadriglie: [
    squadriglia(1, 'Aquile', [
      { id: 11, persona: persona(100, 'Giulia'), data_inizio: '2025-10-01' },
    ]),
    squadriglia(2, 'Volpi', []),
  ],
  senza_squadriglia: [{ ...persona(200, 'Marta'), reparto_id: 5 }],
  avvisi: [],
  puo_modificare: false,
  puo_gestire_squadriglie,
  nomina: [],
})

async function monta(puo: boolean, chiamate: { url: string; corpo: unknown }[] = []) {
  await nuovoDatabase() // vault to configure: reads go straight to the network
  vi.stubGlobal(
    'fetch',
    vi.fn(async (url: string, opzioni?: RequestInit) => {
      if (opzioni?.method === 'POST') {
        chiamate.push({ url, corpo: JSON.parse((opzioni.body as string) ?? 'null') })
        return risposta(201, { id: 1 })
      }
      return risposta(200, dettaglio(puo))
    }),
  )
  const pagina = mount(UnitaDettaglioView, {
    props: { id: 5 },
    global: { stubs: { RouterLink: { template: '<a><slot /></a>' } } },
  })
  await flushPromises()
  return pagina
}

afterEach(() => vi.unstubAllGlobals())

describe('patrol composition', () => {
  it('moves a member and places a ragazza without a patrol', async () => {
    const chiamate: { url: string; corpo: unknown }[] = []
    const pagina = await monta(true, chiamate)
    expect(pagina.text()).toContain('Senza squadriglia')

    await pagina.get('select[aria-label="Sposta Giulia Prova"]').setValue('2')
    await flushPromises()
    await pagina.get('select[aria-label="Metti Marta Prova in una squadriglia"]').setValue('1')
    await flushPromises()
    await pagina.get('select[aria-label="Sposta Giulia Prova"]').setValue('fuori')
    await flushPromises()

    expect(chiamate).toEqual([
      { url: '/api/v1/squadriglie/2/membri', corpo: { persona_id: 100 } },
      { url: '/api/v1/squadriglie/1/membri', corpo: { persona_id: 200 } },
      { url: '/api/v1/membri-squadriglia/11/termina', corpo: null },
    ])
  })

  // DEC-403
  it('archives only an empty patrol, after asking', async () => {
    const chiamate: { url: string; corpo: unknown }[] = []
    const pagina = await monta(true, chiamate)
    const archivia = pagina.findAll('button').filter((b) => b.text() === 'archivia')
    expect(archivia).toHaveLength(1) // the Volpi, the Aquile have a member
    await archivia[0].trigger('click')
    expect(pagina.text()).toContain('Archiviarla per sempre?')
    await pagina
      .findAll('button')
      .find((b) => b.text() === 'Archivia')!
      .trigger('click')
    await flushPromises()
    expect(chiamate).toEqual([{ url: '/api/v1/squadriglie/2/archivia', corpo: null }])
  })

  it('shows members read-only to whoever may not change them', async () => {
    const pagina = await monta(false)
    expect(pagina.text()).toContain('Giulia Prova')
    expect(pagina.find('select[aria-label="Sposta Giulia Prova"]').exists()).toBe(false)
  })
})

describe('two linked reparti', () => {
  // DEC-405
  it('moves each ragazzo only among the patrols of their own reparto', async () => {
    const dati = {
      ...dettaglio(true),
      reparti: [
        { id: 5, nome: 'Reparto Prova', composizione: 'F' },
        { id: 6, nome: 'Reparto Parallelo', composizione: 'M' },
      ],
      squadriglie: [
        { ...squadriglia(1, 'Aquile', []), unita_nome: 'Reparto Prova' },
        { ...squadriglia(2, 'Volpi', []), unita_nome: 'Reparto Prova' },
        { ...squadriglia(3, 'Lupi', [], 6), unita_nome: 'Reparto Parallelo' },
      ],
      senza_squadriglia: [
        { ...persona(200, 'Marta'), reparto_id: 5 },
        { ...persona(300, 'Marco'), reparto_id: 6 },
      ],
    }
    await nuovoDatabase()
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => risposta(200, dati)),
    )
    const pagina = mount(UnitaDettaglioView, {
      props: { id: 5 },
      global: { stubs: { RouterLink: { template: '<a><slot /></a>' } } },
    })
    await flushPromises()
    expect(pagina.text()).toContain('Reparto Parallelo')
    const opzioni = (etichetta: string) =>
      pagina
        .get(`select[aria-label="${etichetta}"]`)
        .findAll('option')
        .map((o) => o.text())
    expect(opzioni('Metti Marta Prova in una squadriglia')).toEqual([
      'Metti in…',
      'Sq. Aquile',
      'Sq. Volpi',
    ])
    expect(opzioni('Metti Marco Prova in una squadriglia')).toEqual(['Metti in…', 'Sq. Lupi'])
  })
})

describe('choosing the animal', () => {
  const animali = {
    animali: [
      { id: 7, nome: 'Aquila', plurale: 'Aquile', tipo: 'GENERALE', attivo: true },
      { id: 8, nome: 'Pantera', plurale: 'Pantere', tipo: 'GENERALE', attivo: true },
      { id: 9, nome: 'Orca', plurale: 'Orche', tipo: 'NAUTICO', attivo: true },
      { id: 10, nome: 'Lupo', plurale: 'Lupi', tipo: 'GENERALE', attivo: false },
    ],
    colori: [],
    puo_modificare: true,
  }

  async function montaConAnimali(dati: object, chiamate: { url: string; corpo: unknown }[]) {
    await nuovoDatabase()
    vi.stubGlobal(
      'fetch',
      vi.fn(async (url: string, opzioni?: RequestInit) => {
        if (opzioni?.method === 'POST' || opzioni?.method === 'PUT') {
          chiamate.push({ url, corpo: JSON.parse(opzioni.body as string) })
          return risposta(201, { id: 1 })
        }
        return risposta(200, url.endsWith('/animali') ? animali : dati)
      }),
    )
    const pagina = mount(UnitaDettaglioView, {
      props: { id: 5 },
      global: { stubs: { RouterLink: { template: '<a><slot /></a>' } } },
    })
    await flushPromises()
    return pagina
  }

  it('offers the free ones grouped, and creates the patrol from the animal', async () => {
    const chiamate: { url: string; corpo: unknown }[] = []
    const pagina = await montaConAnimali(dettaglio(true), chiamate)
    const nuova = pagina.findAll('button').find((b) => b.text() === 'Nuova squadriglia')!
    await nuova.trigger('click')
    await flushPromises()
    const scelta = pagina.find('select[aria-label="Animale della squadriglia"]')
    // «Aquile» is taken in this reparto, Lupo is switched off.
    expect(scelta.findAll('option').map((o) => o.text())).toEqual([
      'Senza animale: lo sceglie il capo squadriglia',
      'Pantere',
      'Orche',
    ])
    expect(scelta.findAll('optgroup').map((o) => o.attributes('label'))).toEqual([
      'Generali',
      'Nautici',
    ])
    await scelta.setValue(8)
    await pagina.find('form').trigger('submit')
    await flushPromises()
    expect(chiamate[0]).toEqual({
      url: '/api/v1/unita/5/squadriglie',
      corpo: { animale_id: 8, sesso: 'F' },
    })
  })

  it('creates a patrol without an animal, for its capo squadriglia', async () => {
    // DEC-409
    const chiamate: { url: string; corpo: unknown }[] = []
    const pagina = await montaConAnimali(dettaglio(true), chiamate)
    await pagina
      .findAll('button')
      .find((b) => b.text() === 'Nuova squadriglia')!
      .trigger('click')
    await flushPromises()
    await pagina.find('form').trigger('submit')
    await flushPromises()
    expect(chiamate[0]).toEqual({ url: '/api/v1/unita/5/squadriglie', corpo: { sesso: 'F' } })
  })

  it('asks a patrol from before the animals to choose one', async () => {
    const chiamate: { url: string; corpo: unknown }[] = []
    const pagina = await montaConAnimali(dettaglio(true), chiamate)
    const scelte = pagina.findAll('select[aria-label="Scegli l\'animale"]')
    expect(scelte).toHaveLength(2)
    await scelte[0].trigger('focus')
    await flushPromises()
    const opzione = pagina.findAll('select[aria-label="Scegli l\'animale"]')[0]
    await opzione.setValue(8)
    await flushPromises()
    expect(chiamate[0]).toEqual({
      url: '/api/v1/squadriglie/1',
      corpo: { animale_id: 8, sesso: 'F' },
    })
  })

  it('does not ask who cannot change the patrols', async () => {
    const pagina = await montaConAnimali(dettaglio(false), [])
    expect(pagina.findAll('select[aria-label="Scegli l\'animale"]')).toHaveLength(0)
  })
})
