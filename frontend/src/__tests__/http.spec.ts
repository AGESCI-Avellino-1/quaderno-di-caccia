import { afterEach, describe, expect, it, vi } from 'vitest'

import { ErroreApi, leggiCookie, richiesta } from '@/api/http'
import { temaDellaBranca } from '@/api/qdc'

afterEach(() => {
  vi.unstubAllGlobals()
  document.cookie = 'csrftoken=; expires=Thu, 01 Jan 1970 00:00:00 GMT'
})

describe('client http', () => {
  it('legge i cookie', () => {
    expect(leggiCookie('csrftoken', 'a=1; csrftoken=abc%3D')).toBe('abc=')
    expect(leggiCookie('manca', 'a=1')).toBeNull()
  })

  it('aggiunge il token CSRF solo alle scritture', async () => {
    document.cookie = 'csrftoken=tok'
    const fetchFinto = vi.fn<typeof fetch>(async () => new Response('{}', { status: 200 }))
    vi.stubGlobal('fetch', fetchFinto)

    await richiesta('/api/v1/io')
    await richiesta('/api/v1/inviti', { metodo: 'POST', corpo: { a: 1 } })

    const intestazioni = (n: number) =>
      fetchFinto.mock.calls[n]![1]!.headers as Record<string, string>
    expect(intestazioni(0)['X-CSRFToken']).toBeUndefined()
    expect(intestazioni(1)['X-CSRFToken']).toBe('tok')
    expect(intestazioni(1)['Content-Type']).toBe('application/json')
  })

  it('trasforma le risposte non 2xx in ErroreApi', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(
        async () =>
          new Response('{"detail":"no"}', {
            status: 403,
            headers: { 'Content-Type': 'application/json' },
          }),
      ),
    )
    await expect(richiesta('/x')).rejects.toMatchObject({ stato: 403, dati: { detail: 'no' } })
    await expect(richiesta('/x')).rejects.toBeInstanceOf(ErroreApi)
  })
})

it('una pagina HTML di errore resta un ErroreApi, non un falso "offline"', async () => {
  vi.stubGlobal(
    'fetch',
    vi.fn(
      async () =>
        new Response('<h1>Forbidden</h1>', {
          status: 403,
          headers: { 'Content-Type': 'text/html' },
        }),
    ),
  )
  await expect(richiesta('/x')).rejects.toMatchObject({ stato: 403, dati: '<h1>Forbidden</h1>' })
})

describe('tema della branca', () => {
  it.each([
    ['LC', 'lc'],
    ['EG', 'eg'],
    ['RS', 'rs'],
    ['COCA', 'capi'],
    ['???', 'generico'],
  ])('%s → %s', (branca, tema) => {
    expect(temaDellaBranca(branca)).toBe(tema)
  })
})
