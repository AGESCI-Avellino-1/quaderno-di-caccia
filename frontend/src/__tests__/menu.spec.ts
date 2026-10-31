import { describe, expect, it } from 'vitest'

import type { Profilo } from '@/api/qdc'
import { gruppiMenu, nomeProgressione, vociProfilo } from '@/navigazione/menu'

const BASE: Profilo = {
  email: 'x@example.invalid',
  persona: null,
  branca: 'generico',
  capo: false,
  capogruppo: false,
  tesoriere: false,
  amministratore_tecnico: false,
  squadriglie_guidate: [],
  squadriglie: [],
  mie_iscrizioni: 0,
  iscrizioni_da_decidere: 0,
  capo_in_attesa: false,
  tutelati: [],
  gestisce_quote: false,
  unita_quote: [],
  vede_cassa: false,
  squadriglie_delegate: [],
  eventi_buonacaccia: false,
  formazione_capi: false,
  puo_impersonare: false,
  impersonazione: null,
  imprese_reparto: null,
  unita_servizio: [],
  ambiente: null,
}

const io = { id: 1, nome: 'Mario', cognome: 'Rossi' }
const titoli = (p: Profilo) => gruppiMenu(p).map((g) => g.titolo)
const voci = (p: Profilo, chiave: string) =>
  gruppiMenu(p)
    .find((g) => g.chiave === chiave)
    ?.voci.map((v) => v.nome) ?? []

describe('menu', () => {
  it('a parent sees the family, the notices and the events, not the group', () => {
    const genitore = {
      ...BASE,
      persona: io,
      tutelati: [{ id: 2, nome: 'Giulia', cognome: 'Rossi' }],
    }
    expect(titoli(genitore)).toEqual(['Bacheca', 'La mia famiglia', 'Attività'])
    expect(voci(genitore, 'famiglia')).toEqual(['Giulia Rossi'])
    expect(vociProfilo(genitore).map((v) => v.nome)).toEqual([
      'Il mio profilo',
      'Privacy',
      'Password e sicurezza',
      'Le mie quote',
    ])
  })

  it('someone with nothing to do sees no groups', () => {
    expect(gruppiMenu(BASE)).toEqual([])
  })

  it('names the Progressione personale after the branch and the setting', () => {
    const ragazzo = { ...BASE, persona: io }
    expect(nomeProgressione({ ...ragazzo, branca: 'eg' })).toBe('Il mio Sentiero')
    expect(nomeProgressione({ ...ragazzo, branca: 'rs' })).toBe('La mia Strada')
    expect(nomeProgressione({ ...ragazzo, branca: 'lc', ambiente: 'GIUNGLA' })).toBe('La mia Pista')
    expect(nomeProgressione({ ...ragazzo, branca: 'lc', ambiente: 'BOSCO' })).toBe(
      'Il mio Sentiero',
    )
    expect(nomeProgressione({ ...ragazzo, branca: 'lc' })).toBe('La mia Pista')
    expect(nomeProgressione({ ...ragazzo, branca: 'capi', capo: true })).toBe(
      'Progressione personale',
    )
  })

  it("describes the child's Progressione with the branch's words", () => {
    const descrizione = (p: Profilo) =>
      gruppiMenu(p).find((g) => g.chiave === 'progressione')?.voci[0]?.descrizione
    const ragazzo = { ...BASE, persona: io }
    expect(descrizione({ ...ragazzo, branca: 'eg' })).toBe('Tappe, mete e impegni')
    expect(descrizione({ ...ragazzo, branca: 'rs' })).toBe('Passi, obiettivi e impegni')
    expect(descrizione({ ...ragazzo, branca: 'lc', ambiente: 'BOSCO' })).toBe(
      'Momenti, voli e specialità',
    )
    expect(descrizione({ ...ragazzo, branca: 'lc', ambiente: 'GIUNGLA' })).toBe(
      'Momenti, prede e specialità',
    )
  })

  it('a capo sees the units they serve under Progressione personale', () => {
    const capo = {
      ...BASE,
      persona: io,
      branca: 'capi' as const,
      capo: true,
      unita_servizio: [
        { id: 7, nome: 'Reparto Antares (N1)', tipo: 'REPARTO', branca: 'EG' },
        { id: 8, nome: 'Clan/Fuoco Hirpinia (T1)', tipo: 'CLAN_FUOCO', branca: 'RS' },
      ],
    }
    expect(voci(capo, 'progressione')).toEqual([
      'Reparto Antares (N1)',
      'Imprese',
      'Passaggi',
      'Clan/Fuoco Hirpinia (T1)',
      'Carta di clan',
      'Passaggi',
    ])
    expect(voci(capo, 'gruppo')).toEqual([
      'Persone',
      'Unità',
      'Incarichi di gruppo',
      'Richieste di iscrizione',
    ])
    expect(titoli(capo)).not.toContain('BuonaStrada')
  })

  it('the capigruppo get BuonaStrada with the counters', () => {
    const capogruppo = {
      ...BASE,
      persona: io,
      capo: true,
      capogruppo: true,
      iscrizioni_da_inserire: 2,
    }
    const gruppo = gruppiMenu(capogruppo, { correzioni: 3 }).find((g) => g.chiave === 'buonastrada')
    expect(gruppo?.voci.map((v) => [v.nome, v.contatore])).toEqual([
      ['Importa da BuonaStrada', undefined],
      ['Iscrizioni da inserire', 2],
      ['Correzioni da inoltrare', 3],
    ])
  })
})
