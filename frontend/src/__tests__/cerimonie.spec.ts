import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { api, type CondizioneVoce, type LibroCerimonie, type VoceLibro } from '@/api/qdc'
import CondizioniVoce from '@/components/CondizioniVoce.vue'
import RegistroVoce from '@/components/RegistroVoce.vue'
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
  unita_condizioni: [],
  incarichi: [],
}

const VOCE: VoceLibro = {
  ...LIBRO.voci[1]!,
  unita_id: 5,
  testo: '<p>Il ponte</p>',
  puo_modificare: false,
  aggiunti: [],
  condizioni: [],
  vede_registro: false,
  partecipanti: [],
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
    expect(pagina.text()).toContain('Scelti a mano (1)')
    await pagina.find('#voce-titolo').setValue('Il ponte')
    await pagina.find('form').trigger('submit')
    await flushPromises()
    expect(salva).toHaveBeenCalledWith(2, {
      titolo: 'Il ponte',
      tipo: 'TRADIZIONE',
      unita_id: 5,
      testo: '<p>Il ponte</p>',
      aggiunti: [9],
      condizioni: [],
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

  describe('condizioni', () => {
    const libro: LibroCerimonie = {
      ...LIBRO,
      puo_scrivere: true,
      unita_condizioni: [{ id: 5, nome: 'Branco (L1)' }],
      incarichi: [{ valore: 'CSQ', nome: 'Capo squadriglia' }],
    }

    function monta(iniziali: CondizioneVoce[][]) {
      const gruppi = { valore: iniziali }
      const pagina = mount(CondizioniVoce, {
        props: {
          libro,
          modelValue: iniziali,
          'onUpdate:modelValue': (v: CondizioneVoce[][]) => (gruppi.valore = v),
        },
      })
      return { pagina, gruppi }
    }

    const pulsante = (pagina: ReturnType<typeof mount>, testo: string) =>
      pagina.findAll('button').find((b) => b.text() === testo)!

    it('aggiunge gruppi in alternativa e condizioni con le prime scelte', async () => {
      const { pagina, gruppi } = monta([])
      expect(pagina.text()).toContain('Nessuna condizione')
      await pulsante(pagina, 'Aggiungi una condizione').trigger('click')
      expect(gruppi.valore).toEqual([[{ tipo: 'unita', unita: 5 }]])
      await pulsante(pagina, 'Aggiungi un altro gruppo, in alternativa').trigger('click')
      expect(gruppi.valore).toHaveLength(2)
      expect(pagina.text()).toContain('oppure')
      // A different kind brings its own choices.
      await pagina.find('[data-condizione] select').setValue('tappa')
      expect(gruppi.valore[0]).toEqual([{ tipo: 'tappa', branca: 'EG', fase: 'SCOPERTA' }])
      await pagina.find('[data-condizione] select').setValue('incarico')
      expect(gruppi.valore[0]).toEqual([{ tipo: 'incarico', ruolo: 'CSQ' }])
    })

    it("togliendo l'ultima condizione toglie il gruppo", async () => {
      const { pagina, gruppi } = monta([[{ tipo: 'totem' }, { tipo: 'promessa' }]])
      expect(pagina.text()).toContain('Valgono tutte insieme')
      await pagina.find('[aria-label="Togli la condizione 1"]').trigger('click')
      expect(gruppi.valore).toEqual([[{ tipo: 'promessa' }]])
      await pagina.find('[aria-label="Togli la condizione 1"]').trigger('click')
      expect(gruppi.valore).toEqual([])
    })
  })

  it('mostra chi la legge oggi con le condizioni scritte', async () => {
    vi.spyOn(api, 'voceLibro').mockResolvedValue({
      ...VOCE,
      puo_modificare: true,
      condizioni: [[{ tipo: 'consiglio_capi' }]],
    })
    vi.spyOn(api, 'libroCerimonie').mockResolvedValue({ ...LIBRO, puo_scrivere: true })
    vi.spyOn(api, 'aggiungibiliVoci').mockResolvedValue([])
    const anteprima = vi
      .spyOn(api, 'anteprimaLettori')
      .mockResolvedValue([{ id: 3, nome: 'Sara', cognome: 'Verdi', unita: 'Reparto (N1)' }])
    const pagina = mount(VoceLibroView, { props: { id: 2 }, global: { stubs } })
    await flushPromises()
    await pagina
      .findAll('button')
      .find((b) => b.text() === 'Modifica')!
      .trigger('click')
    await flushPromises()
    await pagina
      .findAll('button')
      .find((b) => b.text() === 'Chi la legge oggi')!
      .trigger('click')
    await flushPromises()
    expect(anteprima).toHaveBeenCalledWith([[{ tipo: 'consiglio_capi' }]], [], 2)
    expect(pagina.find('[data-anteprima]').text()).toContain('Verdi Sara')
  })

  describe('registro', () => {
    const PARTECIPANTI = [
      { id: 3, nome: 'Sara', cognome: 'Verdi', unita: 'Reparto (N1)', data: '2025-06-14' },
    ]

    it('chi ha partecipato vede gli altri, senza poter cambiare', () => {
      const pagina = mount(RegistroVoce, {
        props: { voce: { ...VOCE, vede_registro: true, partecipanti: PARTECIPANTI } },
      })
      expect(pagina.text()).toContain('Verdi Sara')
      expect(pagina.text()).toContain(new Date('2025-06-14T00:00:00').toLocaleDateString('it-IT'))
      expect(pagina.text()).not.toContain('Segna')
      expect(pagina.text()).not.toContain('Togli')
    })

    it('chi scrive la voce segna e toglie', async () => {
      const voce = { ...VOCE, puo_modificare: true, vede_registro: true, partecipanti: [] }
      vi.spyOn(api, 'segnabiliRegistro').mockResolvedValue([
        { id: 3, nome: 'Sara', cognome: 'Verdi', unita: 'Reparto (N1)' },
      ])
      const segna = vi
        .spyOn(api, 'segnaPartecipanti')
        .mockResolvedValue({ ...voce, partecipanti: PARTECIPANTI })
      const togli = vi.spyOn(api, 'togliPartecipante').mockResolvedValue(voce)
      const pagina = mount(RegistroVoce, { props: { voce } })
      expect(pagina.text()).toContain('Nessuno, per ora.')
      await pagina
        .findAll('button')
        .find((b) => b.text() === "Segna chi l'ha vissuta")!
        .trigger('click')
      await flushPromises()
      await pagina.find('#registro-giorno').setValue('2025-06-14')
      await pagina.find('#registro-3').setValue(true)
      await pagina.find('form').trigger('submit')
      await flushPromises()
      expect(segna).toHaveBeenCalledWith(2, [3], '2025-06-14')
      const aggiornata = pagina.emitted('aggiornata')![0]![0] as VoceLibro
      await pagina.setProps({ voce: aggiornata })
      await pagina.find('[aria-label="Togli Verdi Sara dal registro"]').trigger('click')
      await flushPromises()
      expect(togli).toHaveBeenCalledWith(2, 3)
    })
  })
})
