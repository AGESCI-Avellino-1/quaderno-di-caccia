import { flushPromises, mount } from '@vue/test-utils'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { euro, type Quota, type QuotePersona as DatiQuote } from '@/api/qdc'
import QuotePersona from '@/components/QuotePersona.vue'
import MieQuoteView from '@/views/MieQuoteView.vue'

import { risposta } from './aiuti'

function quota(campi: Partial<Quota>): Quota {
  return {
    id: 1,
    persona_id: 1,
    persona: 'Giulia Rossi',
    descrizione: 'Quota di gruppo 2025/26',
    categoria: 'GRUPPO',
    periodo: '2025-10-01',
    scadenza: '2025-11-30',
    importo: '40.00',
    sconto: '5.00',
    agevolazione: null,
    dovuto: '35.00',
    pagato: '0.00',
    residuo: '35.00',
    annullata: false,
    motivo_annullamento: '',
    arretrata: false,
    ...campi,
  }
}

const datiPersona: DatiQuote = {
  quote: [quota({})],
  famiglia: [quota({ id: 2, persona_id: 2, persona: 'Luca Rossi', residuo: '35.00' })],
  puo_registrare: true,
  puo_gestire: false,
  puo_agevolare: false,
}

afterEach(() => vi.unstubAllGlobals())

describe('euro', () => {
  it('formats amounts the Italian way', () => {
    expect(euro('12345.5').replace(/\s/g, ' ')).toBe('12.345,50 €')
  })
})

describe('QuotePersona', () => {
  it('stays hidden from who may not see the fees', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => risposta(404, { detail: 'Persona non trovata.' })),
    )
    const pannello = mount(QuotePersona, { props: { id: 1 } })
    await flushPromises()
    expect(pannello.html()).not.toContain('Quote')
  })

  it('records one payment over fees of two siblings, one in part', async () => {
    const corpi: unknown[] = []
    vi.stubGlobal(
      'fetch',
      vi.fn(async (url: string, opzioni?: RequestInit) => {
        if (opzioni?.method === 'POST') {
          corpi.push(JSON.parse(opzioni.body as string))
          return risposta(201, {})
        }
        if (url.includes('/pagamenti')) return risposta(200, [])
        return risposta(200, datiPersona)
      }),
    )
    const pannello = mount(QuotePersona, { props: { id: 1 } })
    await flushPromises()
    expect(pannello.text()).toContain('Sconto famiglia 5,00 €')

    await pannello.get('button.theme-primary').trigger('click')
    await pannello.get('#paga-1').setValue(true)
    await pannello.get('#paga-2').setValue(true)
    const importi = pannello.findAll('input[type="number"]')
    await importi[1]!.setValue('10')
    await pannello.get('#paga-chi').setValue('Mario Rossi')
    await pannello.get('form').trigger('submit')
    await flushPromises()

    expect(corpi).toHaveLength(1)
    expect(corpi[0]).toMatchObject({
      metodo: 'CONTANTI',
      versato_da: 'Mario Rossi',
      righe: [
        { quota_id: 1, importo: '35.00' },
        { quota_id: 2, importo: '10.00' },
      ],
    })
    expect(pannello.text()).toContain('la ricevuta è partita per email')
  })
})

describe('MieQuoteView', () => {
  it('shows what is left to pay, the payment link and the receipts', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () =>
        risposta(200, {
          quote: [quota({ agevolazione: { importo: '10.00', decisa_il: '2025-12-01', nota: '' } })],
          pagamenti: [
            {
              id: 7,
              numero: '2025-26/001',
              data: '2026-01-15',
              importo: '20.00',
              metodo: 'BONIFICO',
              metodo_nome: 'Bonifico',
              versato_da: 'Mario Rossi',
              note: '',
              righe: [],
              registrato_da: null,
              ricevuta_inviata_il: null,
              annullato: false,
              motivo_annullamento: '',
              arretrata: false,
            },
          ],
          link_pagamento: 'https://paypal.me/gruppo',
        }),
      ),
    )
    const pagina = mount(MieQuoteView)
    await flushPromises()
    expect(pagina.text()).toContain('Da pagare: 35,00 €')
    expect(pagina.text()).toContain('coperto dal gruppo 10,00 €')
    expect(pagina.get('a[href="https://paypal.me/gruppo"]').text()).toBe('Paga online')
    expect(pagina.find('a[href="/api/v1/pagamenti/7/ricevuta.pdf"]').exists()).toBe(true)
  })
})
