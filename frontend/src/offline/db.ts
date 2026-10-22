/**
 * Local database (IndexedDB via Dexie) for offline use (DEC-93..DEC-97).
 *
 * - `coda`: writes made offline, replayed in order with their Idempotency-Key.
 * - `cache`: last server answer per read, shown when the network is missing.
 * - `protezione`: the vault configuration (wrapped keys, attempts, offline expiry).
 * - `meta`: non-personal facts about this device (its id on the server).
 *
 * Every payload in `coda` and `cache` is encrypted with the vault key
 * (src/sicurezza/cassaforte.ts): without the PIN or the fingerprint they are unreadable.
 */
import Dexie, { type EntityTable } from 'dexie'

import type { ChiaveAvvolta, Cifrato } from '@/sicurezza/cripto'

export type StatoOperazione = 'in_attesa' | 'errore'

export interface OperazioneInCoda {
  id?: number
  /** UUID sent as Idempotency-Key: created once, when the user acted. */
  chiave: string
  metodo: 'POST' | 'PUT' | 'PATCH' | 'DELETE'
  percorso: string
  /** The request body, encrypted (context: the Idempotency-Key). */
  corpo?: Cifrato
  /** Short text shown to the user in the list of pending changes. Never personal data. */
  descrizione: string
  creata_il: string
  stato: StatoOperazione
  tentativi: number
  errore?: { stato: number; dati: unknown }
}

export interface VoceCache {
  chiave: string
  /** Encrypted value (context: `chiave`). */
  valore: Cifrato
  aggiornata_il: string
}

export interface ConfigurazioneProtezione {
  id: 'config'
  /** "solo_online": the user chose to keep nothing on this device. */
  modalita: 'protetto' | 'solo_online'
  /** Email of the account the data belongs to: another login wipes it. */
  proprietario: string
  pin?: ChiaveAvvolta & { sale: Uint8Array<ArrayBuffer>; iterazioni: number }
  biometria?: ChiaveAvvolta & { sale: Uint8Array<ArrayBuffer>; idCredenziale: ArrayBuffer }
  tentativiFalliti: number
  /** ISO date sent by the server (X-QdC-Offline-Fino-Al); past it, data is wiped. */
  offlineFinoAl?: string
}

export interface VoceMeta {
  chiave: string
  valore: string
}

export class DatabaseQdc extends Dexie {
  coda!: EntityTable<OperazioneInCoda, 'id'>
  cache!: EntityTable<VoceCache, 'chiave'>
  protezione!: EntityTable<ConfigurazioneProtezione, 'id'>
  meta!: EntityTable<VoceMeta, 'chiave'>

  constructor(nome = 'qdc') {
    super(nome)
    this.version(1).stores({ coda: '++id, &chiave, stato', cache: 'chiave' })
    // v2: encrypted payloads. Version 1 only ever held unencrypted development data.
    this.version(2)
      .stores({ coda: '++id, &chiave, stato', cache: 'chiave', protezione: 'id', meta: 'chiave' })
      .upgrade(async (tx) => {
        await tx.table('coda').clear()
        await tx.table('cache').clear()
      })
  }
}

export const db = new DatabaseQdc()

/** Logout: forget the data and the vault, keep the device id (same phone, same device). */
export async function svuotaDatiLocali(database: DatabaseQdc = db): Promise<void> {
  await Promise.all([database.coda.clear(), database.cache.clear(), database.protezione.clear()])
}

/** Revocation or expiry: nothing of this account must remain. */
export async function cancellaTutto(database: DatabaseQdc = db): Promise<void> {
  await Promise.all([svuotaDatiLocali(database), database.meta.clear()])
}
