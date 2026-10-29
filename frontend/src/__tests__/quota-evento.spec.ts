import { flushPromises, mount } from '@vue/test-utils'
import { afterEach, describe, expect, it, vi } from 'vitest'

import QuotaEvento from '@/components/QuotaEvento.vue'

import { risposta } from './aiuti'

afterEach(() => vi.unstubAllGlobals())

const quota = {
  nome: 'Campo estivo',
  totale: '180.00',
  sconto_famiglia: '0.00',
  rate: [
    { descrizione: 'Primo acconto', importo: '100.00', scadenza: '2026-05-01' },
    { descrizione: 'Saldo', importo: '80.00', scadenza: '2026-07-15' },
  ],
}

describe('QuotaEvento', () => {
  it('shows the instalments to the family', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => risposta(200, [])),
    )
    const pannello = mount(QuotaEvento, {
      props: { evento: 5, quota, puoGestire: false, inFamiglia: true },
      global: { stubs: { RouterLink: true } },
    })
    await flushPromises()
    expect(pannello.text()).toContain('Campo estivo: 180,00 €')
    expect(pannello.text()).toContain('Primo acconto: 100,00 € entro il 01/05/2026')
    expect(pannello.text()).not.toContain('Cambia la quota')
  })

  it('lets the capi set the instalments', async () => {
    const corpi: unknown[] = []
    vi.stubGlobal(
      'fetch',
      vi.fn(async (_url: string, opzioni?: RequestInit) => {
        if (opzioni?.method === 'PUT') corpi.push(JSON.parse(opzioni.body as string))
        return risposta(200, [])
      }),
    )
    const pannello = mount(QuotaEvento, {
      props: { evento: 5, quota: null, puoGestire: true, inFamiglia: false },
      global: { stubs: { RouterLink: true } },
    })
    await flushPromises()
    await pannello
      .findAll('button')
      .find((b) => b.text() === 'Fissa una quota')!
      .trigger('click')
    await pannello.get('#quota-nome').setValue('Uscita')
    await pannello.get('#rata-importo-0').setValue('25')
    await pannello.get('#rata-scadenza-0').setValue('2026-04-01')
    await pannello.get('form').trigger('submit')
    await flushPromises()
    expect(corpi).toEqual([
      {
        nome: 'Uscita',
        sconto_famiglia: '0.00',
        rate: [{ descrizione: '', importo: '25.00', scadenza: '2026-04-01' }],
      },
    ])
  })
})
