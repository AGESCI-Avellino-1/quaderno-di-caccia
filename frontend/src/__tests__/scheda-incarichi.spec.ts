import { flushPromises, mount } from '@vue/test-utils'
import { afterEach, describe, expect, it, vi } from 'vitest'

import ElencoIncarichi from '@/components/ElencoIncarichi.vue'
import SchedaIncarichiView from '@/views/SchedaIncarichiView.vue'

import { risposta } from './aiuti'

const tipo = (campi: object = {}) => ({
  id: 7,
  nome: 'Referente sicurezza',
  ambito: 'GRUPPO',
  di_servizio: false,
  educativo: false,
  attivo: true,
  usato: false,
  ...campi,
})

const scheda = (puo_modificare: boolean, definiti: object[] = [tipo()]) => ({
  esistenti: [{ nome: 'Capogruppo', ambito: 'GRUPPO', di_servizio: false, educativo: true }],
  definiti,
  puo_modificare,
})

async function monta(dati: object, chiamate: { url: string; opzioni: RequestInit }[] = []) {
  vi.stubGlobal(
    'fetch',
    vi.fn(async (url: string, opzioni: RequestInit = {}) => {
      if (opzioni.method && opzioni.method !== 'GET') {
        chiamate.push({ url, opzioni })
        return opzioni.method === 'DELETE' ? new Response(null, { status: 204 }) : risposta(200, {})
      }
      return risposta(200, dati)
    }),
  )
  const pagina = mount(SchedaIncarichiView)
  await flushPromises()
  return pagina
}

afterEach(() => vi.unstubAllGlobals())

describe('the list of roles', () => {
  it('shows the fixed roles and the group’s own', async () => {
    const pagina = await monta(scheda(true))
    expect(pagina.text()).toContain('Referente sicurezza')
    expect(pagina.text()).toContain('Di gruppo, aggiuntivo, non educativo')
    expect(pagina.text()).toContain('Capogruppo')
  })

  it('offers no change to who is not a capogruppo', async () => {
    const pagina = await monta(scheda(false))
    expect(pagina.text()).not.toContain('Nuovo incarico')
    expect(pagina.findAll('button').map((b) => b.text())).toEqual([])
  })

  it('creates a role with what was chosen', async () => {
    const chiamate: { url: string; opzioni: RequestInit }[] = []
    const pagina = await monta(scheda(true, []), chiamate)
    await pagina.find('button.btn-outline').trigger('click')
    await pagina.find('#incarico-nome').setValue(' Materiale ')
    await pagina.find('#incarico-unita').setValue()
    await pagina.find('#incarico-servizio').setValue()
    expect(pagina.text()).toContain('non dà i permessi dello staff')
    await pagina.find('form').trigger('submit')
    await flushPromises()
    expect(chiamate[0].url).toBe('/api/v1/gruppo/tipi-incarico')
    expect(JSON.parse(chiamate[0].opzioni.body as string)).toEqual({
      nome: 'Materiale',
      ambito: 'UNITA',
      di_servizio: true,
      educativo: true,
      attivo: true,
    })
  })

  it('does not let a role in use change what it is, nor be deleted', async () => {
    const pagina = await monta(scheda(true, [tipo({ usato: true })]))
    expect(pagina.text()).not.toContain('elimina')
    const modifica = pagina.findAll('button').find((b) => b.text() === 'modifica')!
    await modifica.trigger('click')
    expect(pagina.text()).toContain('È già stato assegnato')
    const blocchi = pagina.findAll('fieldset')
    expect(blocchi.map((f) => f.attributes('disabled'))).toEqual(['', ''])
  })

  it('switches a role off keeping the rest', async () => {
    const chiamate: { url: string; opzioni: RequestInit }[] = []
    const pagina = await monta(scheda(true), chiamate)
    await pagina
      .findAll('button')
      .find((b) => b.text() === 'disattiva')!
      .trigger('click')
    await flushPromises()
    expect(chiamate[0].url).toBe('/api/v1/gruppo/tipi-incarico/7')
    expect(JSON.parse(chiamate[0].opzioni.body as string)).toEqual({
      nome: 'Referente sicurezza',
      ambito: 'GRUPPO',
      di_servizio: false,
      educativo: false,
      attivo: false,
    })
  })

  it('asks before deleting a role never used', async () => {
    const chiamate: { url: string; opzioni: RequestInit }[] = []
    const pagina = await monta(scheda(true), chiamate)
    await pagina
      .findAll('button')
      .find((b) => b.text() === 'elimina')!
      .trigger('click')
    expect(chiamate).toEqual([])
    await pagina
      .findAll('button')
      .find((b) => b.text() === 'Sì')!
      .trigger('click')
    await flushPromises()
    expect(chiamate[0].opzioni.method).toBe('DELETE')
  })
})

describe('a role of a type switched off', () => {
  it('can be closed although no longer offered', () => {
    const incarico = {
      id: 1,
      ruolo: 'DEFINITO:7',
      ruolo_nome: 'Referente sicurezza',
      persona: { id: 1, nome: 'Anna', cognome: 'Prova' },
      data_inizio: '2026-10-01',
      data_fine: null,
    }
    const con = (chiudibile: boolean) =>
      mount(ElencoIncarichi, {
        props: {
          incarichi: [{ ...incarico, chiudibile }],
          nomina: [],
          dove: {},
          candidati: async () => [],
        },
        global: { stubs: { Avatar: true } },
      })
    expect(con(true).text()).toContain('chiudi')
    expect(con(false).text()).not.toContain('chiudi')
  })
})
