import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { api, type BabboNatale, type ScambioRegali } from '@/api/qdc'
import BabboNataleView from '@/views/BabboNataleView.vue'
import ScambioRegaliView from '@/views/ScambioRegaliView.vue'

const stubs = { RouterLink: { props: ['to'], template: '<a><slot /></a>' } }
vi.mock('vue-router', async (originale) => ({
  ...(await originale<typeof import('vue-router')>()),
  useRouter: () => ({ push: vi.fn() }),
  useRoute: () => undefined,
}))

const VUOTO: BabboNatale = {
  regali: [],
  nascosti: false,
  puo_organizzare: false,
  scambi: [],
  unita: [],
  puo_tutto_il_gruppo: false,
}

const SCAMBIO: ScambioRegali = {
  id: 4,
  nome: 'Natale in reparto',
  unita: 'Reparto Antares (N1)',
  unita_id: 7,
  consegna_il: '2026-12-20',
  luogo: 'in sede',
  estratto: false,
  chiuso: false,
  partecipanti: 3,
  minimo: 3,
  elenco: [
    { id: 1, nome: 'Giulia', cognome: 'Rossi', avviso: 'app' },
    { id: 2, nome: 'Marco', cognome: 'Bianchi', avviso: 'genitori' },
    { id: 3, nome: 'Sara', cognome: 'Verdi', avviso: 'nessuno' },
  ],
}

describe('Babbo Natale segreto', () => {
  beforeEach(() => setActivePinia(createPinia()))
  afterEach(() => vi.restoreAllMocks())

  it('shows to whom one gives a gift, and the child’s for a parent', async () => {
    vi.spyOn(api, 'babboNatale').mockResolvedValue({
      ...VUOTO,
      regali: [
        {
          scambio: 'Natale in reparto',
          consegna_il: '2026-12-20',
          luogo: 'in sede',
          chi: 'Giulia Rossi',
          proprio: false,
          a_chi: 'Marco Bianchi',
          chiuso: false,
        },
      ],
    })
    const pagina = mount(BabboNataleView, { global: { stubs } })
    await flushPromises()
    expect(pagina.find('[data-regalo]').text()).toContain('Giulia Rossi fa il regalo a')
    expect(pagina.find('[data-a-chi]').text()).toBe('Marco Bianchi')
    expect(pagina.text()).not.toContain('Nuovo scambio')
  })

  it('the organiser sees how each one is told, never to whom', async () => {
    vi.spyOn(api, 'scambio').mockResolvedValue(SCAMBIO)
    vi.spyOn(api, 'candidatiScambio').mockResolvedValue([])
    vi.spyOn(api, 'babboNatale').mockResolvedValue({ ...VUOTO, puo_organizzare: true })
    const pagina = mount(ScambioRegaliView, { props: { id: 4 }, global: { stubs } })
    await flushPromises()
    expect(pagina.text()).toContain('Email ai genitori')
    expect(pagina.text()).toContain('senza account né email')
    const estrai = vi.spyOn(api, 'estraiScambio').mockResolvedValue({
      ...SCAMBIO,
      estratto: true,
      avvisati: { app: 1, genitori: 1, nessuno: 1 },
      elenco: SCAMBIO.elenco.map((p) => ({
        ...p,
        a_chi: p.avviso === 'nessuno' ? 'Giulia Rossi' : null,
      })),
    })
    const bottone = pagina.findAll('button').find((b) => b.text() === 'Estrai')!
    await bottone.trigger('click')
    // A second click confirms: the draw cannot be undone.
    expect(estrai).not.toHaveBeenCalled()
    await pagina
      .findAll('button')
      .find((b) => b.text() === "Conferma l'estrazione")!
      .trigger('click')
    await flushPromises()
    expect(estrai).toHaveBeenCalledWith(4)
    expect(pagina.text()).toContain('Estrazione fatta.')
    expect(pagina.find('[data-partecipanti]').exists()).toBe(true)
    // Only who nobody can tell: the organiser says it aloud.
    expect(pagina.findAll('[data-a-voce]').map((x) => x.text())).toEqual([
      'Diglielo a voce: fa il regalo a Giulia Rossi',
    ])
  })
})
