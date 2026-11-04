import { flushPromises, mount } from '@vue/test-utils'
import { afterEach, describe, expect, it, vi } from 'vitest'

import type { ConvocazioneModello, VerbaleCollegato, VerbaleModello } from '@/api/qdc'
import ConvocazioneAssemblea from '@/components/ConvocazioneAssemblea.vue'
import VerbaleAssemblea from '@/components/VerbaleAssemblea.vue'
import VerbaliCollegati from '@/components/VerbaliCollegati.vue'

import { risposta } from './aiuti'

type Chiamata = { url: string; metodo: string; corpo: string }

function stub(lettura: (url: string, metodo: string) => Response, chiamate: Chiamata[] = []) {
  vi.stubGlobal(
    'fetch',
    vi.fn(async (url: string, opzioni?: RequestInit) => {
      const metodo = opzioni?.method ?? 'GET'
      chiamate.push({ url, metodo, corpo: String(opzioni?.body ?? '') })
      return lettura(url, metodo)
    }),
  )
  return chiamate
}

const luogo = { presso: 'Sede', via: '', civico: '', cap: '', citta: '', provincia: '' }

afterEach(() => vi.unstubAllGlobals())

describe('convocazione dal modello', () => {
  const modello: ConvocazioneModello = {
    dati: { punti: [], prima_il: null, anno_bilancio: 2026, anno_elezione: 2027, luogo },
    mancanti: ['luogo: via'],
    testo: '<p>Con la presente</p>',
    puo_modificare: true,
    prima_il: '2026-11-14T00:00:00+01:00',
  }

  it('propone la mezzanotte, dice cosa manca e chiede gli anni solo se servono', async () => {
    stub(() => risposta(200, modello))
    const w = mount(ConvocazioneAssemblea, { props: { evento: 1 } })
    await flushPromises()
    expect(w.text()).toContain('Per inviarla manca: luogo: via.')
    expect((w.find('input[type=datetime-local]').element as HTMLInputElement).value).toContain(
      'T00:00',
    )
    expect(w.find('#anno-bilancio-1').exists()).toBe(false)
    await w.find('#punto-1-BILANCIO').setValue(true)
    expect(w.find('#anno-bilancio-1').exists()).toBe(true)
    expect(w.find('#anno-elezione-1').exists()).toBe(false)
  })

  it('una volta inviata non si modifica', async () => {
    stub(() => risposta(200, { ...modello, puo_modificare: false, mancanti: [] }))
    const w = mount(ConvocazioneAssemblea, { props: { evento: 1 } })
    await flushPromises()
    expect(w.find('form').exists()).toBe(false)
    expect(w.text()).toContain('Scarica il PDF della convocazione')
  })
})

describe('verbale dell’assemblea dal modello', () => {
  const modello: VerbaleModello = {
    dati: {
      ora_apertura: '',
      ora_chiusura: '',
      scrutatori: [],
      voti: {},
      risultato: '',
      quota_gruppo: '',
      quota_totale: '',
      quota_modalita: '',
      varie: '',
      bilancio_separato: false,
    },
    punti: ['BILANCIO'],
    delibere: { BILANCIO: 'bilancio' },
    mancanti: [],
    testo: '<p>In data odierna</p>',
    candidati_scrutatori: [{ id: 7, nome: 'Anna', cognome: 'Bianchi' }],
    puo_modificare: true,
  }

  it('solo i campi dei punti scelti; con l’unanimità niente numeri', async () => {
    const chiamate = stub(() => risposta(200, structuredClone(modello)))
    const w = mount(VerbaleAssemblea, { props: { evento: 1 } })
    await flushPromises()
    expect(w.find('#risultato-1').exists()).toBe(true)
    expect(w.find('#quota-1').exists()).toBe(false)
    expect(w.find('#varie-1').exists()).toBe(false)
    expect(w.find('#favorevoli-1-BILANCIO').exists()).toBe(true)
    await w.find('#unanimita-1-BILANCIO').setValue(true)
    expect(w.find('#favorevoli-1-BILANCIO').exists()).toBe(false)
    await w.find('#risultato-1').setValue('150.50')
    await w.find('form').trigger('submit')
    await flushPromises()
    const inviato = JSON.parse(chiamate.at(-1)!.corpo)
    expect(inviato.voti.BILANCIO.unanimita).toBe(true)
    expect(inviato.risultato).toBe('150.50')
  })
})

describe('verbali collegati', () => {
  const dati = {
    ora_apertura: '',
    ora_chiusura: '',
    luogo,
    cambia_capi_gruppo: false,
    capi_gruppo: [],
    cambia_rappresentante: false,
    rappresentante: null,
    cambia_sede: false,
    sede: { via: '', civico: '', cap: '', citta: '', provincia: '' },
    varie: '',
  }
  const collegato: VerbaleCollegato = {
    tipo: 'CAPI_GRUPPO',
    nome: 'Verbale Capi Gruppo',
    stato: 'BOZZA',
    definitivo_il: null,
    testo: '<p>Testo</p>',
    dati,
    mancanti: ['almeno una parte'],
    puo_gestire: true,
  }

  it('non mostra nulla a chi non ne ha', async () => {
    stub(() => new Response('{}', { status: 404, headers: { 'Content-Type': 'application/json' } }))
    const w = mount(VerbaliCollegati, { props: { evento: 1 } })
    await flushPromises()
    expect(w.find('section').exists()).toBe(false)
  })

  it('si aggiunge solo se serve e chiede solo le parti scelte', async () => {
    let aggiunto = false
    const chiamate = stub((_, metodo) => {
      if (metodo === 'PUT') {
        aggiunto = true
        return risposta(200, collegato)
      }
      return risposta(200, {
        collegati: aggiunto ? [collegato] : [],
        da_aggiungere: aggiunto ? [] : ['CAPI_GRUPPO'],
        candidati_capi_gruppo: [{ id: 3, nome: 'Rita', cognome: 'Neri' }],
      })
    })
    const w = mount(VerbaliCollegati, { props: { evento: 1 } })
    await flushPromises()
    await w.find('button').trigger('click')
    await flushPromises()
    expect(chiamate.some((c) => c.metodo === 'PUT')).toBe(true)
    expect(w.text()).toContain('Per renderlo definitivo manca: almeno una parte.')
    expect(w.find('#cg-capo-3').exists()).toBe(false)
    await w.find('#cg-cambia-capi').setValue(true)
    expect(w.find('#cg-capo-3').exists()).toBe(true)
    expect(w.find('#cg-sede-via').exists()).toBe(false)
    await w.find('#cg-cambia-sede').setValue(true)
    expect(w.find('#cg-sede-via').exists()).toBe(true)
  })

  it('il testo si chiede solo aprendolo', async () => {
    const definitivo = {
      ...collegato,
      stato: 'DEFINITIVO' as const,
      puo_gestire: false,
      dati: null,
    }
    const chiamate = stub((url) =>
      url.endsWith('/verbali-collegati')
        ? risposta(200, {
            collegati: [{ ...definitivo, testo: '' }],
            da_aggiungere: [],
            candidati_capi_gruppo: [],
          })
        : risposta(200, definitivo),
    )
    const w = mount(VerbaliCollegati, { props: { evento: 1 } })
    await flushPromises()
    expect(chiamate).toHaveLength(1)
    await w.find('button').trigger('click')
    await flushPromises()
    expect(chiamate.at(-1)!.url).toContain('/verbali-collegati/CAPI_GRUPPO')
    expect(w.text()).toContain('Scarica il PDF')
    expect(w.text()).not.toContain('Rendi definitivo')
  })
})
