import { flushPromises, mount } from '@vue/test-utils'
import { afterEach, describe, expect, it, vi } from 'vitest'

import AbilitaCensito from '@/components/AbilitaCensito.vue'

// A capo with a provisional code let in by a capogruppo (DEC-400).
afterEach(() => vi.unstubAllGlobals())

describe('abilitazione come censito', () => {
  it('asks to confirm, then sends it and tells the page', async () => {
    const chiamate: string[] = []
    vi.stubGlobal(
      'fetch',
      vi.fn(async (url: string, opzioni?: RequestInit) => {
        chiamate.push(`${opzioni?.method ?? 'GET'} ${url}`)
        return new Response(null, { status: 204 })
      }),
    )
    const w = mount(AbilitaCensito, { props: { persona: 4, nome: 'Anna', abilitato: false } })
    await w.get('button').trigger('click')
    expect(w.text()).toContain('Abilitare Anna come censito?')
    await w.get('button.btn-solid').trigger('click')
    await flushPromises()
    expect(chiamate).toEqual(['POST /api/v1/persone/4/censito'])
    expect(w.emitted('cambiato')).toHaveLength(1)

    await w.setProps({ abilitato: true })
    await w.get('button').trigger('click')
    await w.get('button.btn-solid').trigger('click')
    await flushPromises()
    expect(chiamate.at(-1)).toBe('DELETE /api/v1/persone/4/censito')
  })
})
