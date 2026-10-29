import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { ErroreApi } from '@/api/http'
import { leggiConCache } from '@/offline/cache'
import type { DatabaseQdc } from '@/offline/db'
import { accoda, inviaCoda, scrivi } from '@/offline/outbox'
import * as cassaforte from '@/sicurezza/cassaforte'
import { collegaCassaforte } from '@/sicurezza/collegamenti'

import { cassaforteSbloccata, nuovoDatabase, risposta } from './aiuti'

let database: DatabaseQdc
let fetchFinto: ReturnType<typeof vi.fn<typeof fetch>>

beforeEach(async () => {
  database = await nuovoDatabase()
  await cassaforteSbloccata()
  fetchFinto = vi.fn<typeof fetch>()
  vi.stubGlobal('fetch', fetchFinto)
})

afterEach(async () => {
  vi.unstubAllGlobals()
  await database.delete()
})

const nuova = (descrizione: string) => ({
  metodo: 'POST' as const,
  percorso: '/api/v1/presenze',
  corpo: { x: 1 },
  descrizione,
})

const intestazioni = (n: number) => fetchFinto.mock.calls[n]![1]!.headers as Record<string, string>

describe('coda offline', () => {
  it("invia in ordine con l'Idempotency-Key e svuota la coda", async () => {
    const a = await accoda(nuova('a'), database)
    const b = await accoda(nuova('b'), database)
    fetchFinto.mockImplementation(async () => risposta(201))

    const esito = await inviaCoda(database)

    expect(esito).toEqual({ inviate: 2, errori: 0, interrotto: false })
    expect([intestazioni(0)['Idempotency-Key'], intestazioni(1)['Idempotency-Key']]).toEqual([
      a.chiave,
      b.chiave,
    ])
    expect(JSON.parse(fetchFinto.mock.calls[0]![1]!.body as string)).toEqual({ x: 1 })
    expect(await database.coda.count()).toBe(0)
  })

  it('il corpo in coda è cifrato', async () => {
    await accoda({ ...nuova('a'), corpo: { allergia: 'arachidi' } }, database)
    const [voce] = await database.coda.toArray()
    expect(new TextDecoder().decode(voce!.corpo!.dati)).not.toContain('arachidi')
  })

  it('si ferma senza rete e conserva ordine e operazioni', async () => {
    await accoda(nuova('a'), database)
    await accoda(nuova('b'), database)
    fetchFinto.mockRejectedValue(new TypeError('Failed to fetch'))

    const esito = await inviaCoda(database)

    expect(esito.interrotto).toBe(true)
    expect(fetchFinto).toHaveBeenCalledTimes(1)
    const rimaste = await database.coda.toArray()
    expect(rimaste.map((o) => [o.descrizione, o.stato, o.tentativi])).toEqual([
      ['a', 'in_attesa', 1],
      ['b', 'in_attesa', 0],
    ])
  })

  it("un 4xx diventa 'errore' da rivedere e non blocca le successive", async () => {
    await accoda(nuova('rifiutata'), database)
    await accoda(nuova('buona'), database)
    fetchFinto
      .mockResolvedValueOnce(risposta(409, { detail: 'conflitto' }))
      .mockResolvedValueOnce(risposta(201))

    const esito = await inviaCoda(database)

    expect(esito).toEqual({ inviate: 1, errori: 1, interrotto: false })
    const [rimasta] = await database.coda.toArray()
    expect(rimasta!.stato).toBe('errore')
    expect(rimasta!.errore).toEqual({ stato: 409, dati: { detail: 'conflitto' } })
  })

  it('sessione scaduta (401): si ferma e riprova dopo', async () => {
    await accoda(nuova('a'), database)
    fetchFinto.mockImplementation(async () => risposta(401))
    expect((await inviaCoda(database)).interrotto).toBe(true)
    expect((await database.coda.toArray())[0]!.stato).toBe('in_attesa')
  })

  it('con la cassaforte bloccata non invia nulla', async () => {
    await accoda(nuova('a'), database)
    cassaforte.blocca()
    expect((await inviaCoda(database)).interrotto).toBe(true)
    expect(fetchFinto).not.toHaveBeenCalled()
  })

  it('scrivi: online invia subito, offline lascia in coda', async () => {
    fetchFinto.mockImplementationOnce(async () => risposta(200))
    expect(await scrivi(nuova('a'), database)).toEqual({ inCoda: false })
    fetchFinto.mockRejectedValueOnce(new TypeError('offline'))
    expect(await scrivi(nuova('b'), database)).toEqual({ inCoda: true })
    expect(await database.coda.count()).toBe(1)
  })

  it('scrivi in modalità solo online: richiesta diretta, niente coda', async () => {
    await cassaforte.sceltaSoloOnline('genitore@example.invalid')
    fetchFinto.mockImplementation(async () => risposta(200))
    expect(await scrivi(nuova('a'), database)).toEqual({ inCoda: false })
    expect(intestazioni(0)['Idempotency-Key']).toBeUndefined()
    expect(await database.coda.count()).toBe(0)
  })
})

