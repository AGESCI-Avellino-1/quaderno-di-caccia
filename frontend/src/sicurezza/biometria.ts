/**
 * Unlock with fingerprint/face through a passkey and the WebAuthn PRF extension
 * (DEC-97). The passkey lives in the phone's authenticator (iCloud Keychain, Google
 * Password Manager…) and returns the same 32-byte secret for the same salt: that
 * secret wraps the vault key. It works offline: no server is involved.
 *
 * This passkey is local and separate from the login passkey managed by allauth.
 * Support (Aug 2026): iOS/iPadOS 18.4+, macOS Safari 18+, Android with Google Password
 * Manager, Windows Hello with Chrome/Edge 147+. Some password managers return no PRF
 * value: the PIN always remains available.
 */
import { casuali } from './cripto'

export class BiometriaNonDisponibile extends Error {
  constructor() {
    super('Impronta o volto non disponibili su questo dispositivo: usa il PIN.')
  }
}

type RisultatiPrf = { prf?: { enabled?: boolean; results?: { first?: BufferSource } } }

/** Best effort: true only means "worth trying". */
export async function biometriaForseDisponibile(): Promise<boolean> {
  if (typeof window === 'undefined' || !('PublicKeyCredential' in window)) return false
  const conCapacita = PublicKeyCredential as unknown as {
    getClientCapabilities?: () => Promise<Record<string, boolean>>
  }
  try {
    const capacita = await conCapacita.getClientCapabilities?.()
    if (capacita && 'extension:prf' in capacita) return capacita['extension:prf'] === true
  } catch {
    // fall through to the platform-authenticator check
  }
  return PublicKeyCredential.isUserVerifyingPlatformAuthenticatorAvailable()
}

function segretoDa(credenziale: PublicKeyCredential): ArrayBuffer | null {
  const risultati = credenziale.getClientExtensionResults() as RisultatiPrf
  const primo = risultati.prf?.results?.first
  if (!primo) return null
  return primo instanceof ArrayBuffer ? primo : (primo.buffer as ArrayBuffer)
}

export async function leggiSegreto(
  idCredenziale: ArrayBuffer,
  sale: Uint8Array<ArrayBuffer>,
): Promise<ArrayBuffer> {
  const credenziale = (await navigator.credentials.get({
    publicKey: {
      challenge: casuali(32),
      allowCredentials: [{ type: 'public-key', id: idCredenziale }],
      userVerification: 'required',
      extensions: { prf: { eval: { first: sale } } },
    },
  })) as PublicKeyCredential | null
  const segreto = credenziale && segretoDa(credenziale)
  if (!segreto) throw new BiometriaNonDisponibile()
  return segreto
}

export async function creaCredenziale(
  email: string,
  sale: Uint8Array<ArrayBuffer>,
): Promise<{ idCredenziale: ArrayBuffer; segreto: ArrayBuffer }> {
  const credenziale = (await navigator.credentials.create({
    publicKey: {
      rp: { name: 'Quaderno di Caccia' },
      user: { id: casuali(16), name: email, displayName: `Sblocco QdC — ${email}` },
      challenge: casuali(32),
      pubKeyCredParams: [
        { type: 'public-key', alg: -7 },
        { type: 'public-key', alg: -257 },
      ],
      authenticatorSelection: {
        authenticatorAttachment: 'platform',
        residentKey: 'preferred',
        userVerification: 'required',
      },
      extensions: { prf: { eval: { first: sale } } },
    },
  })) as PublicKeyCredential | null
  if (!credenziale) throw new BiometriaNonDisponibile()
  const risultati = credenziale.getClientExtensionResults() as RisultatiPrf
  if (risultati.prf?.enabled === false) throw new BiometriaNonDisponibile()
  // Some authenticators return the secret only on get(), not on create().
  const segreto = segretoDa(credenziale) ?? (await leggiSegreto(credenziale.rawId, sale))
  return { idCredenziale: credenziale.rawId, segreto }
}
