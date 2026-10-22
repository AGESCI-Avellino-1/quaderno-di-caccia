/** Shared test helpers: a fresh database and an unlocked vault (fast PBKDF2). */
import { DatabaseQdc } from '@/offline/db'
import * as cassaforte from '@/sicurezza/cassaforte'

export const PIN = '123456'
export const ITERAZIONI_TEST = 1_000

export async function nuovoDatabase(): Promise<DatabaseQdc> {
  const database = new DatabaseQdc(`test-${crypto.randomUUID()}`)
  cassaforte.usaDatabase(database)
  await cassaforte.inizializza()
  return database
}

export async function cassaforteSbloccata(email = 'capo@example.invalid') {
  await cassaforte.configura(email, PIN, ITERAZIONI_TEST)
}

export function risposta(stato: number, corpo: unknown = {}, intestazioni = {}) {
  return new Response(JSON.stringify(corpo), {
    status: stato,
    headers: { 'Content-Type': 'application/json', ...intestazioni },
  })
}
