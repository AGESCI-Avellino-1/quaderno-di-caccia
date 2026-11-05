import { flushPromises, mount } from '@vue/test-utils'
import { afterEach, describe, expect, it, vi } from 'vitest'

import ColoriAnimale from '@/components/ColoriAnimale.vue'
import ImmagineAnimale from '@/components/ImmagineAnimale.vue'
import { impostaImpersonazione } from '@/sicurezza/impersonazione'
import { scaricaAnimaliInUso } from '@/pwa/animali'
import AnimaliSquadrigliaView from '@/views/AnimaliSquadrigliaView.vue'

import { risposta } from './aiuti'

const animale = (campi: object = {}) => ({
  id: 1,
  nome: 'Pantera',
  plurale: 'Pantere',
  tipo: 'GENERALE',
  tipo_nome: 'Generale',
  colore_1: 'Nero',
  significato_1: 'Coraggio',
  colore_2: '',
  significato_2: '',
  colori: [{ nome: 'Nero', codice: '#111111', significato: 'Coraggio' }],
  richiamo: 'Miao',
  immagine: '/animali/pantera.svg',
  simbolo: 'pantera',
  attivo: true,
  usato: false,
  ...campi,
})

const elenco = (puo_modificare: boolean, animali: object[]) => ({
  animali,
  colori: ['Nero', 'Rosso'],
  puo_modificare,
})

afterEach(() => {
  vi.unstubAllGlobals()
  impostaImpersonazione(false)
})

describe('the image next to a patrol’s name', () => {
  it('draws a symbol of the catalog, which takes the theme’s colour', () => {
    const immagine = mount(ImmagineAnimale, {
      props: { animale: { nome: 'Pantera', immagine: '/animali/pantera.svg', simbolo: 'pantera' } },
    })
    expect(immagine.find('use').attributes('href')).toBe('/animali/pantera.svg#pantera')
    expect(immagine.find('img').exists()).toBe(false)
    expect(immagine.attributes('aria-label')).toBe('Pantera')
  })

  it('never puts an uploaded file inside the page', () => {
    const percorso = '/api/v1/animali/immagini/abc.svg'
    const immagine = mount(ImmagineAnimale, {
      props: { animale: { nome: 'Drago', immagine: percorso, simbolo: '' } },
    })
    expect(immagine.find('img').attributes('src')).toBe(percorso)
    expect(immagine.find('svg').exists()).toBe(false)
  })

  it('shows nothing without an animal or an image', () => {
    expect(
      mount(ImmagineAnimale, { props: { animale: null } })
        .find('span')
        .exists(),
    ).toBe(false)
    const senza = { nome: 'Drago', immagine: '', simbolo: '' }
    expect(
      mount(ImmagineAnimale, { props: { animale: senza } })
        .find('span')
        .exists(),
    ).toBe(false)
  })

  it('asks for the file in a long list only when in view', async () => {
    let avvisa: (voci: { isIntersecting: boolean }[]) => void = () => {}
    vi.stubGlobal(
      'IntersectionObserver',
      class {
        constructor(richiamo: typeof avvisa) {
          avvisa = richiamo
        }
        observe() {}
        disconnect() {}
      },
    )
    const immagine = mount(ImmagineAnimale, {
      props: {
        animale: { nome: 'Pantera', immagine: '/animali/pantera.svg', simbolo: 'pantera' },
        pigra: true,
      },
    })
    expect(immagine.find('use').exists()).toBe(false)
    avvisa([{ isIntersecting: true }])
    await immagine.vm.$nextTick()
    expect(immagine.find('use').exists()).toBe(true)
  })
})

describe('the colours', () => {
  it('are drawn and named, with their meaning', () => {
    const colori = mount(ColoriAnimale, {
      props: { colori: [{ nome: 'Nero', codice: '#111111', significato: 'Coraggio' }] },
    })
    expect(colori.text()).toContain('Nero: Coraggio')
    expect(colori.find('.campione').attributes('style')).toContain('background-color')
  })
})

