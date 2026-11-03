import { afterEach, describe, expect, it, vi } from 'vitest'

import { creaCredenziale, leggiSegreto } from '@/sicurezza/biometria'

const segreto = new Uint8Array(32).fill(7).buffer
const credenziale = {
  rawId: new Uint8Array([1, 2, 3]).buffer,
  getClientExtensionResults: () => ({ prf: { enabled: true, results: { first: segreto } } }),
}

function finte() {
  const crea = vi.fn<(o: CredentialCreationOptions) => Promise<typeof credenziale>>(
    async () => credenziale,
  )
  const leggi = vi.fn<(o: CredentialRequestOptions) => Promise<typeof credenziale>>(
    async () => credenziale,
  )
  vi.stubGlobal('navigator', { credentials: { create: crea, get: leggi } })
  return { crea, leggi }
}

afterEach(() => vi.unstubAllGlobals())

describe('biometria', () => {
  it('names the unlock passkey with the device and the day', async () => {
    const { crea } = finte()
    await creaCredenziale(
      'capo@example.invalid',
      new Uint8Array(32),
      'Mac di Andrea',
      new Date(2026, 10, 3),
    )
    const utente = crea.mock.calls[0]![0].publicKey!.user
    expect(utente.name).toBe('capo@example.invalid (sblocco Mac di Andrea, 03/11/2026)')
    expect(utente.displayName).toBe('Sblocco QdC — Mac di Andrea, 03/11/2026')
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
