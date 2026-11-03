import { createPinia, setActivePinia } from 'pinia'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { richiesta } from '@/api/http'
import { SITO_DI_BASE } from '@/sito/segnaposto'
import { useSitoStore } from '@/stores/sito'

import { cassaforteSbloccata, nuovoDatabase, risposta } from './aiuti'

const MESSAGGIO = 'Torniamo alle 18.'

beforeEach(() => setActivePinia(createPinia()))
afterEach(() => vi.unstubAllGlobals())

describe('manutenzione', () => {
  it('una risposta "manutenzione" la accende subito', async () => {
    const sito = useSitoStore()
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => risposta(503, { detail: MESSAGGIO, codice: 'manutenzione' })),
    )
    await expect(richiesta('/api/v1/io')).rejects.toMatchObject({ stato: 503 })
    expect(sito.sito.manutenzione).toBe(true)
    expect(sito.sito.messaggio_manutenzione).toBe(MESSAGGIO)
  })

  it('un 503 qualunque (server che riparte) non è una manutenzione', async () => {
    const sito = useSitoStore()
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => risposta(503, { detail: 'Service Unavailable' })),
    )
    await expect(richiesta('/api/v1/io')).rejects.toMatchObject({ stato: 503 })
    expect(sito.sito.manutenzione).toBeFalsy()
  })

  it('finisce quando il server lo dice', async () => {
    const sito = useSitoStore()
    sito.aggiorna({ ...SITO_DI_BASE, manutenzione: true, messaggio_manutenzione: MESSAGGIO })
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => risposta(200, { ...SITO_DI_BASE, manutenzione: false })),
    )
    await sito.carica()
    expect(sito.sito.manutenzione).toBe(false)
  })

  it('la copia sul dispositivo non blocca chi è senza rete', async () => {
    await nuovoDatabase()
    await cassaforteSbloccata()
    const sito = useSitoStore()
    vi.stubGlobal(
      'fetch',
      vi.fn(async () =>
        risposta(200, { ...SITO_DI_BASE, manutenzione: true, messaggio_manutenzione: MESSAGGIO }),
      ),
    )
    await sito.carica()
    expect(sito.sito.manutenzione).toBe(true)
    // Offline: the copy saved during the maintenance is read, the maintenance is not.
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => {
        throw new TypeError('Failed to fetch')
      }),
    )
    await sito.carica()
    expect(sito.sito.nome_sito).toBe(SITO_DI_BASE.nome_sito)
    expect(sito.sito.manutenzione).toBe(false)
  })
})
