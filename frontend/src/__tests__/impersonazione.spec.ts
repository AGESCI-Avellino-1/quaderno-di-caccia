import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { leggiConCache, salvaInCache } from '@/offline/cache'
import type { DatabaseQdc } from '@/offline/db'
import { accoda, inviaCoda, scrivi } from '@/offline/outbox'
import { impostaImpersonazione } from '@/sicurezza/impersonazione'

import { cassaforteSbloccata, nuovoDatabase, risposta } from './aiuti'

// While a capo acts as another user, the device copy and the queue stay the capo's own.
let database: DatabaseQdc
let fetchFinto: ReturnType<typeof vi.fn<typeof fetch>>

beforeEach(async () => {
  database = await nuovoDatabase()
  await cassaforteSbloccata()
  fetchFinto = vi.fn<typeof fetch>()
  vi.stubGlobal('fetch', fetchFinto)
})

afterEach(async () => {
  impostaImpersonazione(false)
  vi.unstubAllGlobals()
  await database.delete()
})

const scrittura = {
  metodo: 'PUT' as const,
  percorso: '/api/v1/eventi/1/presenze',
  corpo: { segni: [] },
  descrizione: 'Presenze',
}

describe('impersonazione', () => {
  it('saves nothing on the device and never shows the capo copy', async () => {
    await salvaInCache('profilo', { email: 'capo@example.invalid' }, database)
    impostaImpersonazione(true)
    fetchFinto.mockImplementation(async () => risposta(200, { email: 'genitore@example.invalid' }))
    await leggiConCache('eventi', () => Promise.resolve([1, 2]), database)
    expect(await database.cache.get('eventi')).toBeUndefined()
    // Offline: the capo's own copy is not offered as if it were the other person's.
    await expect(
      leggiConCache('profilo', () => Promise.reject(new TypeError('offline')), database),
    ).rejects.toThrow()
  })

  it('sends writes directly and keeps the capo queue for later', async () => {
    await accoda({ ...scrittura, descrizione: 'del capo' }, database)
    impostaImpersonazione(true)
    fetchFinto.mockImplementation(async () => risposta(200))
    const esito = await scrivi(scrittura, database)
    expect(esito.inCoda).toBe(false)
    expect(fetchFinto).toHaveBeenCalledTimes(1)
    expect((await inviaCoda(database)).interrotto).toBe(true)
    expect(await database.coda.count()).toBe(1)
  })
})
