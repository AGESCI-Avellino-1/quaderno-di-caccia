import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { api, type LibroCerimonie, type VoceLibro } from '@/api/qdc'
import CerimonieView from '@/views/CerimonieView.vue'
import VoceLibroView from '@/views/VoceLibroView.vue'

const stubs = {
  RouterLink: { props: ['to'], template: '<a><slot /></a>' },
  // The editor is loaded apart: a plain textarea is enough here.
  EditorTesto: {
    props: ['modelValue', 'etichetta'],
    emits: ['update:modelValue'],
    template: '<textarea :value="modelValue" />',
  },
}
const sostituisci = vi.fn()
vi.mock('vue-router', async (originale) => ({
  ...(await originale<typeof import('vue-router')>()),
  useRouter: () => ({ push: vi.fn(), replace: sostituisci }),
}))

const LIBRO: LibroCerimonie = {
  voci: [
    {
      id: 1,
      titolo: 'Cerimonia del totem',
      tipo: 'CERIMONIA',
      unita: 'Tutto il gruppo',
      cerimonia_del_totem: true,
    },
    {
      id: 2,
      titolo: 'Passaggio dal branco',
      tipo: 'TRADIZIONE',
      unita: 'Branco (L1)',
      cerimonia_del_totem: false,
    },
  ],
  puo_scrivere: false,
  unita: [],
  puo_tutto_il_gruppo: false,
}

const VOCE: VoceLibro = {
  ...LIBRO.voci[1]!,
  unita_id: 5,
  testo: '<p>Il ponte</p>',
  puo_modificare: false,
  aggiunti: [],
}

beforeEach(() => setActivePinia(createPinia()))
afterEach(() => vi.restoreAllMocks())

describe('libro delle cerimonie', () => {
  it('divide cerimonie e tradizioni, senza «Nuova voce» per chi legge', async () => {
    vi.spyOn(api, 'libroCerimonie').mockResolvedValue(LIBRO)
    const pagina = mount(CerimonieView, { global: { stubs } })
    await flushPromises()
    expect(pagina.findAll('h2').map((h) => h.text())).toEqual(['Cerimonie', 'Tradizioni'])
    expect(pagina.text()).toContain('Passaggio dal branco')
    expect(pagina.text()).not.toContain('Nuova voce')
  })

  it('mostra il testo e il PDF, senza modifica per chi legge', async () => {
    vi.spyOn(api, 'voceLibro').mockResolvedValue(VOCE)
    const pagina = mount(VoceLibroView, { props: { id: 2 }, global: { stubs } })
    await flushPromises()
    expect(pagina.html()).toContain('<p>Il ponte</p>')
    expect(pagina.find('a[download]').attributes('href')).toBe('/api/v1/cerimonie/2/pdf')
    expect(pagina.text()).not.toContain('Modifica')
    expect(pagina.text()).not.toContain('Elimina')
  })

  it('lo staff modifica la voce e sceglie chi la legge', async () => {
    vi.spyOn(api, 'voceLibro').mockResolvedValue({ ...VOCE, puo_modificare: true, aggiunti: [9] })
    vi.spyOn(api, 'libroCerimonie').mockResolvedValue({
      ...LIBRO,
      puo_scrivere: true,
      unita: [{ id: 5, nome: 'Branco (L1)' }],
    })
    vi.spyOn(api, 'aggiungibiliVoci').mockResolvedValue([
      { id: 9, nome: 'Giulia', cognome: 'Rossi', unita: 'Branco (L1)' },
    ])
    const salva = vi
      .spyOn(api, 'modificaVoceLibro')
      .mockResolvedValue({ ...VOCE, puo_modificare: true })
    const pagina = mount(VoceLibroView, { props: { id: 2 }, global: { stubs } })
    await flushPromises()
    await pagina
      .findAll('button')
      .find((b) => b.text() === 'Modifica')!
      .trigger('click')
    await flushPromises()
    // The group's only for the capigruppo.
    expect(pagina.findAll('#voce-unita option').map((o) => o.text())).toEqual(['Branco (L1)'])
    expect(pagina.text()).toContain('Ragazzi/e che la leggono (1)')
    await pagina.find('#voce-titolo').setValue('Il ponte')
    await pagina.find('form').trigger('submit')
    await flushPromises()
    expect(salva).toHaveBeenCalledWith(2, {
      titolo: 'Il ponte',
      tipo: 'TRADIZIONE',
      unita_id: 5,
      testo: '<p>Il ponte</p>',
      aggiunti: [9],
      cerimonia_del_totem: false,
    })
    expect(pagina.text()).toContain('Voce salvata.')
  })

  it('una voce nuova del capogruppo parte da «Tutto il gruppo»', async () => {
    vi.spyOn(api, 'libroCerimonie').mockResolvedValue({
      ...LIBRO,
      puo_scrivere: true,
      puo_tutto_il_gruppo: true,
      unita: [{ id: 5, nome: 'Branco (L1)' }],
    })
    vi.spyOn(api, 'aggiungibiliVoci').mockResolvedValue([])
    const crea = vi.spyOn(api, 'creaVoceLibro').mockResolvedValue({ ...VOCE, id: 3 })
    const pagina = mount(VoceLibroView, { global: { stubs } })
    await flushPromises()
    await pagina.find('#voce-titolo').setValue('Promessa')
    await pagina.find('form').trigger('submit')
    await flushPromises()
    expect(crea.mock.calls[0]![0]).toMatchObject({ titolo: 'Promessa', unita_id: null })
    expect(sostituisci).toHaveBeenCalledWith({ name: 'voce-libro', params: { id: 3 } })
  })
})
