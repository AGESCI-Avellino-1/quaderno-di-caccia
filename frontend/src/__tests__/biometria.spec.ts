import { WebAuthnError } from '@simplewebauthn/browser'
import { afterEach, describe, expect, it, vi } from 'vitest'

import type { PasskeyCreata } from '@/api/allauth'
import { creaPasskeyDiSblocco, leggiSegreto, SbloccoNonDisponibile } from '@/sicurezza/biometria'

const segreto = new Uint8Array(32).fill(7).buffer
const credenziale = {
  rawId: new Uint8Array([1, 2, 3]).buffer,
  getClientExtensionResults: () => ({ prf: { enabled: true, results: { first: segreto } } }),
}

function finte() {
  const leggi = vi.fn<(o: CredentialRequestOptions) => Promise<typeof credenziale>>(
    async () => credenziale,
  )
  vi.stubGlobal('navigator', { credentials: { get: leggi } })
  return { leggi }
}

const creata = (prf: PasskeyCreata['prf']) =>
  vi.fn<(nome: string, sale: Uint8Array<ArrayBuffer>) => Promise<PasskeyCreata>>(async () => ({
    idCredenziale: 'AQID',
    prf,
  }))

afterEach(() => vi.unstubAllGlobals())

const giaPresente = () =>
  new WebAuthnError({
    message: 'già presente',
    code: 'ERROR_AUTHENTICATOR_PREVIOUSLY_REGISTERED',
    cause: new Error('InvalidStateError'),
  })

// DEC-388.
describe('passkey already on the device, synced', () => {
  const sale = new Uint8Array(32) as Uint8Array<ArrayBuffer>
  const lista = async () => [
    { id: 9, name: 'Mac', created_at: 1, last_used_at: null, id_credenziale: 'AQID' },
    { id: 10, name: 'Vecchia', created_at: 1, last_used_at: null },
  ]

  it('uses it to unlock instead of failing, asking for the ones of the account', async () => {
    const { leggi } = finte()
    const risultato = await creaPasskeyDiSblocco(
      'iPhone',
      sale,
      async () => {
        throw giaPresente()
      },
      lista,
    )
    expect(risultato.esistente).toBe(true)
    expect(new Uint8Array(risultato.idCredenziale)).toEqual(new Uint8Array([1, 2, 3]))
    expect(risultato.segreto).toBe(segreto)
    const ammesse = leggi.mock.calls[0]![0].publicKey!.allowCredentials!
    expect(ammesse).toHaveLength(1)
  })

  it('without a secret the passkey still lets you in, and it says so', async () => {
    const leggi = vi.fn(async () => ({
      ...credenziale,
      getClientExtensionResults: () => ({}),
    }))
    vi.stubGlobal('navigator', { credentials: { get: leggi } })
    await expect(
      creaPasskeyDiSblocco(
        'iPhone',
        sale,
        async () => {
          throw giaPresente()
        },
        lista,
      ),
    ).rejects.toThrow(/Hai già una passkey/)
  })

  it('any other refusal stays an error', async () => {
    finte()
    await expect(
      creaPasskeyDiSblocco(
        'iPhone',
        sale,
        async () => {
          throw new Error('rete')
        },
        lista,
      ),
    ).rejects.toThrow('rete')
  })
})

describe('biometria', () => {
  it('unlocks with the login passkey of this device, named after the device', async () => {
    const crea = creata({ enabled: true, results: { first: segreto } })
    const sale = new Uint8Array(32)
    const esito = await creaPasskeyDiSblocco('Mac di Andrea', sale, crea)
    expect(crea).toHaveBeenCalledWith('Mac di Andrea', sale)
    expect(new Uint8Array(esito.idCredenziale)).toEqual(new Uint8Array([1, 2, 3]))
    expect(esito.segreto).toBe(segreto)
  })

  it('reads the secret with get() when create() does not give it', async () => {
    const { leggi } = finte()
    const esito = await creaPasskeyDiSblocco('Mac', new Uint8Array(32), creata({ enabled: true }))
    expect(esito.segreto).toBe(segreto)
    expect(leggi).toHaveBeenCalledOnce()
  })

  it('without PRF the passkey stays to log in, and the PIN unlocks', async () => {
    const errore = await creaPasskeyDiSblocco(
      'Mac',
      new Uint8Array(32),
      creata({ enabled: false }),
    ).catch((e: unknown) => e)
    expect(errore).toBeInstanceOf(SbloccoNonDisponibile)
    expect(String((errore as Error).message)).toContain('ti serve per entrare')
  })

  it('suggests Safari to Chrome on a Mac', () => {
    const mac = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) Chrome/142.0 Safari/537.36'
    expect(new SbloccoNonDisponibile(mac).message).toContain('Aggiungi al Dock')
    expect(new SbloccoNonDisponibile('iPhone').message).not.toContain('Dock')
  })

  it('asks for the passkey on this device, not a phone', async () => {
    const { leggi } = finte()
    expect(await leggiSegreto(credenziale.rawId, new Uint8Array(32))).toBe(segreto)
    const opzioni = leggi.mock.calls[0]![0].publicKey as PublicKeyCredentialRequestOptions & {
      hints: string[]
    }
    expect(opzioni.hints).toEqual(['client-device'])
    expect(opzioni.allowCredentials![0]!.transports).toEqual(['internal'])
  })
})
