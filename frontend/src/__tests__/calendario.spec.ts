import { afterEach, describe, expect, it } from 'vitest'

import type { EventoCalendario } from '@/api/qdc'
import {
  chiaveGiorno,
  eventiDelGiorno,
  leggiModo,
  leggiVista,
  salvaModo,
  salvaVista,
  settimaneDelMese,
} from '@/eventi/calendario'

const evento = (id: number, inizio: string, fine: string): EventoCalendario => ({
  id,
  titolo: `Evento ${id}`,
  tipo_nome: 'Uscita',
  inizio,
  fine,
  luogo: '',
  annullato: false,
})

describe('mese del calendario', () => {
  it('settimane da lunedì, con i giorni dei mesi vicini', () => {
    // Novembre 2026 comincia di domenica.
    const settimane = settimaneDelMese(2026, 10)
    expect(settimane.every((s) => s.length === 7)).toBe(true)
    expect(chiaveGiorno(settimane[0]![0]!)).toBe('2026-10-26')
    expect(chiaveGiorno(settimane[0]![6]!)).toBe('2026-11-01')
    expect(chiaveGiorno(settimane.at(-1)!.at(-1)!)).toBe('2026-12-06')
    // Febbraio 2027 comincia di lunedì e finisce di domenica: quattro settimane.
    expect(settimaneDelMese(2027, 1)).toHaveLength(4)
  })

  it('un evento di più giorni compare in ognuno', () => {
    const eventi = [
      evento(1, '2026-11-07T09:00:00+01:00', '2026-11-08T17:00:00+01:00'),
      evento(2, '2026-11-08T15:00:00+01:00', '2026-11-08T18:00:00+01:00'),
    ]
    expect(eventiDelGiorno(eventi, new Date(2026, 10, 7)).map((e) => e.id)).toEqual([1])
    expect(eventiDelGiorno(eventi, new Date(2026, 10, 8)).map((e) => e.id)).toEqual([1, 2])
    expect(eventiDelGiorno(eventi, new Date(2026, 10, 9))).toEqual([])
  })
})

describe('scelte ricordate', () => {
  afterEach(() => localStorage.clear())

  it('mese o elenco, e la vista del capo', () => {
    expect(leggiModo()).toBe('mese')
    salvaModo('elenco')
    expect(leggiModo()).toBe('elenco')
    expect(leggiVista()).toBe('')
    salvaVista('coca')
    expect(leggiVista()).toBe('coca')
  })
})
