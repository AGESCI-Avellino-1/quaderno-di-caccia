/**
 * The vault (DEC-97): encryption of local data, unlock with PIN or biometrics, wrong-PIN
 * limit, remote revocation and offline expiry.
 *
 * States:
 *   da_configurare → the user has not chosen yet (after the first login)
 *   solo_online    → nothing is kept on this device
 *   bloccata       → data exists, the key is not in memory
 *   sbloccata      → the key is in memory (never written anywhere)
 *
 * The data key lives only in this module's memory while unlocked. It is stored wrapped
 * twice at most: by a key derived from the PIN, and by a key derived from the passkey
 * PRF secret. Logout, revocation, expiry and too many wrong PINs delete everything.
 */
import { ref } from 'vue'

import {
  avvolgi,
  casuali,
  chiaveDaPin,
  chiaveDaSegreto,
  cifra,
  decifra,
  ITERAZIONI_PIN,
  nuovaChiaveDati,
  svolgi,
  type Cifrato,
} from './cripto'
import { creaPasskeyDiSblocco, dimenticaCredenziale, leggiSegreto } from './biometria'
import {
  cancellaTutto,
  db as dbPredefinito,
  svuotaDatiLocali,
  type ConfigurazioneProtezione,
  type DatabaseQdc,
} from '@/offline/db'

export type StatoCassaforte = 'da_configurare' | 'solo_online' | 'bloccata' | 'sbloccata'
export type MotivoCancellazione = 'revocato' | 'scaduto' | 'tentativi' | 'altro_account' | 'uscita'

export const TENTATIVI_MASSIMI = 5
// Exactly 6 digits since DEC-298 (before: at least 6). A longer PIN set before still
// unlocks, and the unlock page then asks for a new one.
export const LUNGHEZZA_PIN = 6

/** True for a PIN that can be chosen now. */
export function pinValido(pin: string): boolean {
  return new RegExp(`^\\d{${LUNGHEZZA_PIN}}$`).test(pin)
}

export class PinErrato extends Error {
  constructor(public readonly rimasti: number) {
    super(
      `PIN errato: ancora ${rimasti} tentativi, poi i dati su questo dispositivo verranno cancellati.`,
    )
  }
}

export class DatiCancellati extends Error {
  constructor(public readonly motivo: MotivoCancellazione) {
    super(MESSAGGI_CANCELLAZIONE[motivo])
  }
}

export const MESSAGGI_CANCELLAZIONE: Record<MotivoCancellazione, string> = {
  revocato: 'Questo dispositivo è stato scollegato: i dati salvati qui sono stati cancellati.',
  scaduto:
    'Il dispositivo non si collega da troppi giorni: per sicurezza i dati salvati qui sono stati cancellati.',
  tentativi: 'Troppi PIN errati: i dati salvati su questo dispositivo sono stati cancellati.',
  altro_account:
    "Hai effettuato l'accesso con un altro account: i dati del precedente sono stati cancellati.",
  uscita: 'Sei uscito: i dati salvati su questo dispositivo sono stati cancellati.',
}

export const EVENTO_CANCELLAZIONE = 'qdc:dati-cancellati'

let chiaveDati: CryptoKey | null = null
let configurazione: ConfigurazioneProtezione | undefined
let database: DatabaseQdc = dbPredefinito

/** Reactive state for the UI and the router. */
export const stato = ref<StatoCassaforte>('da_configurare')
export const biometriaAttiva = ref(false)
/** Why the data was last wiped: the router shows it on the login page, then clears it. */
export const ultimoMotivo = ref<MotivoCancellazione | null>(null)

function aggiornaStato() {
  biometriaAttiva.value = !!configurazione?.biometria
  if (!configurazione) stato.value = 'da_configurare'
  else if (configurazione.modalita === 'solo_online') stato.value = 'solo_online'
  else stato.value = chiaveDati ? 'sbloccata' : 'bloccata'
}

/** Tests only: use another database. */
export function usaDatabase(altro: DatabaseQdc) {
  database = altro
  chiaveDati = null
  configurazione = undefined
}

export async function inizializza(): Promise<void> {
  configurazione = await database.protezione.get('config')
  aggiornaStato()
  await verificaScadenza()
}

export function proprietario(): string | undefined {
  return configurazione?.proprietario
}

export function protetta(): boolean {
  return configurazione?.modalita === 'protetto'
}

export function sbloccata(): boolean {
  return chiaveDati !== null
}

async function salva() {
  if (configurazione) await database.protezione.put(configurazione)
  aggiornaStato()
}

/** Deletes every local trace and tells the app (App.vue shows the reason). */
export async function cancella(motivo: MotivoCancellazione): Promise<void> {
  const passkey = vecchiaPasskey()
  chiaveDati = null
  configurazione = undefined
  if (motivo === 'uscita') await svuotaDatiLocali(database)
  else await cancellaTutto(database)
  aggiornaStato()
  ultimoMotivo.value = motivo
  // An old unlock passkey would stay in the manager; a login passkey still lets you in.
  if (passkey) void dimenticaCredenziale(passkey)
  if (typeof window !== 'undefined') {
    window.dispatchEvent(new CustomEvent(EVENTO_CANCELLAZIONE, { detail: motivo }))
  }
}

export async function verificaScadenza(adesso = new Date()): Promise<void> {
  const limite = configurazione?.offlineFinoAl
  if (configurazione?.modalita === 'protetto' && limite && new Date(limite) < adesso) {
    await cancella('scaduto')
  }
}

/** Called for every server answer carrying X-QdC-Offline-Fino-Al. */
export async function aggiornaScadenza(valore: string): Promise<void> {
  if (!configurazione || configurazione.modalita !== 'protetto') return
  if (configurazione.offlineFinoAl === valore) return
  configurazione.offlineFinoAl = valore
  await salva()
}

