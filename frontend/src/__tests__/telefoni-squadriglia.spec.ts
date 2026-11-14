import { flushPromises, mount, RouterLinkStub } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import TelefonoSquadriglia from '@/components/TelefonoSquadriglia.vue'
import SquadrigliaView from '@/views/SquadrigliaView.vue'

import { nuovoDatabase, risposta } from './aiuti'

const membro = (id: number, nome: string, altro: object = {}) => ({
  id,
  nome,
  cognome: 'Prova',
  incarico: null,
  telefono: null,
  del_genitore: null,
  ...altro,
})

const squadriglia = (sonoCapo: boolean) => ({
  id: 1,
  nome: 'Aquile',
  reparto: 'Reparto Prova',
  sono_capo: sonoCapo,
  membri: [
    membro(1, 'Sara', { incarico: 'Capo squadriglia', telefono: '3331' }),
    membro(2, 'Giulia', { telefono: '3472', del_genitore: 'Mario' }),
    membro(3, 'Ada'),
  ],
  genitori: sonoCapo ? [{ figlio_id: 3, nome: 'Lucia', cognome: 'Prova', telefono: '3489' }] : [],
})

type Chiamata = { url: string; metodo: string; corpo: unknown }

function stubFetch(lettura: unknown, stato = 200, chiamate: Chiamata[] = []) {
  vi.stubGlobal(
    'fetch',
    vi.fn(async (url: string, opzioni?: RequestInit) => {
      const metodo = opzioni?.method ?? 'GET'
      if (metodo !== 'GET') {
        chiamate.push({ url, metodo, corpo: JSON.parse((opzioni?.body as string) ?? 'null') })
      }
      // The patrol's roles have their own answer (DEC-321).
      if (url.endsWith('/incarichi')) {
        return risposta(200, { id: 1, nome: 'Aquile', incarichi: [], nomina: [] })
      }
      return risposta(stato, lettura)
    }),
  )
}

beforeEach(async () => {
  setActivePinia(createPinia()) // the phone buttons read the profile
  await nuovoDatabase()
})
afterEach(() => vi.unstubAllGlobals())

describe('SquadrigliaView', () => {
  it('shows the members phones, the parent number marked', async () => {
    stubFetch([squadriglia(false)])
    const vista = mount(SquadrigliaView, { global: { stubs: { RouterLink: RouterLinkStub } } })
    await flushPromises()
    expect(vista.text()).toContain('Aquile')
    expect(vista.find('a[href="tel:+393472"]').exists()).toBe(true)
    expect(vista.text()).toContain('numero di Mario (genitore)')
    expect(vista.text()).toContain('nessun numero')
    expect(vista.text()).not.toContain('Genitore:')
  })

  it('shows the parents to the capo squadriglia', async () => {
    stubFetch([squadriglia(true)])
    const vista = mount(SquadrigliaView, { global: { stubs: { RouterLink: RouterLinkStub } } })
    await flushPromises()
    expect(vista.text()).toContain('Genitore: Lucia Prova')
    expect(vista.find('a[href="tel:+393489"]').exists()).toBe(true)
  })

  it('says so when the user is in no patrol', async () => {
    stubFetch([])
    const vista = mount(SquadrigliaView, { global: { stubs: { RouterLink: RouterLinkStub } } })
    await flushPromises()
    expect(vista.text()).toContain('Non sei in una squadriglia')
  })
})

describe('TelefonoSquadriglia', () => {
  it('shows the BuonaStrada mobile when the child has one, without choices', async () => {
    stubFetch({ ...impostazione, proprio: '3330000000' })
    const pannello = mount(TelefonoSquadriglia, { props: { id: 2 } })
    await flushPromises()
    expect(pannello.text()).toContain('3330000000')
    expect(pannello.find('#telefono-squadriglia').exists()).toBe(false)
  })

  const impostazione = {
    in_squadriglia: true,
    genitore_id: null,
    famiglia_id: null,
    nascosto: false,
    proprio: '',
    genitori: [{ valore: '9', etichetta: 'Mario Prova (3472)' }],
  }

  it('stays hidden from whoever may not set it', async () => {
    stubFetch({ detail: 'Persona non trovata.' }, 404)
    const pannello = mount(TelefonoSquadriglia, { props: { id: 2 } })
    await flushPromises()
    expect(pannello.html()).not.toContain('Telefono in squadriglia')
  })

  it("chooses a parent's phone and hides it", async () => {
    const chiamate: Chiamata[] = []
    stubFetch(impostazione, 200, chiamate)
    const pannello = mount(TelefonoSquadriglia, { props: { id: 2 } })
    await flushPromises()
    expect(pannello.text()).toContain('Non ha un cellulare suo')

    await pannello.get('select').setValue('9')
    await pannello.get('#telefono-per-tutti').setValue(true)
    await pannello.get('#telefono-nascosto').setValue(true)
    await pannello.get('form').trigger('submit')
    await flushPromises()
    expect(chiamate).toEqual([
      {
        url: '/api/v1/persone/2/telefono-squadriglia',
        metodo: 'PUT',
        corpo: { genitore_id: 9, per_tutti_i_figli: true, nascosto: true },
      },
    ])
  })
})

describe('the animal of a new patrol', () => {
  // DEC-409
  it('its capo squadriglia chooses it, once', async () => {
    const chiamate: Chiamata[] = []
    vi.stubGlobal(
      'fetch',
      vi.fn(async (url: string, opzioni?: RequestInit) => {
        const metodo = opzioni?.method ?? 'GET'
        if (metodo !== 'GET') {
          chiamate.push({ url, metodo, corpo: JSON.parse((opzioni?.body as string) ?? 'null') })
          return risposta(200, { id: 1 })
        }
        if (url.endsWith('/incarichi')) {
          return risposta(200, { id: 1, nome: 'Aquile', incarichi: [], nomina: [] })
        }
        if (url.endsWith('/animali')) {
          return risposta(200, {
            animali: [
              { id: 8, nome: 'Pantera', plurale: 'Pantere', tipo: 'GENERALE', attivo: true },
            ],
            colori: [],
            puo_modificare: false,
          })
        }
        return risposta(200, [
          { ...squadriglia(true), nome: 'Nuova Squadriglia 1', provvisoria: true },
        ])
      }),
    )
    const pagina = mount(SquadrigliaView, { global: { stubs: { RouterLink: RouterLinkStub } } })
    await flushPromises()
    const scelta = pagina.get('select[aria-label="Animale della squadriglia"]')
    await scelta.trigger('focus')
    await flushPromises()
    await scelta.setValue(8)
    await pagina.get('form').trigger('submit')
    await flushPromises()
    expect(chiamate).toEqual([
      { url: '/api/v1/squadriglie/1/animale', metodo: 'POST', corpo: { animale_id: 8 } },
    ])
  })

  it('is not asked to a member who is not the capo squadriglia', async () => {
    stubFetch([{ ...squadriglia(false), provvisoria: true }])
    const pagina = mount(SquadrigliaView, { global: { stubs: { RouterLink: RouterLinkStub } } })
    await flushPromises()
    expect(pagina.find('select[aria-label="Animale della squadriglia"]').exists()).toBe(false)
  })
})
