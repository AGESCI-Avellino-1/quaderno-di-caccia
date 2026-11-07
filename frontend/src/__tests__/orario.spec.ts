import { describe, expect, it } from 'vitest'

import { dataEOra, quandoEvento } from '@/eventi/orario'

const UN_GIORNO = { inizio: '2026-12-04T15:00:00', fine: '2026-12-04T17:30:00' }
const PIU_GIORNI = { inizio: '2026-12-04T15:00:00', fine: '2026-12-06T17:00:00' }

describe('orario degli eventi', () => {
  it('shows only the day when no hour is known', () => {
    const senza = { senza_ora_inizio: true, senza_ora_fine: true }
    const testo = quandoEvento({ ...UN_GIORNO, ...senza })
    expect(testo).toContain('4 dic')
    expect(testo).not.toContain(':')
  })

  it('a single known hour says which one', () => {
    expect(quandoEvento({ ...UN_GIORNO, senza_ora_fine: true })).toMatch(/dalle 15:00$/)
    expect(quandoEvento({ ...UN_GIORNO, senza_ora_inizio: true })).toMatch(/fino alle 17:30$/)
  })

  it('stays as before when the hours are known', () => {
    expect(quandoEvento(UN_GIORNO)).toMatch(/15:00–17:30$/)
    expect(quandoEvento(PIU_GIORNI)).toMatch(/^dal .* al /)
    expect(quandoEvento(PIU_GIORNI, true)).toContain('15:00')
    expect(quandoEvento(PIU_GIORNI, true)).toContain('17:00')
  })

  it('over several days drops only the unknown hour', () => {
    const testo = quandoEvento({ ...PIU_GIORNI, senza_ora_fine: true }, true)
    expect(testo).toContain('15:00')
    expect(testo).not.toContain('17:00')
  })

  it('on the page of the event, no «ore 00:00»', () => {
    expect(dataEOra('2026-12-04T00:00:00', true)).not.toContain('00:00')
    expect(dataEOra('2026-12-04T15:00:00')).toContain('15:00')
  })
})
