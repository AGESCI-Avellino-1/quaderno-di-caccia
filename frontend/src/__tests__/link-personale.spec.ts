import { flushPromises, mount } from '@vue/test-utils'
import { afterEach, describe, expect, it, vi } from 'vitest'

import LinkPersonale from '@/components/LinkPersonale.vue'
import AttivaView from '@/views/AttivaView.vue'

const json = (dati: unknown, stato = 200) =>
  new Response(JSON.stringify(dati), {
    status: stato,
    headers: { 'Content-Type': 'application/json' },
  })

afterEach(() => vi.unstubAllGlobals())

describe('LinkPersonale', () => {
  it('is hidden to who may not generate the link', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => json({ detail: 'Persona non trovata.' }, 404)),
    )
    const pannello = mount(LinkPersonale, { props: { persona: 3, nome: 'Leo' } })
    await flushPromises()
    expect(pannello.find('section').exists()).toBe(false)
  })

  it('generates the link and shows it once', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async (_url: string, opzioni?: RequestInit) =>
        opzioni?.method === 'POST'
          ? json({
              link: 'https://qdc.esempio.it/attiva/123/abc',
              scadenza: '2026-12-03T10:00:00Z',
            })
          : json({ attivo_fino_al: null }),
      ),
    )
    const pannello = mount(LinkPersonale, { props: { persona: 3, nome: 'Leo' } })
    await flushPromises()
    await pannello.get('button').trigger('click')
    await flushPromises()
    expect(pannello.text()).toContain('https://qdc.esempio.it/attiva/123/abc')
    expect(pannello.text()).toContain('Genera un link nuovo')
  })
})

describe('AttivaView', () => {
  it('asks birth date and email, then says where the invitation went', async () => {
    const corpi: unknown[] = []
    vi.stubGlobal(
      'fetch',
      vi.fn(async (url: string, opzioni?: RequestInit) => {
        if (opzioni?.method === 'POST') {
          corpi.push(JSON.parse(opzioni.body as string))
          return json({ email: 'leo@example.invalid' })
        }
        expect(url).toBe('/api/v1/attivazione/123/abc')
        return json({ nome: 'Leo' })
      }),
    )
    const vista = mount(AttivaView, { props: { codice: '123', segreto: 'abc' } })
    await flushPromises()
    expect(vista.text()).toContain('Ciao Leo')
    await vista.get('#attiva-nascita').setValue('2011-05-04')
    await vista.get('#attiva-email').setValue('leo@example.invalid')
    await vista.get('form').trigger('submit')
    await flushPromises()
    expect(corpi[0]).toEqual({
      codice_socio: '123',
      segreto: 'abc',
      data_nascita: '2011-05-04',
      email: 'leo@example.invalid',
    })
    expect(vista.text()).toContain("Ti abbiamo mandato un'email a leo@example.invalid")
  })
})