describe('the list of the animals', () => {
  async function monta(dati: object, chiamate: { url: string; opzioni: RequestInit }[] = []) {
    vi.stubGlobal(
      'fetch',
      vi.fn(async (url: string, opzioni: RequestInit = {}) => {
        if (opzioni.method && opzioni.method !== 'GET') {
          chiamate.push({ url, opzioni })
          if (opzioni.method === 'DELETE') return new Response(null, { status: 204 })
          return risposta(200, animale({ id: 9 }))
        }
        return risposta(200, dati)
      }),
    )
    const pagina = mount(AnimaliSquadrigliaView)
    await flushPromises()
    return pagina
  }

  it('groups them and offers no change to who may only read', async () => {
    const pagina = await monta(
      elenco(false, [animale(), animale({ id: 2, nome: 'Orca', tipo: 'NAUTICO' })]),
    )
    expect(pagina.findAll('h2').map((h) => h.text())).toEqual(['Generali', 'Nautici'])
    expect(pagina.text()).toContain('Sq. Pantere')
    expect(pagina.text()).toContain('Richiamo: Miao')
    expect(pagina.findAll('button').map((b) => b.text())).toEqual([])
  })

  it('finds an animal by its name or plural', async () => {
    const pagina = await monta(
      elenco(false, [animale(), animale({ id: 2, nome: 'Volpe', plurale: 'Volpi' })]),
    )
    await pagina.find('input[type=search]').setValue('volpi')
    expect(pagina.text()).toContain('Volpe')
    expect(pagina.text()).not.toContain('Pantera')
  })

  it('creates an animal, then sends its image', async () => {
    const chiamate: { url: string; opzioni: RequestInit }[] = []
    const pagina = await monta(elenco(true, []), chiamate)
    await pagina.find('button.btn-outline').trigger('click')
    await pagina.find('#animale-nome').setValue('Drago')
    await pagina.find('#animale-plurale').setValue('Draghi')
    const file = new File(['<svg/>'], 'drago.svg', { type: 'image/svg+xml' })
    const campo = pagina.find('#animale-immagine')
    Object.defineProperty(campo.element, 'files', { value: [file] })
    await campo.trigger('change')
    await pagina.find('form').trigger('submit')
    await flushPromises()
    expect(chiamate.map((c) => c.url)).toEqual(['/api/v1/animali', '/api/v1/animali/9/immagine'])
    expect(JSON.parse(chiamate[0].opzioni.body as string).plurale).toBe('Draghi')
    expect(chiamate[1].opzioni.body).toBeInstanceOf(FormData)
  })

  it('does not offer to delete an animal in use, only to switch it off', async () => {
    const chiamate: { url: string; opzioni: RequestInit }[] = []
    const pagina = await monta(elenco(true, [animale({ usato: true })]), chiamate)
    const bottoni = pagina.findAll('button')
    expect(bottoni.map((b) => b.text())).not.toContain('elimina')
    await bottoni.find((b) => b.text() === 'disattiva')!.trigger('click')
    await flushPromises()
    expect(JSON.parse(chiamate[0].opzioni.body as string).attivo).toBe(false)
  })
})

describe('the images kept on the device', () => {
  function cacheFinta(presenti: string[]) {
    const add = vi.fn(async () => {})
    vi.stubGlobal('caches', {
      open: async () => ({
        add,
        keys: async () => presenti.map((p) => new Request(`http://localhost${p}`)),
      }),
    })
    return add
  }

  it('are only those in use and still missing', async () => {
    const add = cacheFinta(['/animali/volpe.svg'])
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => risposta(200, ['/animali/pantera.svg', '/animali/volpe.svg'])),
    )
    await scaricaAnimaliInUso()
    expect(add.mock.calls).toEqual([['/animali/pantera.svg']])
  })

  it('are not downloaded while using the app as someone else', async () => {
    const add = cacheFinta([])
    const lettura = vi.fn(async () => risposta(200, ['/animali/pantera.svg']))
    vi.stubGlobal('fetch', lettura)
    impostaImpersonazione(true)
    await scaricaAnimaliInUso()
    expect(lettura).not.toHaveBeenCalled()
    expect(add).not.toHaveBeenCalled()
  })

  it('do not stop the app when the server does not answer', async () => {
    cacheFinta([])
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => {
        throw new TypeError('rete')
      }),
    )
    await expect(scaricaAnimaliInUso()).resolves.toBeUndefined()
  })
})
