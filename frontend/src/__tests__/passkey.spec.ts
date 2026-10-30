import { afterEach, describe, expect, it, vi } from 'vitest'

import { passkey, RiautenticazioneRichiesta } from '@/api/allauth'

afterEach(() => vi.unstubAllGlobals())

function risponde(stato: number, corpo: unknown) {
  vi.stubGlobal(
    'fetch',
    vi.fn(
      async () =>
        new Response(JSON.stringify(corpo), {
          status: stato,
          headers: { 'Content-Type': 'application/json' },
        }),
    ),
  )
}

describe('passkey per entrare', () => {
  it('elenca solo le passkey, non i codici di recupero', async () => {
    risponde(200, {
      status: 200,
      data: [
        { type: 'webauthn', id: 3, name: 'Telefono', created_at: 1, last_used_at: null },
        { type: 'recovery_codes', created_at: 1, last_used_at: null },
      ],
    })
    expect((await passkey.elenco()).map((p) => p.name)).toEqual(['Telefono'])
  })

  it('chiede di confermare chi sei, con i modi che il server accetta', async () => {
    risponde(401, {
      status: 401,
      data: {
        flows: [{ id: 'reauthenticate' }, { id: 'mfa_reauthenticate', types: ['webauthn'] }],
      },
      meta: { is_authenticated: true },
    })
    const errore = await passkey.rimuovi(3).catch((e: unknown) => e)
    expect(errore).toBeInstanceOf(RiautenticazioneRichiesta)
    expect(errore).toMatchObject({ conPassword: true, conPasskey: true })
  })

  it('senza passkey si conferma solo con la password', async () => {
    risponde(401, { status: 401, data: { flows: [{ id: 'reauthenticate' }] }, meta: {} })
    const errore = await passkey.crea('Telefono').catch((e: unknown) => e)
    expect(errore).toMatchObject({ conPassword: true, conPasskey: false })
  })
})
