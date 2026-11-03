import { flushPromises, mount } from '@vue/test-utils'
import { afterEach, describe, expect, it, vi } from 'vitest'

import PassaggioInCoca from '@/components/PassaggioInCoca.vue'

afterEach(() => vi.unstubAllGlobals())

const vuota = () => new Response(null, { status: 204 })

describe('PassaggioInCoca', () => {
  it('brings the parent in after a confirmation', async () => {
    const chiamate: string[] = []
    vi.stubGlobal(
      'fetch',
      vi.fn(async (url: string, opzioni?: RequestInit) => {
        chiamate.push(`${opzioni?.method} ${url}`)
        return vuota()
      }),
    )
    const pannello = mount(PassaggioInCoca, {
      props: { persona: 4, nome: 'Mario', annullabile: false },
    })
    await pannello.get('button').trigger('click')
    await pannello
      .findAll('button')
      .find((b) => b.text() === 'Porta in Comunità capi')!
      .trigger('click')
    await flushPromises()
    expect(chiamate).toEqual(['POST /api/v1/persone/4/coca'])
    expect(pannello.text()).toContain('Mario è in Comunità capi.')
    expect(pannello.emitted('cambiato')).toHaveLength(1)
  })

  it('undoes the passage while it can', async () => {
    const chiamate: string[] = []
    vi.stubGlobal(
      'fetch',
      vi.fn(async (url: string, opzioni?: RequestInit) => {
        chiamate.push(`${opzioni?.method} ${url}`)
        return vuota()
      }),
    )
    const pannello = mount(PassaggioInCoca, {
      props: { persona: 4, nome: 'Mario', annullabile: true },
    })
    await pannello.get('button').trigger('click')
    await pannello
      .findAll('button')
      .find((b) => b.text() === 'Annulla il passaggio')!
      .trigger('click')
    await flushPromises()
    expect(chiamate).toEqual(['DELETE /api/v1/persone/4/coca'])
    expect(pannello.text()).toContain('resta genitore')
  })
})
