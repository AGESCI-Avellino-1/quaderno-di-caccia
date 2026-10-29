import { flushPromises, mount, RouterLinkStub } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import CodiciIscrizione from '@/components/CodiciIscrizione.vue'
import CompletaIscrizione from '@/components/CompletaIscrizione.vue'
import ModuliIscrizione from '@/components/ModuliIscrizione.vue'
import { useSessioneStore } from '@/stores/sessione'
import IscrizioneView from '@/views/IscrizioneView.vue'
import IscrizioniBuonaStradaView from '@/views/IscrizioniBuonaStradaView.vue'
import IscrizioniView from '@/views/IscrizioniView.vue'

import { risposta } from './aiuti'

const sostituisci = vi.fn()
vi.mock('vue-router', async (originale) => ({
  ...(await originale<typeof import('vue-router')>()),
  useRouter: () => ({ replace: sostituisci, push: vi.fn() }),
}))

type Chiamata = { url: string; metodo: string; corpo: unknown }

function stubFetch(risposte: (url: string, metodo: string) => [number, unknown]) {
  const chiamate: Chiamata[] = []
  vi.stubGlobal(
    'fetch',
    vi.fn(async (url: string, opzioni?: RequestInit) => {
      const metodo = opzioni?.method ?? 'GET'
      if (metodo !== 'GET') {
        chiamate.push({ url, metodo, corpo: JSON.parse((opzioni?.body as string) ?? 'null') })
      }
      const [stato, corpo] = risposte(url, metodo)
      return risposta(stato, corpo)
    }),
  )
  return chiamate
}

beforeEach(() => {
  setActivePinia(createPinia())
  sostituisci.mockReset()
})
afterEach(() => vi.unstubAllGlobals())

describe('IscrizioneView', () => {
  it('a parent without an account sends the request, then signs up', async () => {
    const sessione = useSessioneStore()
    sessione.pronta = true // not logged in
    const chiamate = stubFetch((url, metodo) => {
      if (url.startsWith('/_allauth'))
        return [
          401,
          {
            status: 401,
            data: { flows: [{ id: 'verify_email', is_pending: true }] },
            meta: { is_authenticated: false },
          },
        ]
      if (metodo === 'GET')
        return [200, { codice: 'ABCD2345', unita: 'Reparto (O1)', per_capi: false }]
      return [200, { serve_account: true, richiesta_id: null }]
    })
    const vista = mount(IscrizioneView, { props: { codice: 'abcd2345' } })
    await flushPromises()
    expect(vista.text()).toContain('Reparto (O1)')

    await vista.get('#isc-nome').setValue('Marta')
    await vista.get('#isc-cognome').setValue('Bianco')
    await vista.get('#isc-nascita').setValue('2014-01-01')
    await vista.get('#isc-cf').setValue('BNCMRA14A41A509Q')
    await vista.get('#gen-nome').setValue('Luigi')
    await vista.get('#gen-cognome').setValue('Bianco')
    await vista.get('#gen-cf').setValue('BNCLGU80A01A509Z')
    await vista.get('#acc-email').setValue('luigi@example.invalid')
    await vista.get('#acc-password').setValue('una-password-lunga')
    await vista.get('form').trigger('submit')
    await flushPromises()

    expect(chiamate[0]).toMatchObject({ url: '/api/v1/iscrizione/abcd2345', metodo: 'POST' })
    expect(chiamate[0]!.corpo).toMatchObject({ nome: 'Marta', email: '', genitore_nome: 'Luigi' })
    expect(chiamate[1]).toMatchObject({
      url: '/_allauth/browser/v1/auth/signup',
      corpo: { email: 'luigi@example.invalid', password: 'una-password-lunga' },
    })
    expect(vista.text()).toContain('Richiesta inviata')
  })

  it('the Co.Ca. code registers only the adult themself', async () => {
    useSessioneStore().pronta = true
    stubFetch(() => [200, { codice: 'ABCD2345', unita: 'Comunità Capi (G1)', per_capi: true }])
    const vista = mount(IscrizioneView, { props: { codice: 'ABCD2345' } })
    await flushPromises()
    expect(vista.text()).toContain('Riservata ai capi')
    expect(vista.find('#chi-figlio').exists()).toBe(false)
    expect(vista.find('#gen-cf').exists()).toBe(false)
  })
})

