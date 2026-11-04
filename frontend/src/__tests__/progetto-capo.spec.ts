import { flushPromises, mount } from '@vue/test-utils'
import { afterEach, describe, expect, it, vi } from 'vitest'

import type { ProgettoCapo } from '@/api/qdc'
import ProgettoDelCapo from '@/components/ProgettoDelCapo.vue'

import { risposta } from './aiuti'

const versione = {
  id: 1,
  data: '2026-11-01T10:00:00+01:00',
  ha_testo: true,
  nome_file: '',
  dimensione: 0,
  in_vigore: true,
}
const base: ProgettoCapo = { versioni: [], puo_modificare: false, massimo: 20 * 1024 * 1024 }

type Chiamata = { url: string; metodo: string; corpo: BodyInit | null | undefined }

function stub(lettura: (url: string, metodo: string) => Response, chiamate: Chiamata[] = []) {
  vi.stubGlobal(
    'fetch',
    vi.fn(async (url: string, opzioni?: RequestInit) => {
      const metodo = opzioni?.method ?? 'GET'
      chiamate.push({ url, metodo, corpo: opzioni?.body })
      return lettura(url, metodo)
    }),
  )
  return chiamate
}

const monta = async () => {
  const w = mount(ProgettoDelCapo, {
    props: { persona: 5 },
    global: { stubs: { LettorePdf: true, EditorTesto: true } },
  })
  await flushPromises()
  return w
}

afterEach(() => vi.unstubAllGlobals())

describe('progetto del capo', () => {
  it('chi legge non ha i comandi per scrivere', async () => {
    stub(() => risposta(200, { ...base, versioni: [versione] }))
    const w = await monta()
    expect(w.text()).toContain('In vigore')
    expect(w.text()).toContain('Scarica il PDF')
    expect(w.text()).not.toContain('Nuova versione')
    expect(w.text()).not.toContain('Elimina')
  })

  it('il testo si chiede solo aprendolo', async () => {
    const chiamate = stub((url) =>
      url.endsWith('/testo')
        ? risposta(200, { testo: '<p>Il mio progetto</p>' })
        : risposta(200, { ...base, versioni: [versione] }),
    )
    const w = await monta()
    expect(chiamate).toHaveLength(1)
    await w
      .findAll('button')
      .find((b) => b.text() === 'Leggi')!
      .trigger('click')
    await flushPromises()
    expect(w.text()).toContain('Il mio progetto')
  })

  it('il PDF caricato si apre nella pagina', async () => {
    const pdf = { ...versione, ha_testo: false, nome_file: 'p.pdf', dimensione: 2048 }
    stub(() => risposta(200, { ...base, versioni: [pdf] }))
    const w = await monta()
    await w
      .findAll('button')
      .find((b) => b.text() === 'Leggi')!
      .trigger('click')
    await flushPromises()
    expect(w.findComponent({ name: 'LettorePdf' }).exists()).toBe(true)
  })

  it('il capo inserisce il progetto caricando un PDF', async () => {
    const chiamate = stub((_, metodo) =>
      metodo === 'POST'
        ? risposta(201, { ...base, puo_modificare: true, versioni: [versione] })
        : risposta(200, { ...base, puo_modificare: true }),
    )
    const w = await monta()
    expect(w.text()).toContain('Non è ancora stato inserito')
    await w
      .findAll('button')
      .find((b) => b.text() === 'Inserisci il progetto')!
      .trigger('click')
    await flushPromises()
    await w.find('#progetto-pdf-5').setValue(true)
    expect(w.find('input[type=file]').exists()).toBe(true)
    await w.find('form').trigger('submit')
    await flushPromises()
    expect(chiamate.at(-1)!.metodo).toBe('POST')
    expect(w.text()).toContain('In vigore')
    expect(w.find('form').exists()).toBe(false)
  })
})