describe('cache di lettura', () => {
  it('online aggiorna la copia, offline la restituisce con la data', async () => {
    const online = await leggiConCache('k', async () => ({ v: 1 }), database)
    expect(online).toEqual({ dati: { v: 1 }, copiaDel: null })

    const offline = await leggiConCache(
      'k',
      () => Promise.reject(new TypeError('offline')),
      database,
    )
    expect(offline.dati).toEqual({ v: 1 })
    expect(offline.copiaDel).not.toBeNull()
  })

  it('un gateway che non raggiunge il server vale come offline, un 404 no', async () => {
    await leggiConCache('k', async () => ({ v: 1 }), database)
    const giu = await leggiConCache('k', () => Promise.reject(new ErroreApi(502, {})), database)
    expect(giu.dati).toEqual({ v: 1 })
    await expect(
      leggiConCache('k', () => Promise.reject(new ErroreApi(404, {})), database),
    ).rejects.toBeInstanceOf(ErroreApi)
  })
})

// DEC-97
describe('collegamento con il server', () => {
  it('la revoca del dispositivo cancella tutto', async () => {
    const scollega = collegaCassaforte()
    try {
      await accoda(nuova('a'), database)
      await database.meta.put({ chiave: 'dispositivo', valore: 'x' })
      fetchFinto.mockImplementation(async () =>
        risposta(401, { codice: 'dispositivo_revocato', detail: 'scollegato' }),
      )
      await inviaCoda(database)
      expect(cassaforte.stato.value).toBe('da_configurare')
      expect(await database.coda.count()).toBe(0)
      expect(await database.meta.count()).toBe(0)
    } finally {
      scollega()
    }
  })

  it("l'intestazione del server rinnova la scadenza offline", async () => {
    const scollega = collegaCassaforte()
    try {
      fetchFinto.mockImplementation(async () =>
        risposta(200, {}, { 'X-QdC-Offline-Fino-Al': '2026-11-05T10:00:00+00:00' }),
      )
      await leggiConCache('k', () => fetch('/x').then((r) => r.json()), database)
      const { richiesta } = await import('@/api/http')
      await richiesta('/api/v1/io')
      expect((await database.protezione.get('config'))!.offlineFinoAl).toBe(
        '2026-11-05T10:00:00+00:00',
      )
    } finally {
      scollega()
    }
  })
})

describe('controllo della revoca all’avvio', () => {
  it('un dispositivo revocato si cancella prima del PIN', async () => {
    const { controllaRevoca } = await import('@/sicurezza/dispositivo')
    await database.meta.put({ chiave: 'dispositivo', valore: 'abc' })
    cassaforte.blocca()
    fetchFinto.mockImplementation(async () => risposta(200, { revocato: true }))
    await controllaRevoca(database)
    expect(fetchFinto.mock.calls[0]![0]).toBe('/api/v1/dispositivi/abc/stato')
    expect(cassaforte.stato.value).toBe('da_configurare')
    expect(await database.protezione.count()).toBe(0)
  })

  it('offline non tocca nulla', async () => {
    const { controllaRevoca } = await import('@/sicurezza/dispositivo')
    await database.meta.put({ chiave: 'dispositivo', valore: 'abc' })
    fetchFinto.mockRejectedValue(new TypeError('offline'))
    await controllaRevoca(database)
    expect(cassaforte.stato.value).toBe('sbloccata')
  })
})
