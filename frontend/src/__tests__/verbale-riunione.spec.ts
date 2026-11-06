import { flushPromises, mount } from '@vue/test-utils'
import { afterEach, describe, expect, it, vi } from 'vitest'

import type { Verbale } from '@/api/qdc'
import VerbaleRiunione from '@/components/VerbaleRiunione.vue'

import { risposta } from './aiuti'

const base: Verbale = {
  tipo: 'SQUADRIGLIA',
  da_modello: false,
  stato: 'BOZZA',
  testo: '',
  non_previsto: false,
  puo_dire_non_previsto: false,
  redattore: null,
  autore_nome: '',
  definitivo_il: null,
  puo_scrivere: false,
  puo_indicare: false,
  puo_riaprire: false,
  puo_stampare: false,
  candidati: [],
  allegati: [],
  massimo_allegato: 20 * 1024 * 1024,
  pezzo: 8,
  zip_possibile: false,
  accessi: null,
  presenti: [],
  puo_cariche: false,
  candidati_cariche: [],
  presidente: '',
  segretari: [],
  presidente_id: null,
  segretari_ids: [],
}

type Chiamata = { url: string; metodo: string; corpo: BodyInit | null | undefined }

function stub(lettura: (url: string, metodo: string) => Response, chiamate: Chiamata[] = []) {
  vi.stubGlobal(
    'fetch',
    vi.fn(async (url: string, opzioni?: RequestInit) => {
      const metodo = opzioni?.method ?? 'GET'
      chiamate.push({ url, metodo, corpo: opzioni?.body })
      return lettura(url, metodo)
    }),
  )
  return chiamate
}

const monta = async () => {
  const pagina = mount(VerbaleRiunione, {
    props: { evento: 5 },
    global: { stubs: { EditorTesto: { template: '<textarea></textarea>' } } },
  })
  await flushPromises()
  return pagina
}

afterEach(() => vi.unstubAllGlobals())

