import { describe, expect, it } from 'vitest'

import { ErroreApi } from '@/api/http'
import { testoErrore } from '@/composables/useErrore'

describe('messaggi di errore', () => {
  it('il messaggio del server vince', () => {
    expect(testoErrore(new ErroreApi(400, { detail: 'Data non valida.' }))).toBe('Data non valida.')
  })

  it('senza messaggio, una frase semplice e nessun codice tecnico', () => {
    const html = '<h1>Server Error (500)</h1>'
    for (const stato of [400, 413, 500, 502, 503, 504, 418]) {
      const testo = testoErrore(new ErroreApi(stato, html))
      expect(testo).not.toMatch(/\d{3}/)
      expect(testo).not.toContain('<')
    }
    expect(testoErrore(new ErroreApi(502, html))).toContain('non risponde')
    expect(testoErrore(new ErroreApi(413, null))).toContain('20 MB')
  })
})
