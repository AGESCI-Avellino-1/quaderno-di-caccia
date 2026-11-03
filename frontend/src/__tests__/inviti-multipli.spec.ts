import { flushPromises, mount } from '@vue/test-utils'
import { afterEach, describe, expect, it, vi } from 'vitest'

import InvitiMultipli from '@/components/InvitiMultipli.vue'

const json = (dati: unknown) =>
  new Response(JSON.stringify(dati), { headers: { 'Content-Type': 'application/json' } })

afterEach(() => vi.unstubAllGlobals())

describe('InvitiMultipli', () => {
  it('lists the candidates, sends the ticked ones and says who was skipped', async () => {
    const chiamate: { url: string; corpo: unknown }[] = []
    let inviati = false
    vi.stubGlobal(
      'fetch',
      vi.fn(async (url: string, opzioni?: RequestInit) => {
        chiamate.push({ url, corpo: opzioni?.body ? JSON.parse(opzioni.body as string) : null })
        if (url.startsWith('/api/v1/inviti/molti')) {
          inviati = true
          return json({
            invitati: 1,
            saltati: [{ id: 2, nome: 'Bea', cognome: 'Bi', motivo: 'ha già un invito valido' }],
          })
        }
        return json(
          inviati
            ? []
            : [
                { id: 1, nome: 'Ada', cognome: 'A', email: 'ada@example.invalid' },
                { id: 2, nome: 'Bea', cognome: 'Bi', email: 'bea@example.invalid' },
              ],
        )
      }),
    )
    const inviti = mount(InvitiMultipli, { props: { tipo: 'genitori', unita: 7 } })
    await inviti.get('button').trigger('click')
    await flushPromises()
    expect(chiamate[0]!.url).toBe('/api/v1/inviti/candidati?unita=7&tipo=genitori')
    expect(inviti.text()).toContain('ada@example.invalid')

    await inviti
      .findAll('button')
      .find((b) => b.text() === 'Tutti')!
      .trigger('click')
    await inviti
      .findAll('button')
      .find((b) => b.text().startsWith('Manda'))!
      .trigger('click')
    await flushPromises()
    expect(chiamate.find((c) => c.url === '/api/v1/inviti/molti')!.corpo).toEqual({
      persone: [1, 2],
    })
    expect(inviti.text()).toContain('Inviti mandati: 1.')
    expect(inviti.text()).toContain('Bea Bi: ha già un invito valido')
    expect(inviti.text()).toContain('Nessuno da invitare qui.')
  })
})
