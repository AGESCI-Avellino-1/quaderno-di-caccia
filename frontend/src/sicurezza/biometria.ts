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
  // `hints` (WebAuthn level 3) is typed only in the JSON variants of the options.
  const opzioni: PublicKeyCredentialRequestOptions & { hints: string[] } = {
    challenge: casuali(32),
    // The passkey is on this device (created as `platform`): no QR code for a phone.
    // Chrome as an installed app on macOS offered only the phone [da verificare].
    allowCredentials: [{ type: 'public-key', id: idCredenziale, transports: ['internal'] }],
    hints: ['client-device'],
    userVerification: 'required',
    extensions: { prf: { eval: { first: sale } } },
  }
  const credenziale = (await navigator.credentials.get({
    publicKey: opzioni,
  })) as PublicKeyCredential | null
  const segreto = credenziale && segretoDa(credenziale)
  if (!segreto) throw new BiometriaNonDisponibile()
  return segreto
}

/**
 * `dispositivo` and the day go in the name, so that in the password manager (where a new
 * one appears after every wipe) the one in use can be told apart. What each manager
 * shows, `name` or `displayName`, varies [da verificare]: both carry them.
 */
export async function creaCredenziale(
  email: string,
  sale: Uint8Array<ArrayBuffer>,
  dispositivo = 'questo dispositivo',
  oggi = new Date(),
): Promise<{ idCredenziale: ArrayBuffer; segreto: ArrayBuffer }> {
  const quando = oggi.toLocaleDateString('it-IT', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
  })
  const credenziale = (await navigator.credentials.create({
    publicKey: {
      rp: { name: 'Quaderno di Caccia' },
      user: {
        id: casuali(16),
        name: `${email} (sblocco ${dispositivo}, ${quando})`,
        displayName: `Sblocco QdC — ${dispositivo}, ${quando}`,
      },
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

function base64url(dati: ArrayBuffer): string {
  let binario = ''
  for (const byte of new Uint8Array(dati)) binario += String.fromCharCode(byte)
  return btoa(binario).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '')
}

/**
 * Asks the password manager to remove an unlock passkey the app no longer uses (WebAuthn
 * Signal API): after a wipe or when the fingerprint is switched off. Where the browser
 * lacks it nothing happens, and the user may delete it by hand. Never throws.
 */
export async function dimenticaCredenziale(idCredenziale: ArrayBuffer): Promise<void> {
  if (typeof PublicKeyCredential === 'undefined') return
  if (typeof PublicKeyCredential.signalUnknownCredential !== 'function') return
  try {
    // No `rp.id` at creation: the passkey belongs to this host.
    await PublicKeyCredential.signalUnknownCredential({
      rpId: location.hostname,
      credentialId: base64url(idCredenziale),
    })
  } catch {
    // Best effort: the passkey stays in the manager, as before.
  }
}
