import { flushPromises, mount, RouterLinkStub } from '@vue/test-utils'
import { afterEach, describe, expect, it, vi } from 'vitest'

import DirittiView from '@/views/DirittiView.vue'
import FascicoloView from '@/views/FascicoloView.vue'

import { risposta } from './aiuti'

type Chiamata = { url: string; metodo: string; corpo: unknown }
const globali = { global: { stubs: { RouterLink: RouterLinkStub } } }

function stubFetch(risposte: (url: string, metodo: string) => unknown, chiamate: Chiamata[]) {
  vi.stubGlobal(
    'fetch',
    vi.fn(async (url: string, opzioni?: RequestInit) => {
      const metodo = opzioni?.method ?? 'GET'
      if (metodo !== 'GET') {
        chiamate.push({ url, metodo, corpo: JSON.parse((opzioni?.body as string) ?? 'null') })
      }
      return risposta(200, risposte(url, metodo))
    }),
  )
}

afterEach(() => vi.unstubAllGlobals())

const richiesta = {
  id: 4,
  persona: { id: 3, nome: 'Giulia', cognome: 'Rossi' },
  tipo: 'ACCESSO',
  tipo_nome: 'Accesso ai dati',
  richiedente: 'La madre, via email',
  ricevuta_il: '2020-01-01',
  scadenza: '2020-01-31',
  note: '',
  inoltrata_nazionale_il: null,
  evasa_il: null,
  registrata_da: 'cg@example.invalid',
}

describe('DirittiView', () => {
  it('flags overdue requests and records the forwarding', async () => {
    const chiamate: Chiamata[] = []
    stubFetch(() => [richiesta], chiamate)
    const vista = mount(DirittiView, globali)
    await flushPromises()
    expect(vista.text()).toMatch(/Scaduta il 31\/0?1\/2020/)

    await vista
      .findAll('button')
      .find((b) => b.text() === 'Girata al nazionale oggi')!
      .trigger('click')
    await flushPromises()
    expect(chiamate[0]).toMatchObject({ url: '/api/v1/richieste-diritti/4', metodo: 'PATCH' })
    expect(Object.keys(chiamate[0]!.corpo as object)).toEqual(['inoltrata_nazionale_il'])
  })
})

describe('FascicoloView', () => {
  const fascicolo = {
    persona: { id: 3, nome: 'Giulia', cognome: 'Rossi' },
    generato_il: '2026-10-29T10:00:00Z',
    anagrafica: { Nome: 'Giulia', 'Consenso per le foto (2B)': true },
    unita: [{ unita: 'Reparto', ruolo: 'Ragazzo', dal: '2025-10-01', al: '' }],
    inviti: [],
    informazioni_sanitarie: null,
  }

  it('shows every section and erases only after the surname is typed', async () => {
    const chiamate: Chiamata[] = []
    stubFetch(
      (url, metodo) =>
        url.endsWith('/fascicolo')
          ? fascicolo
          : { anonimizza: metodo === 'POST', motivo_anagrafica: null, voci: ['Account'] },
      chiamate,
    )
    const vista = mount(FascicoloView, { props: { id: 3 }, ...globali })
    await flushPromises()
    expect(vista.text()).toContain('Fascicolo di Giulia Rossi')
    expect(vista.text()).toContain('Dati anagrafici')
    expect(vista.text()).toContain('Sì')
    expect(vista.findAll('table td').map((c) => c.text())).toContain('—')
    expect(vista.text()).toContain('Nessun dato.')

    await vista
      .findAll('button')
      .find((b) => b.text().startsWith('Vedi cosa'))!
      .trigger('click')
    await flushPromises()
    await vista.get('#conferma-cognome').setValue('Rossi')
    await vista.get('form').trigger('submit')
    await flushPromises()
    expect(chiamate).toEqual([
      { url: '/api/v1/persone/3/cancellazione', metodo: 'POST', corpo: { cognome: 'Rossi' } },
    ])
    expect(vista.text()).toContain('La persona è stata resa anonima')
  })
})
