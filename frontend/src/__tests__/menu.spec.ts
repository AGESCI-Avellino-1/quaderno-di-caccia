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
  it('a parent sees the family, the notices, the events and «Invita nel gruppo»', () => {
    const genitore = {
      ...BASE,
      persona: io,
      tutelati: [{ id: 2, nome: 'Giulia', cognome: 'Rossi' }],
    }
    expect(titoli(genitore)).toEqual(['Bacheca', 'La mia famiglia', 'Il mio gruppo', 'Attività'])
    expect(voci(genitore, 'famiglia')).toEqual(['Giulia Rossi'])
    expect(voci(genitore, 'gruppo')).toEqual(['Invita nel gruppo'])
    expect(vociProfilo(genitore).map((v) => v.nome)).toEqual([
      'Il mio profilo',
      'Privacy e preferenze',
      'Password e sicurezza',
      'Le mie quote',
    ])
  })

  it('someone with nothing to do sees only «Invita nel gruppo»', () => {
    expect(titoli(BASE)).toEqual(['Il mio gruppo'])
    expect(voci(BASE, 'gruppo')).toEqual(['Invita nel gruppo'])
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

  it('only who may refund sees the expenses to refund, with how many wait', () => {
    const capo = { ...BASE, persona: io, branca: 'capi' as const, capo: true }
    expect(voci(capo, 'economia')).not.toContain('Spese da rimborsare')
    const tesoriere = { ...capo, rimborsa_spese: true, spese_da_rimborsare: 2 }
    expect(voci(tesoriere, 'economia')).toContain('Spese da rimborsare')
    const voce = gruppiMenu(tesoriere)
      .find((g) => g.chiave === 'economia')!
      .voci.find((v) => v.nome === 'Spese da rimborsare')!
    expect(voce.contatore).toBe(2)
    expect(voce.to).toBe('/spese-da-rimborsare')
  })

  it('a capo reaches the other units from one entry, after their own', () => {
    const capo = {
      ...BASE,
      persona: io,
      branca: 'capi' as const,
      capo: true,
      unita_servizio: [{ id: 7, nome: 'Reparto Antares (N1)', tipo: 'REPARTO', branca: 'EG' }],
      altre_unita: [{ id: 8, nome: 'Clan/Fuoco Hirpinia (T1)', tipo: 'CLAN_FUOCO', branca: 'RS' }],
    }
    expect(voci(capo, 'progressione')).toEqual([
      'Reparto Antares (N1)',
      'Imprese',
      'Passaggi',
      'Altre unità',
    ])
    expect(voci({ ...capo, altre_unita: [] }, 'progressione')).not.toContain('Altre unità')
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
    // Each unit is one block: with two parallel reparti, whose Passaggi are which is clear.
    const progressione = gruppiMenu(capo).find((g) => g.chiave === 'progressione')!.voci
    expect(progressione.map((v) => v.sezione)).toEqual([
      'Reparto Antares (N1)',
      'Reparto Antares (N1)',
      'Reparto Antares (N1)',
      'Clan/Fuoco Hirpinia (T1)',
      'Clan/Fuoco Hirpinia (T1)',
      'Clan/Fuoco Hirpinia (T1)',
    ])
    expect(progressione[0]!.nomeInSezione).toBe('Progressione')
    expect(voci(capo, 'gruppo')).toEqual([
      'Soci',
      'Genitori',
      'Unità',
      'Organigramma',
      'Richieste di iscrizione',
      'Invita nel gruppo',
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
