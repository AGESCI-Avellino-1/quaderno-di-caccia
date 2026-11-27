/**
 * The book of ceremonies offline (DEC-437): the device keeps, encrypted (DEC-97), the list and
 * the texts of the entries one reads, refreshed every time the book is opened with the network.
 * The register and the attachments stay online only.
 */
import { ErroreApi } from '@/api/http'
import { api, type TestoVoceLibro, type VoceLibro } from '@/api/qdc'

import {
  leggiConCache,
  leggiDallaCache,
  salvabile,
  SERVER_IRRAGGIUNGIBILE,
  type Letto,
} from './cache'
import { db as dbPredefinito, type DatabaseQdc } from './db'

export const CHIAVE_TESTI = 'cerimonie:testi'

/** Saves the texts again; a 404 (the book switched off, no longer a member) wipes them. */
export async function aggiornaTesti(database: DatabaseQdc = dbPredefinito): Promise<void> {
  // Never while acting as another user: a refusal would wipe one's own copy.
  if (!salvabile()) return
  try {
    await leggiConCache(CHIAVE_TESTI, () => api.testiCerimonie(), database)
  } catch {
    /* offline or refused: the copy stays as it was, or is gone */
  }
}

function daTesto(t: TestoVoceLibro): VoceLibro {
  return {
    ...t,
    unita_id: null,
    allegati: [],
    puo_modificare: false,
    aggiunti: [],
    condizioni: [],
    vede_registro: false,
    partecipanti: [],
  }
}

/** One entry: from the server, or offline its text from the copy on the device. */
export async function leggiVoce(
  id: number,
  database: DatabaseQdc = dbPredefinito,
): Promise<Letto<VoceLibro>> {
  try {
    return { dati: await api.voceLibro(id), copiaDel: null }
  } catch (errore) {
    // A real answer (403, 404...) is never masked by the copy.
    if (errore instanceof ErroreApi && !SERVER_IRRAGGIUNGIBILE.has(errore.stato)) throw errore
    const copia = await leggiDallaCache<TestoVoceLibro[]>(CHIAVE_TESTI, database)
    const testo = copia?.dati.find((t) => t.id === id)
    if (!copia || !testo) throw errore
    return { dati: daTesto(testo), copiaDel: copia.copiaDel }
  }
}
