import { flushPromises, mount } from '@vue/test-utils'
import { afterEach, describe, expect, it, vi } from 'vitest'

import CriteriAmmissione from '@/components/CriteriAmmissione.vue'
import CriteriAmmissioneView from '@/views/CriteriAmmissioneView.vue'

import { risposta } from './aiuti'

const versione = (campi: object = {}) => ({
  id: 4,
  anno: 2027,
  anno_nome: '2026/27',
  valida_dal: '2026-10-01',
  valida_fino_al: '2027-09-30',
  in_vigore: true,
  verbale_numero: '3',
  verbale_data: '2026-10-01',
  ...campi,
})

afterEach(() => vi.unstubAllGlobals())

describe('the criteria anyone can download', () => {
  async function monta(dati: object | null) {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => (dati ? risposta(200, dati) : risposta(500, {}))),
    )
    const blocco = mount(CriteriAmmissione)
    await flushPromises()
    return blocco
  }

  it('lists every version of the year with its validity', async () => {
    const blocco = await monta({
      traccia: false,
      anno_nome: '2026/27',
      anno_corrente_nome: '2026/27',
      versioni: [
        versione({ id: 5, valida_dal: '2027-01-10' }),
        versione({ valida_fino_al: '2027-01-09', in_vigore: false }),
      ],
    })
    const link = blocco.findAll('a').map((a) => a.attributes('href'))
    expect(link).toEqual([
      '/api/v1/criteri-ammissione/pubblici/5.pdf',
      '/api/v1/criteri-ammissione/pubblici/4.pdf',
    ])
    expect(blocco.text()).toContain('al 09/01/2027')
    expect(blocco.findAll('.badge')).toHaveLength(1)
    expect(blocco.text()).not.toContain('traccia')
  })

  it('says last year’s are only an outline', async () => {
    const blocco = await monta({
      traccia: true,
      anno_nome: '2025/26',
      anno_corrente_nome: '2026/27',
      versioni: [versione({ in_vigore: false })],
    })
    expect(blocco.text()).toContain('solo una traccia')
    expect(blocco.text()).toContain('2026/27 verranno caricati a breve')
  })

  it('shows nothing without any, nor when the server does not answer', async () => {
    const vuoto = {
      traccia: false,
      anno_nome: '',
      anno_corrente_nome: '2026/27',
      versioni: [],
    }
    expect((await monta(vuoto)).find('a').exists()).toBe(false)
    expect((await monta(null)).text()).toBe('')
  })
})

describe('writing the criteria', () => {
  const gestione = {
    versioni: [versione()],
    anni: [
      { valore: 2027, nome: '2026/27' },
      { valore: 2028, nome: '2027/28' },
    ],
    unita: [
      { id: 1, nome: 'Reparto' },
      { id: 2, nome: 'Clan' },
    ],
    testo: '<p>Testo di partenza</p>',
    massimi: [{ unita_id: 1, massimo: 45 }],
    verbale_numero: '3',
    verbale_data: '2026-10-01',
  }

  async function monta(chiamate: { url: string; opzioni: RequestInit }[] = []) {
    vi.stubGlobal(
      'fetch',
      vi.fn(async (url: string, opzioni: RequestInit = {}) => {
        if (opzioni.method && opzioni.method !== 'GET') {
          chiamate.push({ url, opzioni })
          if (opzioni.method === 'DELETE') return new Response(null, { status: 204 })
          return risposta(201, versione({ id: 9 }))
        }
        return risposta(200, gestione)
      }),
    )
    const pagina = mount(CriteriAmmissioneView, {
      global: { stubs: { EditorTesto: { template: '<div class="editor" />' } } },
    })
    await flushPromises()
    return pagina
  }

  const bottone = (pagina: Awaited<ReturnType<typeof monta>>, testo: string) =>
    pagina.findAll('button').find((b) => b.text() === testo)!

  it('starts a new version from the latest, and sends only the maxima written', async () => {
    const chiamate: { url: string; opzioni: RequestInit }[] = []
    const pagina = await monta(chiamate)
    await bottone(pagina, 'Nuova versione').trigger('click')
    expect((pagina.find('#massimo-1').element as HTMLInputElement).value).toBe('45')
    await pagina.find('#criteri-dal').setValue('2027-01-10')
    await pagina.find('form').trigger('submit')
    await flushPromises()
    expect(chiamate[0].url).toBe('/api/v1/criteri-ammissione')
    expect(JSON.parse(chiamate[0].opzioni.body as string)).toEqual({
      anno: 2027,
      valida_dal: '2027-01-10',
      verbale_numero: '3',
      verbale_data: '2026-10-01',
      testo: '<p>Testo di partenza</p>',
      massimi: [{ unita_id: 1, massimo: 45 }],
    })
  })

  it('asks before deleting a version', async () => {
    const chiamate: { url: string; opzioni: RequestInit }[] = []
    const pagina = await monta(chiamate)
    await bottone(pagina, 'elimina').trigger('click')
    expect(chiamate).toEqual([])
    await bottone(pagina, 'Sì').trigger('click')
    await flushPromises()
    expect(chiamate[0].opzioni.method).toBe('DELETE')
  })
})
