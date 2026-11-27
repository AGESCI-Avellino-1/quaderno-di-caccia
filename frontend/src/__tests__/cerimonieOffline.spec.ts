import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { ErroreApi } from '@/api/http'
import { api, type TestoVoceLibro } from '@/api/qdc'
import { leggiDallaCache } from '@/offline/cache'
import { aggiornaTesti, CHIAVE_TESTI, leggiVoce } from '@/offline/cerimonie'
import type { DatabaseQdc } from '@/offline/db'

import { cassaforteSbloccata, nuovoDatabase } from './aiuti'

const TESTI: TestoVoceLibro[] = [
  {
    id: 3,
    titolo: "Notte dell'Alta Squadriglia",
    tipo: 'CERIMONIA',
    ambito: 'ALTA_SQ',
    unita: 'Reparto (N1)',
    cerimonia_del_totem: false,
    testo: '<p>La veglia</p>',
  },
]

let database: DatabaseQdc

beforeEach(async () => {
  database = await nuovoDatabase()
})

afterEach(async () => {
  vi.restoreAllMocks()
  await database.delete()
})

describe('libro delle cerimonie senza rete', () => {
  it('tiene i testi cifrati e li mostra senza rete, senza registro né allegati', async () => {
    await cassaforteSbloccata()
    vi.spyOn(api, 'testiCerimonie').mockResolvedValue(TESTI)
    await aggiornaTesti(database)
    expect(JSON.stringify(await database.cache.get(CHIAVE_TESTI))).not.toContain('veglia')
    vi.spyOn(api, 'voceLibro').mockRejectedValue(new TypeError('Failed to fetch'))
    const letta = await leggiVoce(3, database)
    expect(letta.copiaDel).not.toBeNull()
    expect(letta.dati).toMatchObject({
      testo: '<p>La veglia</p>',
      puo_modificare: false,
      vede_registro: false,
      allegati: [],
    })
    await expect(leggiVoce(4, database)).rejects.toBeInstanceOf(TypeError)
  })

  it('una risposta vera non si copre con la copia; un rifiuto la cancella', async () => {
    await cassaforteSbloccata()
    vi.spyOn(api, 'testiCerimonie').mockResolvedValue(TESTI)
    await aggiornaTesti(database)
    vi.spyOn(api, 'voceLibro').mockRejectedValue(new ErroreApi(404, {}))
    await expect(leggiVoce(3, database)).rejects.toBeInstanceOf(ErroreApi)
    // The book switched off, or no longer a member.
    vi.spyOn(api, 'testiCerimonie').mockRejectedValue(new ErroreApi(404, {}))
    await aggiornaTesti(database)
    expect(await database.cache.get(CHIAVE_TESTI)).toBeUndefined()
  })

  it('senza protezione del dispositivo non salva niente', async () => {
    const chiamata = vi.spyOn(api, 'testiCerimonie').mockResolvedValue(TESTI)
    await aggiornaTesti(database)
    expect(chiamata).not.toHaveBeenCalled()
    expect(await leggiDallaCache(CHIAVE_TESTI, database)).toBeNull()
  })
})
