/** Registration of this browser as a device that keeps data offline (DEC-97). */
import { api, type Dispositivo } from '@/api/qdc'
import { db as dbPredefinito, type DatabaseQdc } from '@/offline/db'

import { aggiornaScadenza, cancella, protetta } from './cassaforte'

/** A readable default name, editable by the user. */
export function nomeProposto(agente = navigator.userAgent): string {
  if (/iPhone/.test(agente)) return 'iPhone'
  if (/iPad/.test(agente)) return 'iPad'
  if (/Android/.test(agente)) return 'Telefono Android'
  if (/Macintosh/.test(agente)) return 'Mac'
  if (/Windows/.test(agente)) return 'Computer Windows'
  return 'Dispositivo'
}

export async function registraDispositivo(
  nome: string,
  db: DatabaseQdc = dbPredefinito,
): Promise<Dispositivo> {
  const id = (await db.meta.get('dispositivo'))?.valore
  // A 403 "dispositivo_revocato" wipes everything through collegamenti.ts.
  const dispositivo = await api.registraDispositivo({ nome, id: id ?? null })
  await db.meta.bulkPut([
    { chiave: 'dispositivo', valore: dispositivo.id },
    { chiave: 'dispositivo_nome', valore: dispositivo.nome },
  ])
  await aggiornaScadenza(dispositivo.offline_fino_al)
  return dispositivo
}

/**
 * After a new login with the vault still on the phone (the server session had expired):
 * bind the new session to the same device, or revocation and expiry would not apply.
 */
export async function ricollegaDispositivo(db: DatabaseQdc = dbPredefinito): Promise<void> {
  const nome = (await db.meta.get('dispositivo_nome'))?.valore ?? nomeProposto()
  await registraDispositivo(nome, db)
}

/**
 * At start-up, before asking the PIN: has this device been disconnected? Revocation
 * deletes the session, so the answer must come without logging in (DEC-97). Offline,
 * or if the server does not answer in time, nothing happens: the offline expiry
 * window covers that case.
 */
export async function controllaRevoca(
  db: DatabaseQdc = dbPredefinito,
  attesaMassima = 4000,
): Promise<void> {
  if (!protetta()) return
  const id = (await db.meta.get('dispositivo'))?.valore
  if (!id) return
  try {
    const { revocato } = await Promise.race([
      api.statoDispositivo(id),
      new Promise<never>((_, rifiuta) =>
        setTimeout(() => rifiuta(new Error('timeout')), attesaMassima),
      ),
    ])
    if (revocato) await cancella('revocato')
  } catch {
    // offline or slow network: try again at the next start
  }
}
