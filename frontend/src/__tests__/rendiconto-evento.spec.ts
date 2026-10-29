import { flushPromises, mount } from '@vue/test-utils'
import { afterEach, describe, expect, it, vi } from 'vitest'

import RendicontoEvento from '@/components/RendicontoEvento.vue'

import { risposta } from './aiuti'

afterEach(() => vi.unstubAllGlobals())

const conti = {
  budget: null,
  entrate: '100.00',
  uscite: '40.00',
  saldo: '60.00',
  quote_dovute: '300.00',
  quote_incassate: '100.00',
  agevolazioni: '50.00',
  puo_gestire: true,
}

describe('RendicontoEvento', () => {
  it('stays hidden from who may not see the money', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => risposta(403, {})),
    )
    const pannello = mount(RendicontoEvento, { props: { evento: 5, campo: true } })
    await flushPromises()
    expect(pannello.html()).not.toContain('Budget')
  })

  it('sends two values of three, the app computes the third', async () => {
    const corpi: unknown[] = []
    vi.stubGlobal(
      'fetch',
      vi.fn(async (_url: string, opzioni?: RequestInit) => {
        if (opzioni?.method === 'PUT') corpi.push(JSON.parse(opzioni.body as string))
        return risposta(200, conti)
      }),
    )
    const pannello = mount(RendicontoEvento, { props: { evento: 5, campo: true } })
    await flushPromises()
    expect(pannello.text()).toContain('Agevolazioni (contributo dalla cassa)')
    await pannello
      .findAll('button')
      .find((b) => b.text() === 'Fissa il budget')!
      .trigger('click')
    await pannello.get('#budget-quota').setValue('150')
    await pannello.get('#budget-contributo').setValue('100')
    await pannello.get('form').trigger('submit')
    await flushPromises()
    expect(corpi).toEqual([
      { quota: '150.00', contributo: '100.00', totale: null, quota_staff: '0.00' },
    ])
  })
})
