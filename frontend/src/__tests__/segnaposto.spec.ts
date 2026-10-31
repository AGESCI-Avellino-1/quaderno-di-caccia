import { describe, expect, it } from 'vitest'

import type { Sito } from '@/api/qdc'
import { riempi, SITO_DI_BASE } from '@/sito/segnaposto'

const SITO: Sito = {
  ...SITO_DI_BASE,
  gruppo: 'AGESCI Avellino 1',
  sigla_gruppo: 'AV1',
  anno: '2025/26',
}

describe('segnaposto del titolo', () => {
  it('riempie i titoli di base', () => {
    expect(riempi(SITO.titolo_completo, SITO)).toBe('Quaderno di Caccia - AGESCI Avellino 1')
    expect(riempi(SITO.titolo_breve, SITO)).toBe('QdC - AV1')
  })

  it('usa la pagina corrente e non lascia separatori vuoti', () => {
    const titolo = '[Pagina corrente] · [Sigla sito] - [Sigla gruppo]'
    expect(riempi(titolo, SITO, 'Eventi')).toBe('Eventi · QdC - AV1')
    expect(riempi(titolo, SITO, '')).toBe('QdC - AV1')
    expect(riempi('[Nome sito] - [Gruppo]', { ...SITO, gruppo: '' })).toBe('Quaderno di Caccia')
  })

  it('senza sigla usa il nome, e ignora maiuscole e minuscole', () => {
    expect(riempi('[sigla GRUPPO]', { ...SITO, sigla_gruppo: '' })).toBe('AGESCI Avellino 1')
    expect(riempi('Anno [Anno]', SITO)).toBe('Anno 2025/26')
  })

  it('lascia come sono i segnaposto sconosciuti e i trattini nelle parole', () => {
    expect(riempi('[Altro] Avellino-1', SITO)).toBe('[Altro] Avellino-1')
  })
})
