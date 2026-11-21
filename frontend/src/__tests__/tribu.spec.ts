import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { ErroreApi } from '@/api/http'
import { api, type Profilo, type TotemPersona, type Tribu } from '@/api/qdc'
import TotemPersonaCard from '@/components/TotemPersona.vue'
import { useSessioneStore } from '@/stores/sessione'
import TribuView from '@/views/TribuView.vue'

const collegamento = { RouterLink: { props: ['to'], template: '<a><slot /></a>' } }

const TRIBU: Tribu = {
  descrizione: 'Attorno al fuoco.\n\nPorta il tuo nome.',
  cerimonia: false,
  mio: {
    id: 1,
    nome: 'Castoro Operoso',
    persona: { id: 10, nome: 'Giulia', cognome: 'Rossi' },
    immagine: false,
    in_attesa: false,
    versione: 'a',
  },
  totem: [
    {
      id: 2,
      nome: 'Aquila Saggia',
      persona: { id: 11, nome: 'Anna', cognome: 'Capo' },
      immagine: true,
      in_attesa: false,
      versione: 'b',
    },
    {
      id: 3,
      nome: 'Volpe Astuta',
      persona: null,
      immagine: false,
      in_attesa: false,
      versione: 'c',
    },
  ],
  da_approvare: [],
}

describe('La mia tribù', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    useSessioneStore().profilo = { capo: false } as Profilo
  })
  afterEach(() => vi.restoreAllMocks())

  it('shows the description, one’s own totem first and whose only when known', async () => {
    vi.spyOn(api, 'tribu').mockResolvedValue(TRIBU)
    const pagina = mount(TribuView, { global: { stubs: collegamento } })
    await flushPromises()
    expect(pagina.findAll('.descrizione p').map((p) => p.text())).toEqual([
      'Attorno al fuoco.',
      'Porta il tuo nome.',
    ])
    const nomi = pagina.findAll('li strong').map((s) => s.text())
    expect(nomi).toEqual(['Castoro Operoso', 'Aquila Saggia', 'Volpe Astuta'])
    expect(pagina.find('li').text()).toContain('il tuo')
    expect(pagina.text()).toContain('Anna Capo')
    // No ceremony: not a word about it.
    expect(pagina.text()).not.toContain('cerimonia')
  })

  it('gives the capi the ceremony and the images to approve', async () => {
    useSessioneStore().profilo = { capo: true } as Profilo
    vi.spyOn(api, 'tribu').mockResolvedValue({
      ...TRIBU,
      mio: null,
      cerimonia: true,
      da_approvare: [{ ...TRIBU.mio!, in_attesa: true }],
    })
    vi.spyOn(api, 'cerimoniaTotem').mockResolvedValue({ html: '<p>Il fuoco</p>' })
    const approva = vi.spyOn(api, 'approvaImmagineTotem').mockResolvedValue(TRIBU.mio!)
    vi.spyOn(useSessioneStore(), 'carica').mockResolvedValue()
    const pagina = mount(TribuView, { global: { stubs: collegamento } })
    await flushPromises()
    expect(pagina.find('a[download]').attributes('href')).toBe('/api/v1/tribu/cerimonia.pdf')
    await pagina
      .findAll('button')
      .find((b) => b.text().includes('cerimonia'))!
      .trigger('click')
    await flushPromises()
    expect(pagina.html()).toContain('<p>Il fuoco</p>')
    await pagina
      .findAll('button')
      .find((b) => b.text() === 'Approva')!
      .trigger('click')
    await flushPromises()
    expect(approva).toHaveBeenCalledWith(1)
  })
})

describe('Nome di totem sulla scheda', () => {
  beforeEach(() => setActivePinia(createPinia()))
  afterEach(() => vi.restoreAllMocks())

  const TOTEM: TotemPersona = {
    id: 1,
    nome: 'Castoro Operoso',
    immagine: false,
    in_attesa: true,
    avviso: 'Immagine tolta da un capo: non adatta',
    versione: 'a',
    puo_assegnare: false,
    puo_caricare: true,
    da_approvare: true,
    puo_moderare: false,
  }

  it('shows the name, the notice and the image waiting; the owner does not rename it', async () => {
    vi.spyOn(api, 'totemPersona').mockResolvedValue(TOTEM)
    const scheda = mount(TotemPersonaCard, { props: { persona: 10, nome: 'Giulia' } })
    await flushPromises()
    expect(scheda.text()).toContain('Castoro Operoso')
    expect(scheda.text()).toContain('Immagine tolta da un capo: non adatta')
    expect(scheda.text()).toContain('in attesa di approvazione')
    expect(scheda.text()).toContain('dopo che un capo')
    expect(scheda.findAll('button').map((b) => b.text())).not.toContain('Cambia')
  })

  it('lets the staff assign a name', async () => {
    vi.spyOn(api, 'totemPersona').mockResolvedValue({
      ...TOTEM,
      id: null,
      nome: '',
      in_attesa: false,
      avviso: '',
      puo_assegnare: true,
      puo_caricare: false,
    })
    const assegna = vi.spyOn(api, 'assegnaTotem').mockResolvedValue(TOTEM)
    const scheda = mount(TotemPersonaCard, { props: { persona: 10, nome: 'Giulia' } })
    await flushPromises()
    expect(scheda.text()).toContain('Giulia non ha ancora un nome di totem.')
    await scheda.find('button').trigger('click')
    await scheda.find('input').setValue('Castoro Operoso')
    await scheda.find('form').trigger('submit')
    await flushPromises()
    expect(assegna).toHaveBeenCalledWith(10, 'Castoro Operoso')
    expect(scheda.text()).toContain('Castoro Operoso')
  })

  it('shows nothing to who may not see it', async () => {
    vi.spyOn(api, 'totemPersona').mockRejectedValue(new ErroreApi(404, 'Non trovato.'))
    const scheda = mount(TotemPersonaCard, { props: { persona: 10, nome: 'Giulia' } })
    await flushPromises()
    expect(scheda.html()).toBe('<!--v-if-->')
  })
})
