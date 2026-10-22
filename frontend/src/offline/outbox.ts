/**
 * Offline write queue (DEC-96).
 *
 * Writes go through `scrivi`: with the protection active they are stored first
 * (body encrypted, DEC-97) and sent when the network is available; in "solo online"
 * mode they are sent directly. The server deduplicates replays by Idempotency-Key
 * (apps.core.idempotenza), so sending the same operation twice is harmless.
 *
 * Outcome of a send:
 * - 2xx                → removed from the queue;
 * - 4xx (not 408/429)  → kept as "errore" for the user to review (conflict, validation,
 *                        permission): never retried automatically, never dropped silently;
 * - network, 5xx, 401, 408, 429, vault locked → the flush stops, order is preserved.
 */
import { ErroreApi, richiesta } from '@/api/http'
import {
  CassaforteBloccata,
  cifraValore,
  decifraValore,
  protetta,
  sbloccata,
} from '@/sicurezza/cassaforte'

import { db as dbPredefinito, type DatabaseQdc, type OperazioneInCoda } from './db'

export interface NuovaOperazione {
  metodo: OperazioneInCoda['metodo']
  percorso: string
  corpo?: unknown
  /** Shown in "Modifiche in sospeso". No personal data: it is stored in clear. */
  descrizione: string
}

export async function accoda(
  operazione: NuovaOperazione,
  database: DatabaseQdc = dbPredefinito,
): Promise<OperazioneInCoda> {
  if (!protetta() || !sbloccata()) throw new CassaforteBloccata()
  const chiave = crypto.randomUUID()
  const voce: OperazioneInCoda = {
    metodo: operazione.metodo,
    percorso: operazione.percorso,
    descrizione: operazione.descrizione,
    corpo: operazione.corpo === undefined ? undefined : await cifraValore(operazione.corpo, chiave),
    chiave,
    creata_il: new Date().toISOString(),
    stato: 'in_attesa',
    tentativi: 0,
  }
  voce.id = await database.coda.add(voce)
  return voce
}

export interface EsitoScrittura {
  /** True when the change waits in the queue (offline or server unreachable). */
  inCoda: boolean
}

/** The one entry point for writes from the views. */
export async function scrivi(
  operazione: NuovaOperazione,
  database: DatabaseQdc = dbPredefinito,
): Promise<EsitoScrittura> {
  if (!protetta()) {
    await richiesta(operazione.percorso, { metodo: operazione.metodo, corpo: operazione.corpo })
    return { inCoda: false }
  }
  const voce = await accoda(operazione, database)
  await inviaCoda(database)
  const ancora = await database.coda.get(voce.id!)
  if (ancora?.stato === 'errore' && ancora.errore) {
    throw new ErroreApi(ancora.errore.stato, ancora.errore.dati)
  }
  return { inCoda: !!ancora }
}

export interface EsitoInvio {
  inviate: number
  errori: number
  /** True when the flush stopped early (offline, server down, session expired, locked). */
  interrotto: boolean
}

const RIPROVABILI = new Set([401, 408, 429])

let invioInCorso: Promise<EsitoInvio> | null = null

/** Send pending operations in creation order. Concurrent calls share one run. */
export function inviaCoda(database: DatabaseQdc = dbPredefinito): Promise<EsitoInvio> {
  invioInCorso ??= svuota(database).finally(() => {
    invioInCorso = null
  })
  return invioInCorso
}

async function svuota(database: DatabaseQdc): Promise<EsitoInvio> {
  const esito: EsitoInvio = { inviate: 0, errori: 0, interrotto: false }
  if (!sbloccata()) return { ...esito, interrotto: true }
  const inAttesa = await database.coda.where('stato').equals('in_attesa').sortBy('id')
  for (const operazione of inAttesa) {
    try {
      const corpo = operazione.corpo
        ? await decifraValore<unknown>(operazione.corpo, operazione.chiave)
        : undefined
      await richiesta(operazione.percorso, {
        metodo: operazione.metodo,
        corpo,
        intestazioni: { 'Idempotency-Key': operazione.chiave },
      })
      await database.coda.delete(operazione.id!)
      esito.inviate++
    } catch (errore) {
      if (
        errore instanceof ErroreApi &&
        errore.stato >= 400 &&
        errore.stato < 500 &&
        !RIPROVABILI.has(errore.stato)
      ) {
        await database.coda.update(operazione.id!, {
          stato: 'errore',
          tentativi: operazione.tentativi + 1,
          errore: { stato: errore.stato, dati: errore.dati },
        })
        esito.errori++
        continue
      }
      if (!(errore instanceof CassaforteBloccata)) {
        await database.coda.update(operazione.id!, { tentativi: operazione.tentativi + 1 })
      }
      esito.interrotto = true
      break
    }
  }
  return esito
}

/** Re-queue an operation the user reviewed (after fixing the cause). */
export async function riprova(id: number, database: DatabaseQdc = dbPredefinito) {
  await database.coda.update(id, { stato: 'in_attesa', errore: undefined })
}

/** Drop an operation the user decided to abandon. */
export async function scarta(id: number, database: DatabaseQdc = dbPredefinito) {
  await database.coda.delete(id)
}
