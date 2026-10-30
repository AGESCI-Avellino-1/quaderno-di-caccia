import { flushPromises, mount } from '@vue/test-utils'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import NotePersona from '@/components/NotePersona.vue'
import RegoleRapporto from '@/components/RegoleRapporto.vue'

import { nuovoDatabase, risposta } from './aiuti'

const nota = (id: number, testo: string, altro: object = {}) => ({
  id,
  tipo: 'STAFF',
  tipo_nome: 'Nota di staff',
  testo,
  autore: 'Anna Capo',
  creata_il: '2026-10-30T10:00:00+01:00',
  aggiornata_il: '2026-10-30T10:00:00+01:00',
  visibile_ragazzo: false,
  visibile_genitori: false,
  visibile_csq: false,
  condivisa_fuori_coca: false,
  puo_modificare: true,
  puo_cambiare_visibilita: true,
  ...altro,
})

const schede = (altro: object = {}) => ({
  note: [
    nota(1, 'Solo per noi'),
    nota(2, 'Per la famiglia', { visibile_genitori: true, condivisa_fuori_coca: true }),
  ],
  scrive: 'STAFF',
  csq_possibile: true,
  regole: null,
  regole_aggiornate_il: null,
  puo_scrivere_regole: true,
  ...altro,
})

type Chiamata = { url: string; metodo: string; corpo: unknown }

function stubFetch(lettura: unknown, chiamate: Chiamata[] = []) {
  vi.stubGlobal(
    'fetch',
    vi.fn(async (url: string, opzioni?: RequestInit) => {
      const metodo = opzioni?.method ?? 'GET'
      if (metodo !== 'GET') {
        chiamate.push({ url, metodo, corpo: JSON.parse((opzioni?.body as string) ?? 'null') })
      }
      return risposta(metodo === 'POST' ? 201 : 200, lettura)
    }),
  )
}

beforeEach(() => nuovoDatabase())
afterEach(() => vi.unstubAllGlobals())

describe('NotePersona', () => {
  it('marks what goes beyond the Co.Ca.', async () => {
    stubFetch(schede())
    const vista = mount(NotePersona, { props: { persona: 7 } })
    await flushPromises()
    expect(vista.text()).toContain('solo la Co.Ca.')
    expect(vista.text()).toContain('la leggono anche i genitori')
  })

  it('writes a note with who reads it', async () => {
    const chiamate: Chiamata[] = []
    stubFetch(schede(), chiamate)
    const vista = mount(NotePersona, { props: { persona: 7 } })
    await flushPromises()
    await vista
      .findAll('button')
      .find((b) => b.text() === 'Nuova nota')!
      .trigger('click')
    await vista.find('#nota-testo').setValue('Ha guidato bene la squadriglia')
    await vista.find('#nota-csq').setValue(true)
    await vista.find('form').trigger('submit')
    await flushPromises()
    expect(chiamate[0]).toMatchObject({
      url: '/api/v1/persone/7/note',
      metodo: 'POST',
      corpo: { testo: 'Ha guidato bene la squadriglia', visibile_csq: true },
    })
  })

  it('hides the choice of the CSQ outside E/G', async () => {
    stubFetch(schede({ csq_possibile: false }))
    const vista = mount(NotePersona, { props: { persona: 7 } })
    await flushPromises()
    await vista
      .findAll('button')
      .find((b) => b.text() === 'Nuova nota')!
      .trigger('click')
    expect(vista.find('#nota-csq').exists()).toBe(false)
  })
})

describe('RegoleRapporto', () => {
  it('shows the rules in evidence', async () => {
    stubFetch(schede({ regole: 'Non consegnarla al padre' }))
    const vista = mount(RegoleRapporto, { props: { persona: 7 } })
    await flushPromises()
    expect(vista.find('.alert.theme-warning').text()).toContain('Non consegnarla al padre')
  })

  it('shows nothing to who may not read them', async () => {
    stubFetch(schede({ regole: null, puo_scrivere_regole: false }))
    const vista = mount(RegoleRapporto, { props: { persona: 7 } })
    await flushPromises()
    expect(vista.text()).toBe('')
  })
})