describe('IscrizioniView', () => {
  it('approves with a deadline', async () => {
    const chiamate = stubFetch(() => [
      200,
      [
        {
          id: 4,
          unita: 'Reparto (O1)',
          unita_id: 1,
          stato: 'IN_ATTESA',
          stato_nome: 'In attesa',
          nome: 'Marta',
          cognome: 'Bianco',
          data_nascita: '2014-01-01',
          codice_fiscale: 'BNCMRA14A41A509Q',
          email: '',
          per_minore: true,
          genitore: 'Luigi Bianco',
          richiesta_da: 'luigi@example.invalid',
          creata_il: '2026-10-29T10:00:00Z',
          scadenza_completamento: null,
          motivo_rifiuto: '',
          persona_id: null,
        },
      ],
    ])
    const vista = mount(IscrizioniView)
    await flushPromises()
    expect(vista.text()).toContain('genitore Luigi Bianco')
    await vista
      .findAll('button')
      .find((b) => b.text() === 'Accogli…')!
      .trigger('click')
    await vista.get('#scadenza-4').setValue('2030-01-31')
    await vista.get('form').trigger('submit')
    await flushPromises()
    expect(chiamate[0]).toEqual({
      url: '/api/v1/iscrizioni/4/approva',
      metodo: 'POST',
      corpo: { scadenza_completamento: '2030-01-31' },
    })
  })
})

describe('CodiciIscrizione', () => {
  it('stays hidden from who may not create codes', async () => {
    stubFetch(() => [200, { puo_creare: false, codici: [] }])
    const pannello = mount(CodiciIscrizione, {
      props: { unita: 1 },
      global: { stubs: { RouterLink: RouterLinkStub } },
    })
    await flushPromises()
    expect(pannello.html()).not.toContain('Codici di iscrizione')
  })

  it('creates a code and shows its QR code', async () => {
    const codice = {
      id: 9,
      codice: 'ABCD2345',
      link: 'http://localhost:5173/iscrizione/ABCD2345',
      tipo: 'UNITA',
      tipo_nome: "Per l'unità",
      scadenza: '2030-01-31',
      usi: 0,
      valido: true,
      creato_il: '2026-10-29T10:00:00Z',
    }
    let creato = false
    const chiamate = stubFetch((_url, metodo) => {
      if (metodo === 'POST') {
        creato = true
        return [201, codice]
      }
      return [200, { puo_creare: true, codici: creato ? [codice] : [] }]
    })
    const pannello = mount(CodiciIscrizione, { props: { unita: 1 } })
    await flushPromises()
    await pannello
      .findAll('button')
      .find((b) => b.text() === 'Nuovo codice')!
      .trigger('click')
    await pannello.get('#codice-scadenza').setValue('2030-01-31')
    await pannello.get('form').trigger('submit')
    await flushPromises()
    expect(chiamate[0]).toEqual({
      url: '/api/v1/unita/1/codici-iscrizione',
      metodo: 'POST',
      corpo: { tipo: 'UNITA', scadenza: '2030-01-31' },
    })
    expect(pannello.text()).toContain('ABCD2345')
    expect(pannello.get('img').attributes('src')).toBe('/api/v1/codici-iscrizione/9/qr.svg')
  })
})

