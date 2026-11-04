import { flushPromises, mount } from '@vue/test-utils'
import { afterEach, describe, expect, it, vi } from 'vitest'

import type { Convocazione } from '@/api/qdc'
import ConvocazioneRiunione from '@/components/ConvocazioneRiunione.vue'

import { risposta } from './aiuti'

const base: Convocazione = {
  da_modello: false,
  convocata_il: null,
  puo_indicare_presenze: false,
  presenze_da: null,
  candidati_presenze: [],
  allegati: [{ id: 3, nome_file: 'programma.pdf', dimensione: 2048, di_convocazione: true }],
  puo_gestire: false,
  puo_inviare: false,
  massimo_allegato: 1024,
  pezzo: 8,
}

function stub(lettura: (url: string, metodo: string) => Response) {
  const chiamate: { url: string; metodo: string }[] = []
  vi.stubGlobal(
    'fetch',
    vi.fn(async (url: string, opzioni?: RequestInit) => {
      const metodo = opzioni?.method ?? 'GET'
      chiamate.push({ url, metodo })
      return lettura(url, metodo)
    }),
  )
  return chiamate
}

const monta = async () => {
  const pagina = mount(ConvocazioneRiunione, { props: { evento: 5 } })
  await flushPromises()
  return pagina
}

afterEach(() => vi.unstubAllGlobals())

describe('ConvocazioneRiunione', () => {
  it('non si vede se il server non la mostra', async () => {
    stub(() => risposta(404, { detail: 'Non trovato.' }))
    expect((await monta()).find('section').exists()).toBe(false)
  })

  it('il genitore legge i documenti senza poter cambiare nulla', async () => {
    stub(() => risposta(200, { ...base, convocata_il: '2026-11-04T10:00:00Z' }))
    const pagina = await monta()
    expect(pagina.find('a[href="/api/v1/allegati-verbale/3"]').text()).toBe('programma.pdf')
    expect(pagina.find('input[type="file"]').exists()).toBe(false)
    expect(pagina.text()).not.toContain('Invia la convocazione')
    expect(pagina.text()).not.toContain('togli')
  })

  it('invia la convocazione dopo la conferma', async () => {
    const chiamate = stub((_url, metodo) =>
      risposta(200, {
        ...base,
        puo_gestire: true,
        puo_inviare: metodo === 'GET',
        convocata_il: metodo === 'POST' ? '2026-11-04T10:00:00Z' : null,
      }),
    )
    const pagina = await monta()
    await pagina
      .findAll('button')
      .find((b) => b.text() === 'Invia la convocazione')!
      .trigger('click')
    expect(chiamate.filter((c) => c.metodo === 'POST')).toEqual([])
    await pagina
      .findAll('button')
      .find((b) => b.text() === 'Sì')!
      .trigger('click')
    await flushPromises()
    expect(chiamate.at(-1)).toEqual({
      url: '/api/v1/eventi/5/convocazione/invia',
      metodo: 'POST',
    })
    expect(pagina.text()).toContain('Inviata il')
    expect(pagina.text()).not.toContain('Invia la convocazione')
  })

  it('il capogruppo indica chi segna le presenze', async () => {
    const chiamate = stub(() =>
      risposta(200, {
        ...base,
        puo_gestire: true,
        puo_indicare_presenze: true,
        candidati_presenze: [{ id: 4, nome: 'Rino', cognome: 'Rover' }],
      }),
    )
    const pagina = await monta()
    await pagina.find('select').setValue(4)
    await pagina.find('form').trigger('submit')
    await flushPromises()
    expect(chiamate.at(-1)).toEqual({
      url: '/api/v1/eventi/5/convocazione/presenze',
      metodo: 'PUT',
    })
  })

  it('aggiunge un documento a pezzi', async () => {
    const chiamate = stub((url, metodo) => {
      if (metodo === 'POST' && url.endsWith('/allegati')) return risposta(201, { id: 9 })
      if (url.endsWith('/pezzo')) return risposta(200, { ricevuti: 0, completo: false })
      return risposta(200, { ...base, puo_gestire: true })
    })
    const pagina = await monta()
    const campo = pagina.find('input[type="file"]')
    Object.defineProperty(campo.element, 'files', {
      value: [new File(['0123456789'], 'b.pdf')],
      configurable: true,
    })
    await campo.trigger('change')
    await flushPromises()
    expect(chiamate.map((c) => c.url)).toContain('/api/v1/eventi/5/convocazione/allegati')
    expect(chiamate.filter((c) => c.url.endsWith('/pezzo')).length).toBe(2)
  })
})
