import { flushPromises, mount } from '@vue/test-utils'
import { afterEach, describe, expect, it, vi } from 'vitest'

import type { DettaglioEvento } from '@/api/qdc'
import EventoView from '@/views/EventoView.vue'

import { risposta } from './aiuti'

// It asks the server for its own list: tested in verbali-modello.spec.ts.
vi.mock('@/components/VerbaliCollegati.vue', () => ({ default: { render: () => null } }))

// The minutes have their own tests and their own answers.
vi.mock('@/components/VerbaleRiunione.vue', () => ({ default: { template: '<div></div>' } }))

function evento(campi: Partial<DettaglioEvento>): DettaglioEvento {
  return {
    id: 5,
    titolo: 'Uscita al lago',
    tipo: 'USCITA',
    tipo_nome: 'Uscita',
    livello: 'UNITA',
    livello_nome: 'Unità',
    branca: '',
    unita: [1],
    unita_nomi: ['Reparto Millennium (M1)'],
    squadriglia_id: null,
    squadriglia: null,
    inizio: '2026-03-14T09:00:00+01:00',
    fine: '2026-03-15T17:00:00+01:00',
    luogo: 'Lago Laceno',
    descrizione: '',
    note_genitori: null,
    cerchia: 'TUTTI',
    cerchia_nome: 'Tutti',
    riunione: false,
    annullato: false,
    motivo_annullamento: '',
    mie: [],
    puo_gestire: false,
    quota: null,
    partecipanti: [],
    puo_presenze: false,
    puo_non_invitare: false,
    ...campi,
  }
}

afterEach(() => vi.unstubAllGlobals())

describe('EventoView', () => {
  it('lets the family say their child will not take part, and shows a staff exclusion', async () => {
    const corpi: unknown[] = []
    vi.stubGlobal(
      'fetch',
      vi.fn(async (_url: string, opzioni?: RequestInit) => {
        if (opzioni?.method === 'POST') corpi.push(JSON.parse(opzioni.body as string))
        return risposta(
          200,
          evento({
            note_genitori: 'Partenza alle 7',
            mie: [
              {
                persona_id: 1,
                persona: 'Giulia Rossi',
                stato: 'INVITATO',
                motivo: '',
                puo_segnalare: true,
              },
              {
                persona_id: 2,
                persona: 'Luca Rossi',
                stato: 'NON_INVITATO',
                motivo: 'Patto non rispettato',
                puo_segnalare: true,
              },
            ],
          }),
        )
      }),
    )
    const pagina = mount(EventoView, { props: { id: 5 } })
    await flushPromises()
    expect(pagina.text()).toContain('Partenza alle 7')
    expect(pagina.text()).toContain('Lo staff ha deciso di non invitarlo: Patto non rispettato')
    expect(pagina.find('#partecipa-2').exists()).toBe(false)

    await pagina.get('#partecipa-1').setValue(false)
    await flushPromises()
    expect(corpi).toEqual([{ partecipa: false }])
  })

  it('the staff marks attendance; who said they would not come is marked excused', async () => {
    const corpi: unknown[] = []
    vi.stubGlobal(
      'fetch',
      vi.fn(async (_url: string, opzioni?: RequestInit) => {
        if (opzioni?.method === 'PUT') {
          corpi.push(JSON.parse(opzioni.body as string))
          return risposta(200, { segnate: 2 })
        }
        return risposta(
          200,
          evento({
            puo_presenze: true,
            partecipanti: [
              {
                persona_id: 1,
                cognome: 'Rossi',
                nome: 'Giulia',
                stato: 'INVITATO',
                motivo: '',
                presenza: null,
              },
              {
                persona_id: 2,
                cognome: 'Bianchi',
                nome: 'Sara',
                stato: 'NON_PARTECIPA',
                motivo: '',
                presenza: null,
              },
            ],
          }),
        )
      }),
    )
    const pagina = mount(EventoView, { props: { id: 5 } })
    await flushPromises()
    const pulsante = (testo: string) => pagina.findAll('button').find((b) => b.text() === testo)!
    await pulsante('Segna gli altri presenti').trigger('click')
    await pulsante('Salva le presenze').trigger('click')
    await flushPromises()
    expect(corpi).toEqual([
      {
        segni: [
          { persona_id: 1, stato: 'PRESENTE' },
          { persona_id: 2, stato: 'GIUSTIFICATO' },
        ],
      },
    ])
    expect(pagina.text()).toContain('Presenze salvate.')
  })
})

describe('EventoView for a meeting', () => {
  it('shows place, uniform and notes, and no fee', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () =>
        risposta(
          200,
          evento({
            tipo: 'RIUNIONE',
            tipo_nome: 'Riunione',
            titolo: 'Riunione di reparto',
            luogo: 'Sede',
            localita: {
              id: 1,
              nome: 'Sede',
              denominazione: '',
              indirizzo: 'Via dei Pini',
              civico: '1',
              indirizzo_completo: 'Via dei Pini 1',
              mappa: '',
            },
            uniforme: false,
            serie_id: 3,
            informazioni: '<p>Porta la <strong>borraccia</strong></p>',
            puo_gestire: true,
          }),
        ),
      ),
    )
    const vista = mount(EventoView, { props: { id: 5 } })
    await flushPromises()
    expect(vista.text()).toContain('Via dei Pini 1')
    expect(vista.text()).toContain('Uniforme no')
    expect(vista.find('strong').exists()).toBe(true)
    expect(vista.html()).toContain('<strong>borraccia</strong>')
    expect(vista.text()).not.toContain('Quota')
    expect(vista.text()).toContain('Modifica la riunione')
    expect(vista.text()).toContain('Annulla la riunione')
  })
})