describe('CompletaIscrizione', () => {
  it('saves the missing data and reports the new state', async () => {
    const vuoti = {
      sesso: '',
      luogo_nascita: '',
      indirizzo: '',
      civico: '',
      comune: '',
      provincia: '',
      cap: '',
      cellulare_genitore: '',
    }
    const chiamate = stubFetch((_url, metodo) => [
      200,
      { ...vuoti, richiesta: { id: 4, stato: metodo === 'PUT' ? 'COMPLETATA' : 'APPROVATA' } },
    ])
    const modulo = mount(CompletaIscrizione, { props: { id: 4 } })
    await flushPromises()
    expect(modulo.find('#cellulare-4').exists()).toBe(true) // a minor: the parent's mobile
    await modulo.get('#sesso-4').setValue('F')
    await modulo.get('#cap-4').setValue('83100')
    await modulo.get('form').trigger('submit')
    await flushPromises()
    expect(chiamate[0]).toMatchObject({ url: '/api/v1/iscrizioni/4/completamento', metodo: 'PUT' })
    expect(chiamate[0]!.corpo).toMatchObject({ sesso: 'F', cap: '83100' })
    expect(modulo.emitted('cambiata')![0]![0]).toMatchObject({ stato: 'COMPLETATA' })
  })
})

describe('ModuliIscrizione', () => {
  const moduli = (verificati = false) => ({
    allegati: [
      {
        id: 3,
        nome_file: 'consensi.pdf',
        tipo_contenuto: 'application/pdf',
        caricato_il: '2026-10-29T10:00:00Z',
      },
    ],
    verificati_il: verificati ? '2026-10-30T10:00:00Z' : null,
    puo_verificare: true,
  })

  it('lets who approves report the consents', async () => {
    let verificato = false
    const chiamate = stubFetch((url, metodo) => {
      if (url === '/api/v1/modulistica') return [200, { puo_gestire: false, moduli: [] }]
      if (metodo === 'POST') {
        verificato = true
        return [200, { id: 4, stato: 'COMPLETATA', mancanti: [] }]
      }
      return [200, moduli(verificato)]
    })
    const pannello = mount(ModuliIscrizione, { props: { id: 4 } })
    await flushPromises()
    expect(pannello.find('a[href="/api/v1/moduli-firmati/3/file"]').exists()).toBe(true)
    await pannello.get('#consenso_iscrizione-4').setValue(true)
    await pannello.findAll('form')[1]!.trigger('submit')
    await flushPromises()
    expect(chiamate[0]).toEqual({
      url: '/api/v1/iscrizioni/4/verifica-moduli',
      metodo: 'POST',
      corpo: {
        consenso_iscrizione: true,
        consenso_foto: false,
        consenso_commerciale: false,
        consenso_riviste: false,
      },
    })
    expect(pannello.text()).toContain('Moduli verificati dai capi')
    expect(pannello.emitted('cambiata')).toHaveLength(1)
  })
})

describe('IscrizioniBuonaStradaView', () => {
  it('shows the data to copy, the exports and marks as entered', async () => {
    let inserita = false
    const chiamate = stubFetch((_url, metodo) => {
      if (metodo === 'POST') {
        inserita = true
        return [200, { id: 4, stato: 'INSERITA' }]
      }
      return [
        200,
        [
          {
            id: 4,
            colonne: ['Codice provvisorio', 'Cognome', 'Nome', 'Codice fiscale'],
            valori: ['9000000001', 'Bianco', 'Marta', 'BNCMRA14A41A509Q'],
            stato: inserita ? 'INSERITA' : 'COMPLETATA',
          },
        ],
      ]
    })
    const vista = mount(IscrizioniBuonaStradaView)
    await flushPromises()
    expect(vista.text()).toContain('Bianco Marta')
    expect(vista.text()).toContain('BNCMRA14A41A509Q')
    const link = vista.findAll('a').map((a) => a.attributes('href'))
    expect(link).toEqual([
      '/api/v1/iscrizioni-buonastrada.xlsx',
      '/api/v1/iscrizioni-buonastrada.pdf',
    ])
    await vista
      .findAll('button')
      .find((b) => b.text() === 'Segna come inserita')!
      .trigger('click')
    await flushPromises()
    expect(chiamate[0]).toMatchObject({ url: '/api/v1/iscrizioni/4/inserita', metodo: 'POST' })
    expect(vista.text()).toContain("inserita, in attesa dell'importazione")
  })
})
