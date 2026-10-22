/**
 * Network-first reads with a local fallback: online you always see fresh data, offline
 * you see the last copy saved on this device (encrypted, DEC-97), with its date.
 * When the user chose "solo online", nothing is saved and offline reads fail.
 */
import { ErroreApi } from '@/api/http'
import { cifraValore, decifraValore, protetta, sbloccata } from '@/sicurezza/cassaforte'

import { db as dbPredefinito, type DatabaseQdc } from './db'

export interface Letto<T> {
  dati: T
  /** Null when the data comes from the server right now. */
  copiaDel: string | null
}

const salvabile = () => protetta() && sbloccata()

export async function salvaInCache(
  chiave: string,
  dati: unknown,
  database: DatabaseQdc = dbPredefinito,
): Promise<void> {
  if (!salvabile()) return
  await database.cache.put({
    chiave,
    valore: await cifraValore(dati, chiave),
    aggiornata_il: new Date().toISOString(),
  })
}

export async function leggiDallaCache<T>(
  chiave: string,
  database: DatabaseQdc = dbPredefinito,
): Promise<Letto<T> | null> {
  if (!salvabile()) return null
  const voce = await database.cache.get(chiave)
  if (!voce) return null
  return { dati: await decifraValore<T>(voce.valore, chiave), copiaDel: voce.aggiornata_il }
}

export async function leggiConCache<T>(
  chiave: string,
  carica: () => Promise<T>,
  database: DatabaseQdc = dbPredefinito,
): Promise<Letto<T>> {
  try {
    const dati = await carica()
    await salvaInCache(chiave, dati, database)
    return { dati, copiaDel: null }
  } catch (errore) {
    // HTTP answers (403, 404...) are real answers: never mask them with old data.
    if (errore instanceof ErroreApi) {
      if (errore.stato === 403 || errore.stato === 404) await database.cache.delete(chiave)
      throw errore
    }
    const copia = await leggiDallaCache<T>(chiave, database)
    if (!copia) throw errore
    return copia
  }
}