describe('VerbaleRiunione', () => {
  it('non si vede se il server non lo mostra', async () => {
    stub(() => risposta(404, { detail: 'Non trovato.' }))
    const pagina = await monta()
    expect(pagina.find('section').exists()).toBe(false)
  })

  it('chiede il testo solo quando lo si apre', async () => {
    const chiamate = stub((url) =>
      risposta(200, {
        ...base,
        stato: 'DEFINITIVO',
        puo_stampare: true,
        testo: url.includes('testo=true') ? '<p>Si è deciso.</p>' : '',
      }),
    )
    const pagina = await monta()
    expect(chiamate.map((c) => c.url)).toEqual(['/api/v1/eventi/5/verbale'])
    expect(pagina.text()).toContain('Definitivo')
    expect(pagina.text()).not.toContain('Si è deciso')
    expect(pagina.find('a[href="/api/v1/eventi/5/verbale.pdf"]').exists()).toBe(true)
    await pagina.find('button').trigger('click')
    await flushPromises()
    expect(chiamate[1]!.url).toBe('/api/v1/eventi/5/verbale?testo=true')
    expect(pagina.text()).toContain('Si è deciso')
    expect(pagina.find('textarea').exists()).toBe(false)
  })

  it('chi può scrivere ha l editor, chi indica anche il resto', async () => {
    stub(() =>
      risposta(200, {
        ...base,
        puo_scrivere: true,
        puo_indicare: true,
        candidati: [{ id: 2, nome: 'Alice', cognome: 'Marino' }],
      }),
    )
    const pagina = await monta()
    expect(pagina.text()).toContain('Chi lo scrive')
    await pagina.find('button').trigger('click')
    await flushPromises()
    expect(pagina.text()).toContain('Rendi definitivo')
    expect(pagina.text()).toContain('Salva la bozza')
  })

  it('offre i dati da inserire e mostra l anteprima senza salvare', async () => {
    HTMLDialogElement.prototype.showModal = vi.fn()
    const chiamate = stub((url, metodo) =>
      url.endsWith('/anteprima') && metodo === 'POST'
        ? risposta(200, { testo: '<p>6 marzo 2026</p>', mancanti: ['la partita IVA del gruppo'] })
        : risposta(200, { ...base, puo_scrivere: true, segnaposto: ['[Data]', '[Luogo]'] }),
    )
    const pagina = await monta()
    await pagina.get('section button').trigger('click')
    await flushPromises()

    expect(pagina.findAll('button').map((b) => b.text())).toEqual(
      expect.arrayContaining(['[Data]', '[Luogo]', 'Anteprima']),
    )
    await pagina
      .findAll('button')
      .find((b) => b.text() === 'Anteprima')!
      .trigger('click')
    await flushPromises()

    expect(HTMLDialogElement.prototype.showModal).toHaveBeenCalled()
    expect(pagina.get('dialog').text()).toContain('6 marzo 2026')
    expect(pagina.get('dialog').text()).toContain('la partita IVA del gruppo')
    expect(chiamate.some((c) => c.metodo === 'PUT')).toBe(false)
  })

  it('prima del definitivo dice cosa resterà vuoto', async () => {
    stub((url, metodo) =>
      url.endsWith('/anteprima') && metodo === 'POST'
        ? risposta(200, { testo: '', mancanti: ['la partita IVA del gruppo'] })
        : risposta(200, {
            ...base,
            puo_scrivere: true,
            puo_indicare: true,
            segnaposto: ['[Data]'],
          }),
    )
    const pagina = await monta()
    await pagina.get('section button').trigger('click')
    await flushPromises()
    await pagina
      .findAll('button')
      .find((b) => b.text() === 'Rendi definitivo')!
      .trigger('click')
    await flushPromises()

    expect(pagina.text()).toContain('Resteranno vuoti: la partita IVA del gruppo.')
  })

  it('il redattore scrive ma non rende definitivo', async () => {
    stub(() =>
      risposta(200, {
        ...base,
        puo_scrivere: true,
        redattore: { id: 3, nome: 'Ada', cognome: 'Prova' },
      }),
    )
    const pagina = await monta()
    expect(pagina.text()).toContain('Lo scrive Ada Prova')
    await pagina.find('button').trigger('click')
    await flushPromises()
    expect(pagina.text()).toContain('Salva la bozza')
    expect(pagina.text()).not.toContain('Rendi definitivo')
  })

  it('carica un file a pezzi, nell ordine', async () => {
    const chiamate = stub((url, metodo) => {
      if (metodo === 'POST' && url.endsWith('/allegati')) return risposta(201, { id: 9 })
      if (url.endsWith('/pezzo')) return risposta(200, { ricevuti: 0, completo: false })
      return risposta(200, { ...base, puo_scrivere: true })
    })
    const pagina = await monta()
    const campo = pagina.find('input[type="file"]')
    Object.defineProperty(campo.element, 'files', {
      value: [new File(['0123456789abcdefghij'], 'ordine.pdf')],
      configurable: true,
    })
    await campo.trigger('change')
    await flushPromises()
    const pezzi = chiamate.filter((c) => c.url === '/api/v1/allegati-verbale/9/pezzo')
    expect(pezzi.map((c) => (c.corpo as FormData).get('inizio'))).toEqual(['0', '8', '16'])
    expect(((pezzi[2]!.corpo as FormData).get('file') as File).size).toBe(4)
  })

  it('dice perché un caricamento non riesce', async () => {
    stub((url, metodo) =>
      metodo === 'POST'
        ? risposta(400, { detail: 'Il file è troppo grande: il massimo è 20 MB.' })
        : risposta(200, { ...base, puo_scrivere: true }),
    )
    const pagina = await monta()
    const campo = pagina.find('input[type="file"]')
    Object.defineProperty(campo.element, 'files', {
      value: [new File(['x'], 'a.pdf')],
      configurable: true,
    })
    await campo.trigger('change')
    await flushPromises()
    expect(pagina.text()).toContain('troppo grande')
  })

  it('all assemblea sceglie presidente e segretari tra i presenti', async () => {
    const chiamate = stub(() =>
      risposta(200, {
        ...base,
        tipo: 'SOCI',
        puo_scrivere: true,
        puo_cariche: true,
        candidati_cariche: [
          { id: 2, nome: 'Alice', cognome: 'Marino' },
          { id: 3, nome: 'Ada', cognome: 'Prova' },
        ],
        presenti: [{ nome: 'Alice Marino', qualita: 'Socio', voto: true }],
      }),
    )
    const pagina = await monta()
    await pagina.find('button').trigger('click')
    await flushPromises()
    expect(pagina.text()).toContain('con diritto di voto')
    await pagina.find('select').setValue(2)
    await pagina.find('input[value="3"]').setValue(true)
    const moduli = pagina.findAll('form')
    await moduli.find((m) => m.text().includes('Salva presidente'))!.trigger('submit')
    await flushPromises()
    const inviata = chiamate.find((c) => c.url.endsWith('/cariche'))!
    expect(JSON.parse(inviata.corpo as string)).toEqual({ presidente_id: 2, segretari_ids: [3] })
  })

  it('senza presenti chiede di segnarle prima', async () => {
    stub(() => risposta(200, { ...base, tipo: 'SOCI', puo_scrivere: true, puo_cariche: true }))
    const pagina = await monta()
    await pagina.find('button').trigger('click')
    await flushPromises()
    expect(pagina.text()).toContain('segna prima le presenze')
  })

  it('riapre chiedendo il motivo', async () => {
    const chiamate = stub((url) =>
      risposta(200, {
        ...base,
        stato: url.endsWith('/riapri') ? 'BOZZA' : 'DEFINITIVO',
        puo_riaprire: !url.endsWith('/riapri'),
        puo_scrivere: url.endsWith('/riapri'),
      }),
    )
    const pagina = await monta()
    await pagina
      .findAll('button')
      .find((b) => b.text() === 'Riapri il verbale')!
      .trigger('click')
    await pagina.find('input[maxlength="300"]').setValue('Un errore')
    await pagina.find('form').trigger('submit')
    await flushPromises()
    const riapertura = chiamate.find((c) => c.url.endsWith('/riapri'))!
    expect(JSON.parse(riapertura.corpo as string)).toEqual({ motivo: 'Un errore' })
    expect(pagina.text()).toContain('Bozza')
  })
})
