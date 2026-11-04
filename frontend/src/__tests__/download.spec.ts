import { flushPromises, mount } from '@vue/test-utils'
import { afterEach, describe, expect, it, vi } from 'vitest'

import type { DocumentoDownload, Download } from '@/api/qdc'
import DownloadView from '@/views/DownloadView.vue'
import PegPubblicoView from '@/views/PegPubblicoView.vue'

import { risposta } from './aiuti'

const documento: DocumentoDownload = {
  id: 1,
  titolo: 'Regolamento',
  descrizione: 'Le regole del campo',
  nome_file: 'regolamento.pdf',
  dimensione: 2048,
  durata: 'SEMPRE',
  anno: null,
  scade_il: null,
  ultimo_giorno: null,
  per_coca: true,
  per_genitori: false,
  unita_ids: [],
  unita_nomi: [],
  unita_ragazzi: false,
  unita_genitori: false,
  aggiornato: false,
  puo_modificare: false,
}

const pagina: Download = {
  documenti: [documento],
  peg: null,
  puo_caricare: false,
  unita: [{ id: 4, nome: 'Reparto Prova (G1)' }],
  anni: [{ anno: 2027, etichetta: '2026/27' }],
  massimo: 20 * 1024 * 1024,
}

type Chiamata = { url: string; metodo: string; corpo: BodyInit | null | undefined }

function stub(dati: unknown, chiamate: Chiamata[] = []) {
  vi.stubGlobal(
    'fetch',
    vi.fn(async (url: string, opzioni?: RequestInit) => {
      chiamate.push({ url, metodo: opzioni?.method ?? 'GET', corpo: opzioni?.body })
      return risposta(200, dati)
    }),
  )
  return chiamate
}

const monta = async () => {
  const w = mount(DownloadView)
  await flushPromises()
  return w
}

afterEach(() => vi.unstubAllGlobals())

describe('Download', () => {
  it('chi legge ha solo il link al file', async () => {
    stub(pagina)
    const w = await monta()
    expect(w.find('a[href="/api/v1/documenti/1/file"]').exists()).toBe(true)
    expect(w.text()).not.toContain('Carica un documento')
    expect(w.text()).not.toContain('Modifica')
    expect(w.text()).not.toContain('Aggiornato')
    expect(w.text()).not.toContain('Progetto Educativo')
  })

  it('mostra «aggiornato» e i comandi di chi può', async () => {
    stub({ ...pagina, documenti: [{ ...documento, aggiornato: true, puo_modificare: true }] })
    const w = await monta()
    expect(w.text()).toContain('Aggiornato')
    expect(w.text()).toContain('Modifica')
  })

  it('il modulo chiede anno o data solo se servono, e ragazzi e genitori con le unità', async () => {
    const chiamate = stub({ ...pagina, puo_caricare: true })
    const w = await monta()
    await w
      .findAll('button')
      .find((b) => b.text() === 'Carica un documento')!
      .trigger('click')
    expect(w.find('#doc-anno').exists()).toBe(false)
    await w.find('#doc-durata').setValue('ANNO')
    expect(w.find('#doc-anno').exists()).toBe(true)
    expect(w.find('#doc-unita-ragazzi').exists()).toBe(false)
    await w.find('#doc-unita-4').setValue(true)
    expect(w.find('#doc-unita-ragazzi').exists()).toBe(true)
    await w.find('#doc-titolo').setValue('Titolo')
    await w.find('#doc-descrizione').setValue('Descrizione')
    await w.find('#doc-anno').setValue(2027)
    await w.find('#doc-unita-genitori').setValue(true)
    await w.find('form').trigger('submit')
    await flushPromises()
    const invio = chiamate.find((c) => c.metodo === 'POST')!
    const corpo = invio.corpo as FormData
    expect(invio.url).toBe('/api/v1/documenti')
    expect(corpo.get('unita')).toBe('4')
    expect(corpo.get('anno')).toBe('2027')
    expect(corpo.get('unita_genitori')).toBe('true')
    expect(corpo.get('unita_ragazzi')).toBe('false')
  })

  it('PEG: storico, versione in vigore ed etichetta', async () => {
    stub({
      ...pagina,
      peg: {
        in_redazione: true,
        puo_gestire: false,
        versioni: [
          {
            id: 2,
            nome_file: 'peg.pdf',
            dimensione: 10,
            ha_testo: false,
            approvato_il: '2026-10-01',
            durata: '2026/2029',
            in_vigore: true,
          },
          {
            id: 1,
            nome_file: 'vecchio.pdf',
            dimensione: 10,
            ha_testo: false,
            approvato_il: '2023-10-01',
            durata: '',
            in_vigore: false,
          },
        ],
      },
    })
    const w = await monta()
    expect(w.text()).toContain('In redazione una nuova versione')
    expect(w.text()).toContain('In vigore')
    expect(w.findAll('a[href^="/api/v1/peg/versioni/"]')).toHaveLength(2)
    expect(w.text()).not.toContain('Carica una nuova versione')
  })
})

describe('pagina pubblica del PEG', () => {
  it('mostra la versione in vigore e l’etichetta', async () => {
    stub({
      gruppo: 'Prova 1',
      in_redazione: true,
      approvato_il: '2026-10-01',
      durata: '2026/2029',
      testo: '<p>Il nostro progetto</p>',
      ha_pdf: true,
    })
    const w = mount(PegPubblicoView)
    await flushPromises()
    expect(w.text()).toContain('Il nostro progetto')
    expect(w.text()).toContain('in redazione')
    expect(w.find('a[href="/api/v1/peg/pubblico.pdf"]').exists()).toBe(true)
  })

  it('senza versione lo dice', async () => {
    stub({
      gruppo: '',
      in_redazione: false,
      approvato_il: null,
      durata: '',
      testo: '',
      ha_pdf: false,
    })
    const w = mount(PegPubblicoView)
    await flushPromises()
    expect(w.text()).toContain('Non è ancora stato pubblicato')
  })
})
