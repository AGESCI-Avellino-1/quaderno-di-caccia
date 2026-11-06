import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import SpeseView from '@/views/SpeseView.vue'

import { risposta } from './aiuti'

beforeEach(() => setActivePinia(createPinia()))
afterEach(() => vi.unstubAllGlobals())

describe('SpeseView', () => {
  it('empties the receipt field after recording, so the next expense does not seem to have it', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async (_url: string, opzioni?: RequestInit) =>
        opzioni?.method === 'POST' ? risposta(201, {}) : risposta(200, []),
      ),
    )
    const vista = mount(SpeseView)
    await flushPromises()

    const foto = vista.get<HTMLInputElement>('#spesa-foto').element
    const svuotata = vi.fn()
    Object.defineProperty(foto, 'value', { configurable: true, get: () => 'x', set: svuotata })

    await vista.get('#spesa-importo').setValue('12,50')
    await vista.get('#spesa-descrizione').setValue('Colla')
    await vista.get('form').trigger('submit')
    await flushPromises()

    expect(vista.text()).toContain('Spesa registrata')
    expect(svuotata).toHaveBeenCalledWith('')
  })
})
