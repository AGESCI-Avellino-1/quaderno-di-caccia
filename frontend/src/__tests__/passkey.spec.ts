import { afterEach, describe, expect, it, vi } from 'vitest'

import { passkey, RiautenticazioneRichiesta } from '@/api/allauth'

afterEach(() => vi.unstubAllGlobals())

const json = (stato: number, corpo: unknown) =>
  new Response(JSON.stringify(corpo), {
    status: stato,
    headers: { 'Content-Type': 'application/json' },
  })

function risponde(stato: number, corpo: unknown) {
  vi.stubGlobal(
    'fetch',
    vi.fn(async () => json(stato, corpo)),
  )
}

describe('passkey per entrare', () => {
  it('elenca solo le passkey, con il loro id di credenziale', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async (url: string) =>
        url === '/api/v1/io/passkey'
          ? json(200, [{ id: 3, id_credenziale: 'AQID' }])
          : json(200, {
              status: 200,
              data: [
                { type: 'webauthn', id: 3, name: 'Telefono', created_at: 1, last_used_at: null },
                { type: 'recovery_codes', created_at: 1, last_used_at: null },
              ],
            }),
      ),
    )
    expect(await passkey.elenco()).toMatchObject([{ name: 'Telefono', id_credenziale: 'AQID' }])
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

  it('il segreto per sbloccare resta sul dispositivo, mai al server', async () => {
    const segreto = new Uint8Array(32).fill(9).buffer
    const crea = vi.fn<(o: CredentialCreationOptions) => Promise<object>>(async () => ({
      id: 'AQID',
      rawId: new Uint8Array([1, 2, 3]).buffer,
      type: 'public-key',
      authenticatorAttachment: 'platform',
      response: {
        attestationObject: new Uint8Array([4]).buffer,
        clientDataJSON: new Uint8Array([5]).buffer,
      },
      getClientExtensionResults: () => ({
        credProps: { rk: true },
        prf: { enabled: true, results: { first: segreto } },
      }),
    }))
    vi.stubGlobal('PublicKeyCredential', function () {})
    vi.stubGlobal('navigator', { credentials: { create: crea } })
    const corpi: unknown[] = []
    vi.stubGlobal(
      'fetch',
      vi.fn(async (_url: string, init?: RequestInit) => {
        if (init?.method === 'POST') {
          corpi.push(JSON.parse(init.body as string))
          return json(200, { status: 200, data: {} })
        }
        return json(200, {
          status: 200,
          data: {
            creation_options: {
              publicKey: {
                challenge: 'AQID',
                rp: { id: 'localhost', name: 'QdC' },
                user: { id: 'AQID', name: 'mario', displayName: 'Mario' },
                pubKeyCredParams: [{ type: 'public-key', alg: -7 }],
                extensions: { credProps: true },
              },
            },
          },
        })
      }),
    )
    const sale = new Uint8Array(32).fill(1)
    const creata = await passkey.crea('Mac di Mario', sale)

    // Asked of the browser, with allauth's own extensions kept.
    const estensioni = crea.mock.calls[0]![0].publicKey!.extensions as Record<string, unknown>
    expect(estensioni).toEqual({ credProps: true, prf: { eval: { first: sale } } })
    // Back to the vault, not to the server.
    expect(creata).toMatchObject({ idCredenziale: 'AQID', prf: { enabled: true } })
    expect(creata.prf?.results?.first).toBe(segreto)
    const inviata = (corpi[0] as { credential: { clientExtensionResults: object } }).credential
    expect(inviata.clientExtensionResults).toEqual({ credProps: { rk: true } })
    expect(JSON.stringify(corpi)).not.toContain('prf')
  })
})
