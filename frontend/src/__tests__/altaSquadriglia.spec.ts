import { flushPromises, mount } from '@vue/test-utils'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { api, type AltaSquadriglia, type MembroAlta } from '@/api/qdc'
import AltaSquadrigliaVue from '@/components/AltaSquadriglia.vue'

const stubs = { RouterLink: { props: ['to'], template: '<a><slot /></a>' } }

const membro = (campi: Partial<MembroAlta>): MembroAlta => ({
  id: 0,
  persona_id: 0,
  nome: '',
  cognome: '',
  unita: 'Reparto (G1)',
  dal: null,
  in_anticamera_dal: null,
  al: null,
  ...campi,
})

const ALTA: AltaSquadriglia = {
  entrati: [membro({ id: 1, persona_id: 11, nome: 'Sara', cognome: 'Verdi', dal: '2023-05-04' })],
  anticamera: [
    membro({
      id: 2,
      persona_id: 12,
      nome: 'Luca',
      cognome: 'Neri',
      in_anticamera_dal: '2026-11-01',
    }),
  ],
  usciti: [
    membro({
      id: 3,
      persona_id: 13,
      nome: 'Marco',
      cognome: 'Bianchi',
      dal: '2022-10-01',
      al: '2024-10-01',
    }),
  ],
  candidati: [membro({ persona_id: 14, nome: 'Giulia', cognome: 'Rossi' })],
  puo_scegliere: true,
  cerimonia: 7,
  alta: { id: 1, nome: 'Aquile', titolo: 'Alta Squadriglia «Aquile»', aperta_il: '2023-01-01' },
  chiuse: [],
  da_copiare: [],
}

afterEach(() => vi.restoreAllMocks())

