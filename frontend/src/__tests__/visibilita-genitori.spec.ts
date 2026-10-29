import { flushPromises, mount } from '@vue/test-utils'
import { afterEach, describe, expect, it, vi } from 'vitest'

import VisibilitaGenitori from '@/components/VisibilitaGenitori.vue'

import { risposta } from './aiuti'

const stato = {
  contatti: true,
  sanitarie: true,
  scheda: true,
  quote: true,
  decisa_il: null,
  genitori: ['Mario Rossi', 'Lucia Rossi'],
}

afterEach(() => vi.unstubAllGlobals())

describe('VisibilitaGenitori', () => {
  it('stays hidden from anyone but the adult member', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => risposta(404, { detail: 'Persona non trovata.' })),
    )
    const pannello = mount(VisibilitaGenitori, { props: { id: 1 } })
    await flushPromises()
    expect(pannello.html()).not.toContain('genitori')
  })

  it('saves the choice by category', async () => {
    const corpi: unknown[] = []
    vi.stubGlobal(
      'fetch',
      vi.fn(async (_url: string, opzioni?: RequestInit) => {
        if (opzioni?.method === 'PUT') corpi.push(JSON.parse(opzioni.body as string))
        return risposta(200, stato)
      }),
    )
    const pannello = mount(VisibilitaGenitori, { props: { id: 1 } })
    await flushPromises()
    expect(pannello.text()).toContain('Mario Rossi e Lucia Rossi')
    expect(pannello.text()).toContain('Finché non scegli, vedono tutto')

    await pannello.get('#visibile-contatti').setValue(false)
    await pannello.get('form').trigger('submit')
    await flushPromises()
    expect(corpi).toEqual([{ contatti: false, sanitarie: true, scheda: true, quote: true }])
  })
})
