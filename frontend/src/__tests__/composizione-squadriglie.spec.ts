import { flushPromises, mount } from '@vue/test-utils'
import { afterEach, describe, expect, it, vi } from 'vitest'

import UnitaDettaglioView from '@/views/UnitaDettaglioView.vue'

import { nuovoDatabase, risposta } from './aiuti'

const persona = (id: number, nome: string) => ({ id, nome, cognome: 'Prova' })
const squadriglia = (id: number, nome: string, membri: object[]) => ({
  id,
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
  senza_squadriglia: [persona(200, 'Marta')],
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

  it('shows members read-only to whoever may not change them', async () => {
    const pagina = await monta(false)
    expect(pagina.text()).toContain('Giulia Prova')
    expect(pagina.find('select[aria-label="Sposta Giulia Prova"]').exists()).toBe(false)
  })
})
