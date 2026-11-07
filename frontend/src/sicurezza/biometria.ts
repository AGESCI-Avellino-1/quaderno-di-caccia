/**
 * Unlock with fingerprint/face (DEC-97, DEC-295). The login passkey of this device (allauth,
 * created on the Dispositivi page or when the protection is set up) also gives, through
 * the WebAuthn PRF extension, a 32-byte secret for a salt kept on the device: that secret
 * wraps the vault key. Unlocking works offline, no server is involved, and the secret
 * never leaves the device. One passkey per device, to log in and to unlock.
 *
 * Before DEC-295 a separate local passkey did it (`accesso` missing in the configuration):
 * it keeps working until a login passkey replaces it. It also showed up, and failed, among
 * the login passkeys: that is why it went.
 *
 * Support (Aug 2026): iOS/iPadOS 18.4+, macOS Safari 18+, Android with Google Password
 * Manager, Windows Hello with Chrome/Edge 147+. Chrome installed as an app on macOS gives
 * no PRF value (maintainer, 03/11); some password managers neither: the PIN always remains.
 */
import { WebAuthnError } from '@simplewebauthn/browser'

import { passkey, type Passkey, type PasskeyCreata } from '@/api/allauth'

import { casuali } from './cripto'

export class BiometriaNonDisponibile extends Error {
  constructor() {
    super('Impronta o volto non disponibili su questo dispositivo: usa il PIN.')
  }
}

