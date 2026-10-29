import { flushPromises, mount, RouterLinkStub } from '@vue/test-utils'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { nomeUnita, valoreLeggibile } from '@/api/qdc'
import CorrezioniPersona from '@/components/CorrezioniPersona.vue'
import CorrezioniView from '@/views/CorrezioniView.vue'

import { risposta } from './aiuti'

const correzione = {
  id: 7,
  campo: 'cellulare',
  etichetta: 'Cellulare',
  valore_precedente: '3330000000',
  valore_corretto: '3331111111',
  stato: 'IN_ATTESA',
  stato_nome: 'Da inoltrare alla segreteria',
  creata_il: '2026-10-29T08:00:00Z',
  richiesta_da: 'Mario Genitore',
  inoltrata_il: null,
  chiusa_il: null,
  motivo_scarto: '',
}

const scheda = (aperta = false) => ({
  campi: [
    {
      campo: 'cellulare',
      etichetta: 'Cellulare',
      tipo: 'testo',
      valore: aperta ? '3331111111' : '3330000000',
      scelte: [],
      correzione: aperta ? correzione : null,
    },
    {
      campo: 'consenso_foto',
      etichetta: 'Consenso per le foto (2B)',
      tipo: 'si_no',
      valore: 'True',
      scelte: [],
      correzione: null,
    },
  ],
  chiuse: [],
})

type Chiamata = { url: string; corpo: unknown }

function stubFetch(lettura: (url: string) => [number, unknown], chiamate: Chiamata[] = []) {
  vi.stubGlobal(
    'fetch',
    vi.fn(async (url: string, opzioni?: RequestInit) => {
      if (opzioni?.method === 'POST') {
        chiamate.push({ url, corpo: JSON.parse((opzioni.body as string) ?? 'null') })
      }
      const [stato, corpo] = lettura(url)
      return risposta(stato, corpo)
    }),
  )
}

afterEach(() => vi.unstubAllGlobals())

describe('valoreLeggibile', () => {
  it('turns stored text into words', () => {
    expect(valoreLeggibile('')).toBe('—')
    expect(valoreLeggibile('True')).toBe('Sì')
    expect(valoreLeggibile('2013-05-04')).toBe('04/05/2013')
    expect(valoreLeggibile('R', [{ valore: 'R', etichetta: 'Rinnovo' }])).toBe('Rinnovo')
  })
})

describe('nomeUnita', () => {
  it('adds the BuonaStrada code; a Co.Ca. without a name shows its type', () => {
    expect(nomeUnita({ nome: 'Hirpinia', codice: 'T1', tipo: 'CLAN_FUOCO' })).toBe(
      'Clan/Fuoco Hirpinia (T1)',
    )
    expect(nomeUnita({ nome: '', codice: 'G1', tipo: 'COMUNITA_CAPI' })).toBe('Comunità Capi (G1)')
    expect(nomeUnita({ nome: 'Arcobaleno', codice: '', tipo: 'NOVIZIATO' })).toBe(
      'Noviziato Arcobaleno',
    )
  })
})

describe('CorrezioniPersona', () => {
  it('stays hidden from whoever may correct nothing', async () => {
    stubFetch(() => [404, { detail: 'Persona non trovata.' }])
    const pannello = mount(CorrezioniPersona, { props: { id: 1 } })
    await flushPromises()
    expect(pannello.html()).not.toContain('BuonaStrada')
  })

  it('corrects a field and tells the page to reload', async () => {
    const chiamate: Chiamata[] = []
    stubFetch(() => [200, scheda(chiamate.length > 0)], chiamate)
    const pannello = mount(CorrezioniPersona, { props: { id: 3 } })
    await flushPromises()
    expect(pannello.text()).toContain('Nessuna correzione in sospeso')

    await pannello.get('button').trigger('click')
    await flushPromises()
    const valore = pannello.get('#correzione-valore')
    expect((valore.element as HTMLInputElement).value).toBe('3330000000')
    await valore.setValue('3331111111')
    await pannello.get('form').trigger('submit')
    await flushPromises()

    expect(chiamate).toEqual([
      { url: '/api/v1/persone/3/correzioni', corpo: { campo: 'cellulare', valore: '3331111111' } },
    ])
    expect(pannello.emitted('cambiato')).toHaveLength(1)
    expect(pannello.text()).toContain('In attesa di BuonaStrada')
    expect(pannello.text()).toContain('Prima: 3330000000')
  })

  it('offers yes/no for consents', async () => {
    stubFetch(() => [200, scheda()])
    const pannello = mount(CorrezioniPersona, { props: { id: 3 } })
    await flushPromises()
    await pannello.get('button').trigger('click')
    await pannello.get('#correzione-campo').setValue('consenso_foto')
    await flushPromises()
    const opzioni = pannello.findAll('#correzione-valore option').map((o) => o.text())
    expect(opzioni).toEqual(['Sì', 'No', 'Non indicato'])
  })
})

describe('CorrezioniView', () => {
  const elenco = [
    {
      ...correzione,
      persona: { id: 3, nome: 'Giulia', cognome: 'Rossi', codice_socio: '9000001' },
    },
  ]

  it('forwards a correction', async () => {
    const chiamate: Chiamata[] = []
    stubFetch(() => [200, chiamate.length ? [] : elenco], chiamate)
    const vista = mount(CorrezioniView, { global: { stubs: { RouterLink: RouterLinkStub } } })
    await flushPromises()
    expect(vista.text()).toContain('Da inoltrare (1)')
    expect(vista.text()).toContain('3330000000 → 3331111111')

    await vista.get('button.theme-primary').trigger('click')
    await flushPromises()
    expect(chiamate).toEqual([{ url: '/api/v1/correzioni/7/inoltra', corpo: null }])
    expect(vista.text()).toContain('Nessuna correzione da gestire')
  })

  it('asks a reason before discarding', async () => {
    const chiamate: Chiamata[] = []
    stubFetch(() => [200, elenco], chiamate)
    const vista = mount(CorrezioniView, { global: { stubs: { RouterLink: RouterLinkStub } } })
    await flushPromises()

    const scarta = vista.findAll('button').find((b) => b.text() === 'Scarta')!
    await scarta.trigger('click')
    await vista.get('input[aria-label="Motivo dello scarto"]').setValue('Numero sbagliato')
    await vista.get('form').trigger('submit')
    await flushPromises()
    expect(chiamate).toEqual([
      { url: '/api/v1/correzioni/7/scarta', corpo: { motivo: 'Numero sbagliato' } },
    ])
  })
})