export async function sceltaSoloOnline(email: string): Promise<void> {
  await svuotaDatiLocali(database)
  chiaveDati = null
  configurazione = {
    id: 'config',
    modalita: 'solo_online',
    proprietario: email,
    tentativiFalliti: 0,
  }
  await salva()
}

export async function configura(
  email: string,
  pin: string,
  iterazioni = ITERAZIONI_PIN,
): Promise<void> {
  if (!pinValido(pin)) throw new Error(`Il PIN deve avere ${LUNGHEZZA_PIN} cifre.`)
  await svuotaDatiLocali(database)
  const nuova = await nuovaChiaveDati()
  const sale = casuali(16)
  const avvolta = await avvolgi(nuova, await chiaveDaPin(pin, sale, iterazioni))
  configurazione = {
    id: 'config',
    modalita: 'protetto',
    proprietario: email,
    pin: { ...avvolta, sale, iterazioni },
    tentativiFalliti: 0,
  }
  chiaveDati = nuova
  await salva()
}

export async function sbloccaConPin(pin: string): Promise<void> {
  if (!configurazione?.pin) throw new Error('Protezione non configurata.')
  try {
    const { sale, iterazioni } = configurazione.pin
    chiaveDati = await svolgi(configurazione.pin, await chiaveDaPin(pin, sale, iterazioni))
  } catch {
    configurazione.tentativiFalliti += 1
    const rimasti = TENTATIVI_MASSIMI - configurazione.tentativiFalliti
    if (rimasti <= 0) {
      await cancella('tentativi')
      throw new DatiCancellati('tentativi')
    }
    await salva()
    throw new PinErrato(rimasti)
  }
  configurazione.tentativiFalliti = 0
  await salva()
}

/**
 * A new PIN for the unlocked vault (DEC-298: after unlocking with a PIN longer than 6
 * digits): the data key is wrapped again, the data on the device stay.
 */
export async function cambiaPin(pin: string, iterazioni = ITERAZIONI_PIN): Promise<void> {
  if (!pinValido(pin)) throw new Error(`Il PIN deve avere ${LUNGHEZZA_PIN} cifre.`)
  if (!chiaveDati || !configurazione?.pin) throw new CassaforteBloccata()
  const sale = casuali(16)
  const avvolta = await avvolgi(chiaveDati, await chiaveDaPin(pin, sale, iterazioni))
  configurazione.pin = { ...avvolta, sale, iterazioni }
  configurazione.tentativiFalliti = 0
  await salva()
}

/** The old local unlock passkey, if the fingerprint still uses one (before DEC-295). */
function vecchiaPasskey(): ArrayBuffer | undefined {
  const bio = configurazione?.biometria
  return bio && !bio.accesso ? bio.idCredenziale : undefined
}

/** The credential that unlocks this device, to match it against the login passkeys. */
export function credenzialeDiSblocco(): ArrayBuffer | undefined {
  return configurazione?.biometria?.idCredenziale
}

/** True while the fingerprint still uses an old local unlock passkey. */
export function conVecchiaPasskey(): boolean {
  return vecchiaPasskey() !== undefined
}

/**
 * Creates the login passkey of this device, named after it, and lets it unlock the data
 * too (DEC-295); a device that already has one, synced, uses that (DEC-388): the answer says
 * so. The secret source is injectable for tests; in the app it is the PRF of the passkey.
 */
export async function attivaBiometria(
  crea: typeof creaPasskeyDiSblocco = creaPasskeyDiSblocco,
  nomePasskey?: string,
): Promise<boolean> {
  if (!configurazione || !chiaveDati) throw new Error('Sblocca prima con il PIN.')
  const sale = casuali(32)
  const nome =
    nomePasskey ?? (await database.meta.get('dispositivo_nome'))?.valore ?? 'Questo dispositivo'
  const { idCredenziale, segreto, esistente } = await crea(nome, sale)
  const kek = await chiaveDaSegreto(segreto, sale)
  const vecchia = vecchiaPasskey()
  configurazione.biometria = {
    ...(await avvolgi(chiaveDati, kek)),
    sale,
    idCredenziale,
    accesso: true,
  }
  await salva()
  if (vecchia) void dimenticaCredenziale(vecchia)
  return !!esistente
}

/** The login passkey stays (it still lets you in); an old unlock passkey goes. */
export async function disattivaBiometria(): Promise<void> {
  if (!configurazione) return
  const vecchia = vecchiaPasskey()
  delete configurazione.biometria
  await salva()
  if (vecchia) void dimenticaCredenziale(vecchia)
}

export async function sbloccaConBiometria(
  leggi: typeof leggiSegreto = leggiSegreto,
): Promise<void> {
  const bio = configurazione?.biometria
  if (!configurazione || !bio) throw new Error('Impronta o volto non attivati.')
  const segreto = await leggi(bio.idCredenziale, bio.sale)
  chiaveDati = await svolgi(bio, await chiaveDaSegreto(segreto, bio.sale))
  configurazione.tentativiFalliti = 0
  await salva()
}

export function blocca(): void {
  chiaveDati = null
  aggiornaStato()
}

export class CassaforteBloccata extends Error {
  constructor() {
    super('Sblocca l’app per leggere i dati salvati su questo dispositivo.')
  }
}

export async function cifraValore(valore: unknown, contesto: string): Promise<Cifrato> {
  if (!chiaveDati) throw new CassaforteBloccata()
  return cifra(chiaveDati, valore, contesto)
}

export async function decifraValore<T>(cifrato: Cifrato, contesto: string): Promise<T> {
  if (!chiaveDati) throw new CassaforteBloccata()
  return decifra<T>(chiaveDati, cifrato, contesto)
}