/** The passkey was created and lets you log in, but here it gives no secret to unlock. */
export class SbloccoNonDisponibile extends Error {
  constructor(
    agente = typeof navigator === 'undefined' ? '' : navigator.userAgent,
    giaPresente = false,
  ) {
    const macChrome = /Macintosh/.test(agente) && /Chrome\//.test(agente)
    super(
      (giaPresente ? 'Hai già una passkey qui' : 'Passkey creata') +
        ': ti serve per entrare. Su questo dispositivo, però, non può sbloccare ' +
        'i dati salvati: usa il PIN.' +
        (macChrome ? ' Sul Mac puoi usare Safari: File → Aggiungi al Dock.' : ''),
    )
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

function segretoDa(risultati: RisultatiPrf): ArrayBuffer | null {
  const primo = risultati.prf?.results?.first
  if (!primo) return null
  return primo instanceof ArrayBuffer ? primo : (primo.buffer as ArrayBuffer)
}

async function chiediPasskey(
  ids: ArrayBuffer[],
  sale: Uint8Array<ArrayBuffer>,
): Promise<PublicKeyCredential | null> {
  // `hints` (WebAuthn level 3) is typed only in the JSON variants of the options.
  const opzioni: PublicKeyCredentialRequestOptions & { hints: string[] } = {
    challenge: casuali(32),
    // The passkey is on this device: no QR code for a phone.
    allowCredentials: ids.map((id) => ({
      type: 'public-key' as const,
      id,
      transports: ['internal' as const],
    })),
    hints: ['client-device'],
    userVerification: 'required',
    extensions: { prf: { eval: { first: sale } } },
  }
  return (await navigator.credentials.get({ publicKey: opzioni })) as PublicKeyCredential | null
}

const segretoDella = (credenziale: PublicKeyCredential | null) =>
  credenziale && segretoDa(credenziale.getClientExtensionResults() as RisultatiPrf)

export async function leggiSegreto(
  idCredenziale: ArrayBuffer,
  sale: Uint8Array<ArrayBuffer>,
): Promise<ArrayBuffer> {
  const segreto = segretoDella(await chiediPasskey([idCredenziale], sale))
  if (!segreto) throw new BiometriaNonDisponibile()
  return segreto
}

/**
 * A passkey of the account this device already has, synced by Apple or Google (DEC-388): it
 * unlocks here too, with a secret of its own for this device's salt. Which one the device
 * picked is in the answer.
 */
async function passkeyGiaPresente(
  ids: ArrayBuffer[],
  sale: Uint8Array<ArrayBuffer>,
): Promise<{ idCredenziale: ArrayBuffer; segreto: ArrayBuffer }> {
  const credenziale = await chiediPasskey(ids, sale)
  const segreto = segretoDella(credenziale)
  if (!credenziale || !segreto) throw new SbloccoNonDisponibile(undefined, true)
  return { idCredenziale: credenziale.rawId, segreto }
}

/** The device refused a new passkey: it already has one of those the server listed. */
export function passkeyGiaSulDispositivo(e: unknown): boolean {
  return e instanceof WebAuthnError && e.code === 'ERROR_AUTHENTICATOR_PREVIOUSLY_REGISTERED'
}

/**
 * Creates the login passkey of this device, named after it (the name shown on the
 * Dispositivi page), and reads its unlock secret. A device that already has a passkey of the
 * account refuses a second one: that one is used instead (`esistente`, DEC-388). Throws
 * `SbloccoNonDisponibile` when the passkey exists but gives no secret, and allauth's
 * `RiautenticazioneRichiesta` when the user must first confirm who they are.
 */
export async function creaPasskeyDiSblocco(
  nome: string,
  sale: Uint8Array<ArrayBuffer>,
  crea: (nome: string, sale: Uint8Array<ArrayBuffer>) => Promise<PasskeyCreata> = passkey.crea,
  elenco: () => Promise<Passkey[]> = passkey.elenco,
): Promise<{ idCredenziale: ArrayBuffer; segreto: ArrayBuffer; esistente?: boolean }> {
  let creata: PasskeyCreata
  try {
    creata = await crea(nome, sale)
  } catch (e) {
    if (!passkeyGiaSulDispositivo(e)) throw e
    const ids = (await elenco()).flatMap((p) =>
      p.id_credenziale ? [daBase64url(p.id_credenziale)] : [],
    )
    if (!ids.length) throw e
    return { ...(await passkeyGiaPresente(ids, sale)), esistente: true }
  }
  const idCredenziale = daBase64url(creata.idCredenziale)
  if (creata.prf?.enabled === false) throw new SbloccoNonDisponibile()
  // Some authenticators return the secret only on get(), not on create().
  let segreto = segretoDa({ prf: creata.prf })
  if (!segreto) {
    try {
      segreto = await leggiSegreto(idCredenziale, sale)
    } catch {
      throw new SbloccoNonDisponibile()
    }
  }
  return { idCredenziale, segreto }
}

export function base64url(dati: ArrayBuffer): string {
  let binario = ''
  for (const byte of new Uint8Array(dati)) binario += String.fromCharCode(byte)
  return btoa(binario).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '')
}

export function daBase64url(testo: string): ArrayBuffer {
  const base64 = testo.replace(/-/g, '+').replace(/_/g, '/')
  const binario = atob(base64 + '='.repeat((4 - (base64.length % 4)) % 4))
  return Uint8Array.from(binario, (c) => c.charCodeAt(0)).buffer
}

/**
 * Asks the password manager to remove a passkey that no longer works here (WebAuthn Signal
 * API): an old local unlock passkey, or a login passkey just removed from the account.
 * Where the browser lacks it nothing happens, and the user may delete it by hand. Never
 * throws.
 */
export async function dimenticaCredenziale(idCredenziale: ArrayBuffer | string): Promise<void> {
  if (typeof PublicKeyCredential === 'undefined') return
  if (typeof PublicKeyCredential.signalUnknownCredential !== 'function') return
  try {
    // Login passkeys and the old unlock ones both belong to this host.
    await PublicKeyCredential.signalUnknownCredential({
      rpId: location.hostname,
      credentialId: typeof idCredenziale === 'string' ? idCredenziale : base64url(idCredenziale),
    })
  } catch {
    // Best effort: the passkey stays in the manager, as before.
  }
}
