/**
 * Cryptographic primitives for the on-device vault (DEC-97). Web Crypto only, no
 * libraries: AES-GCM 256 for data, PBKDF2-SHA256 for the PIN, HKDF for the passkey PRF.
 *
 * Threat model (see CLAUDE.md, "Protezione sul telefono"): a lost, stolen or borrowed
 * phone, and anyone opening the app or reading its storage without the PIN. A short
 * PIN does NOT resist an offline brute force on a dump of the browser storage taken
 * from an unlocked/rooted phone: against that the defences are the phone's own lock,
 * remote revocation and the offline expiry window.
 */

/** OWASP Password Storage Cheat Sheet: 600,000 iterations for PBKDF2-HMAC-SHA256. */
export const ITERAZIONI_PIN = 600_000

const testo = new TextEncoder()

export function casuali(n: number): Uint8Array<ArrayBuffer> {
  return crypto.getRandomValues(new Uint8Array(n))
}

/** The key that encrypts every local record. Extractable only to be wrapped. */
export function nuovaChiaveDati(): Promise<CryptoKey> {
  return crypto.subtle.generateKey({ name: 'AES-GCM', length: 256 }, true, ['encrypt', 'decrypt'])
}

/** Key-encryption key from the PIN. */
export async function chiaveDaPin(
  pin: string,
  sale: Uint8Array<ArrayBuffer>,
  iterazioni = ITERAZIONI_PIN,
): Promise<CryptoKey> {
  const base = await crypto.subtle.importKey('raw', testo.encode(pin), 'PBKDF2', false, [
    'deriveKey',
  ])
  return crypto.subtle.deriveKey(
    { name: 'PBKDF2', salt: sale, iterations: iterazioni, hash: 'SHA-256' },
    base,
    { name: 'AES-GCM', length: 256 },
    false,
    ['wrapKey', 'unwrapKey'],
  )
}

/** Key-encryption key from a high-entropy secret (the passkey PRF output). */
export async function chiaveDaSegreto(
  segreto: BufferSource,
  sale: Uint8Array<ArrayBuffer>,
): Promise<CryptoKey> {
  const base = await crypto.subtle.importKey('raw', segreto, 'HKDF', false, ['deriveKey'])
  return crypto.subtle.deriveKey(
    { name: 'HKDF', hash: 'SHA-256', salt: sale, info: testo.encode('qdc-cassaforte-v1') },
    base,
    { name: 'AES-GCM', length: 256 },
    false,
    ['wrapKey', 'unwrapKey'],
  )
}

export interface ChiaveAvvolta {
  iv: Uint8Array<ArrayBuffer>
  avvolta: ArrayBuffer
}

export async function avvolgi(chiaveDati: CryptoKey, kek: CryptoKey): Promise<ChiaveAvvolta> {
  const iv = casuali(12)
  const avvolta = await crypto.subtle.wrapKey('raw', chiaveDati, kek, { name: 'AES-GCM', iv })
  return { iv, avvolta }
}

/** Throws (OperationError) when the KEK is wrong: that is how a wrong PIN is detected. */
export function svolgi(avvolta: ChiaveAvvolta, kek: CryptoKey): Promise<CryptoKey> {
  return crypto.subtle.unwrapKey(
    'raw',
    avvolta.avvolta,
    kek,
    { name: 'AES-GCM', iv: avvolta.iv },
    { name: 'AES-GCM', length: 256 },
    true,
    ['encrypt', 'decrypt'],
  )
}

export interface Cifrato {
  iv: Uint8Array<ArrayBuffer>
  dati: ArrayBuffer
}

/**
 * Encrypts a JSON value. `contesto` (e.g. the cache key) is authenticated data: a
 * ciphertext copied under another key fails to decrypt.
 */
export async function cifra(
  chiave: CryptoKey,
  valore: unknown,
  contesto: string,
): Promise<Cifrato> {
  const iv = casuali(12)
  const dati = await crypto.subtle.encrypt(
    { name: 'AES-GCM', iv, additionalData: testo.encode(contesto) },
    chiave,
    testo.encode(JSON.stringify(valore)),
  )
  return { iv, dati }
}

export async function decifra<T>(
  chiave: CryptoKey,
  cifrato: Cifrato,
  contesto: string,
): Promise<T> {
  const chiaro = await crypto.subtle.decrypt(
    { name: 'AES-GCM', iv: cifrato.iv, additionalData: testo.encode(contesto) },
    chiave,
    cifrato.dati,
  )
  return JSON.parse(new TextDecoder().decode(chiaro)) as T
}
