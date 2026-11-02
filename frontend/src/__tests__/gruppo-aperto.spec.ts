import { afterEach, describe, expect, it } from 'vitest'

import {
  CHIAVE_GRUPPO_APERTO,
  leggiGruppoAperto,
  salvaGruppoAperto,
  totaleContatori,
} from '@/navigazione/gruppoAperto'

describe('gruppi della Home', () => {
  afterEach(() => localStorage.clear())

  it('ricorda solo la chiave del gruppo aperto', () => {
    expect(leggiGruppoAperto()).toBeNull()
    salvaGruppoAperto('economia')
    expect(localStorage.getItem(CHIAVE_GRUPPO_APERTO)).toBe('economia')
    expect(leggiGruppoAperto()).toBe('economia')
    salvaGruppoAperto(null)
    expect(leggiGruppoAperto()).toBeNull()
  })

  it('somma i contatori delle voci per il titolo chiuso', () => {
    const gruppo = {
      chiave: 'gruppo',
      titolo: 'Gruppo',
      icona: 'people' as const,
      voci: [
        { nome: 'Iscrizioni', icona: 'people' as const, to: '/', contatore: 2 },
        { nome: 'Soci', icona: 'people' as const, to: '/' },
        { nome: 'Correzioni', icona: 'people' as const, to: '/', contatore: 3 },
      ],
    }
    expect(totaleContatori(gruppo)).toBe(5)
    expect(totaleContatori({ ...gruppo, voci: [] })).toBe(0)
  })
})