describe("Alta Squadriglia con l'anticamera", () => {
  it('mostra chi è dentro, chi è in anticamera e la storia', async () => {
    vi.spyOn(api, 'altaSquadriglia').mockResolvedValue(ALTA)
    const pagina = mount(AltaSquadrigliaVue, { props: { reparto: 5 }, global: { stubs } })
    await flushPromises()
    expect(pagina.find('[data-entrati]').text()).toContain('Verdi Sara')
    expect(pagina.find('[data-entrati]').text()).toContain('04/05/2023')
    expect(pagina.find('[data-anticamera]').text()).toContain('Neri Luca')
    expect(pagina.find('[data-usciti]').text()).toContain('Bianchi Marco')
    expect(pagina.text()).toContain("La cerimonia d'ingresso")
  })

  it('dice con quale reparto collegato è condivisa', async () => {
    vi.spyOn(api, 'altaSquadriglia').mockResolvedValue({ ...ALTA, insieme_a: 'Reparto Orsa (M2)' })
    const pagina = mount(AltaSquadrigliaVue, { props: { reparto: 5 }, global: { stubs } })
    await flushPromises()
    expect(pagina.find('[data-insieme]').text()).toContain('Reparto Orsa (M2)')
  })

  it('fa entrare, anche direttamente, con il giorno scelto', async () => {
    vi.spyOn(api, 'altaSquadriglia').mockResolvedValue(ALTA)
    const entra = vi.spyOn(api, 'faiEntrareInAlta').mockResolvedValue(ALTA)
    const anticamera = vi.spyOn(api, 'mettiInAnticamera').mockResolvedValue(ALTA)
    const pagina = mount(AltaSquadrigliaVue, { props: { reparto: 5 }, global: { stubs } })
    await flushPromises()
    await pagina
      .findAll('button')
      .find((b) => b.text() === 'Aggiungi')!
      .trigger('click')
    await pagina.find('#alta-14').setValue(true)
    await pagina.find('#alta-12').setValue(true)
    await pagina.find('#alta-giorno').setValue('2021-04-10')
    await pagina.find('[data-aggiungi]').trigger('submit')
    await flushPromises()
    expect(entra).toHaveBeenCalledWith(5, [14, 12], '2021-04-10')
    // The antechamber takes only who is not in it yet.
    await pagina
      .findAll('button')
      .find((b) => b.text() === 'Aggiungi')!
      .trigger('click')
    await pagina.find('#alta-14').setValue(true)
    await pagina.find('#alta-12').setValue(true)
    await pagina
      .findAll('button')
      .find((b) => b.text() === 'Metti in anticamera')!
      .trigger('click')
    await flushPromises()
    expect(anticamera).toHaveBeenCalledWith(5, [14])
  })

  it('toglie e rimette in anticamera', async () => {
    vi.spyOn(api, 'altaSquadriglia').mockResolvedValue(ALTA)
    const togli = vi.spyOn(api, 'togliDallAlta').mockResolvedValue(ALTA)
    const rimetti = vi.spyOn(api, 'rimettiInAnticamera').mockResolvedValue(ALTA)
    const pagina = mount(AltaSquadrigliaVue, { props: { reparto: 5 }, global: { stubs } })
    await flushPromises()
    await pagina.find('[aria-label="Rimetti Verdi Sara in anticamera"]').trigger('click')
    await pagina.find('[aria-label="Togli Neri Luca dall\'anticamera"]').trigger('click')
    await flushPromises()
    expect(rimetti).toHaveBeenCalledWith(5, 1)
    expect(togli).toHaveBeenCalledWith(5, 2)
  })

  it('cambia nome e chiude, con una conferma', async () => {
    vi.spyOn(api, 'altaSquadriglia').mockResolvedValue(ALTA)
    const rinomina = vi.spyOn(api, 'rinominaAlta').mockResolvedValue(ALTA)
    const chiudi = vi.spyOn(api, 'chiudiAlta').mockResolvedValue(ALTA)
    const pagina = mount(AltaSquadrigliaVue, { props: { reparto: 5 }, global: { stubs } })
    await flushPromises()
    expect(pagina.find('h2').text()).toBe('Alta Squadriglia «Aquile»')
    await pagina
      .findAll('button')
      .find((b) => b.text() === 'Cambia nome')!
      .trigger('click')
    await pagina.find('#alta-nome').setValue('Orsa')
    await pagina.find('[data-rinomina]').trigger('submit')
    await flushPromises()
    expect(rinomina).toHaveBeenCalledWith(5, 'Orsa')
    await pagina
      .findAll('button')
      .find((b) => b.text() === "Chiudi l'Alta Squadriglia")!
      .trigger('click')
    expect(chiudi).not.toHaveBeenCalled()
    await pagina
      .findAll('button')
      .find((b) => b.text() === 'Chiudila')!
      .trigger('click')
    await flushPromises()
    expect(chiudi).toHaveBeenCalledWith(5)
  })

  it('senza Alta Squadriglia la crea, copiando le voci della vecchia', async () => {
    vi.spyOn(api, 'altaSquadriglia').mockResolvedValue({
      ...ALTA,
      alta: null,
      entrati: [],
      anticamera: [],
      candidati: [],
      chiuse: [
        {
          id: 1,
          nome: 'Aquile',
          titolo: 'Alta Squadriglia «Aquile»',
          aperta_il: '2022-10-01',
          chiusa_il: '2026-09-30',
          membri: [ALTA.entrati[0]!],
        },
      ],
      da_copiare: [{ id: 4, titolo: 'Ingresso', cerimonia_ingresso_alta: true }],
    })
    const crea = vi.spyOn(api, 'creaAlta').mockResolvedValue(ALTA)
    const pagina = mount(AltaSquadrigliaVue, { props: { reparto: 5 }, global: { stubs } })
    await flushPromises()
    expect(pagina.find('[data-entrati]').exists()).toBe(false)
    expect(pagina.find('[data-chiuse]').text()).toContain('Verdi Sara')
    await pagina.find('#alta-nuova-nome').setValue('Lupi')
    await pagina.find('#alta-copia-4').setValue(true)
    await pagina.find('[data-nuova-alta]').trigger('submit')
    await flushPromises()
    expect(crea).toHaveBeenCalledWith(5, 'Lupi', [4])
  })

  it('senza permesso solo legge', async () => {
    vi.spyOn(api, 'altaSquadriglia').mockResolvedValue({ ...ALTA, puo_scegliere: false })
    const pagina = mount(AltaSquadrigliaVue, { props: { reparto: 5 }, global: { stubs } })
    await flushPromises()
    expect(pagina.text()).not.toContain('Aggiungi')
    expect(pagina.text()).not.toContain('Togli')
  })
})
