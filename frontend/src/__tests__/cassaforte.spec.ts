import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { leggiDallaCache, salvaInCache } from '@/offline/cache'
import type { DatabaseQdc } from '@/offline/db'
import * as cassaforte from '@/sicurezza/cassaforte'

import { ITERAZIONI_TEST, PIN, cassaforteSbloccata, nuovoDatabase } from './aiuti'

let database: DatabaseQdc
let cancellazioni: string[]
const registra = (e: Event) => cancellazioni.push((e as CustomEvent<string>).detail)

beforeEach(async () => {
  database = await nuovoDatabase()
  cancellazioni = []
  window.addEventListener(cassaforte.EVENTO_CANCELLAZIONE, registra)
})

afterEach(async () => {
  window.removeEventListener(cassaforte.EVENTO_CANCELLAZIONE, registra)
  await database.delete()
})

describe('cassaforte', () => {
  it('parte da configurare', () => {
    expect(cassaforte.stato.value).toBe('da_configurare')
  })

  it('rifiuta PIN corti o non numerici', async () => {
    await expect(cassaforte.configura('a@b', '1234', ITERAZIONI_TEST)).rejects.toThrow('6 cifre')
    await expect(cassaforte.configura('a@b', 'abcdef', ITERAZIONI_TEST)).rejects.toThrow()
  })

  it('i dati sul dispositivo sono cifrati', async () => {
    await cassaforteSbloccata()
    await salvaInCache('persona:1', { nome: 'Giulia', allergie: ['arachidi'] }, database)
    const grezzo = await database.cache.get('persona:1')
    const byte = new TextDecoder().decode(grezzo!.valore.dati)
    expect(byte).not.toContain('Giulia')
    expect(byte).not.toContain('arachidi')
    expect((await leggiDallaCache('persona:1', database))!.dati).toEqual({
      nome: 'Giulia',
      allergie: ['arachidi'],
    })
  })

  it("un dato spostato sotto un'altra chiave non si decifra", async () => {
    await cassaforteSbloccata()
    await salvaInCache('persona:1', { nome: 'Giulia' }, database)
    const voce = await database.cache.get('persona:1')
    await database.cache.put({ ...voce!, chiave: 'persona:2' })
    await expect(leggiDallaCache('persona:2', database)).rejects.toThrow()
  })

  it('bloccata: niente letture; sblocco con il PIN', async () => {
    await cassaforteSbloccata()
    await salvaInCache('k', { v: 1 }, database)
    cassaforte.blocca()
    expect(cassaforte.stato.value).toBe('bloccata')
    expect(await leggiDallaCache('k', database)).toBeNull()

    // A fresh start (app reopened) finds the vault locked.
    await cassaforte.inizializza()
    expect(cassaforte.stato.value).toBe('bloccata')
    await cassaforte.sbloccaConPin(PIN)
    expect(cassaforte.stato.value).toBe('sbloccata')
    expect((await leggiDallaCache('k', database))!.dati).toEqual({ v: 1 })
  })

  it('PIN errati: conto alla rovescia, poi cancellazione di tutto', async () => {
    await cassaforteSbloccata()
    await salvaInCache('k', { v: 1 }, database)
    await database.meta.put({ chiave: 'dispositivo', valore: 'x' })
    cassaforte.blocca()
    for (let rimasti = cassaforte.TENTATIVI_MASSIMI - 1; rimasti > 0; rimasti--) {
      await expect(cassaforte.sbloccaConPin('000000')).rejects.toMatchObject({ rimasti })
    }
    await expect(cassaforte.sbloccaConPin('000000')).rejects.toBeInstanceOf(
      cassaforte.DatiCancellati,
    )
    expect(cancellazioni).toEqual(['tentativi'])
    expect(cassaforte.stato.value).toBe('da_configurare')
    expect(await database.cache.count()).toBe(0)
    expect(await database.meta.count()).toBe(0)
  })

  it('un PIN giusto azzera i tentativi', async () => {
    await cassaforteSbloccata()
    cassaforte.blocca()
    await expect(cassaforte.sbloccaConPin('000000')).rejects.toBeInstanceOf(cassaforte.PinErrato)
    await cassaforte.sbloccaConPin(PIN)
    cassaforte.blocca()
    await expect(cassaforte.sbloccaConPin('000000')).rejects.toMatchObject({
      rimasti: cassaforte.TENTATIVI_MASSIMI - 1,
    })
  })

  it('sblocco con impronta: il segreto PRF avvolge la chiave', async () => {
    await cassaforteSbloccata()
    await salvaInCache('k', { v: 2 }, database)
    const segreto = crypto.getRandomValues(new Uint8Array(32)).buffer
    const crea = vi.fn(async () => ({ idCredenziale: new ArrayBuffer(8), segreto }))
    await cassaforte.attivaBiometria('capo@example.invalid', crea)
    expect(cassaforte.biometriaAttiva.value).toBe(true)

    cassaforte.blocca()
    await expect(
      cassaforte.sbloccaConBiometria(async () => crypto.getRandomValues(new Uint8Array(32)).buffer),
    ).rejects.toThrow()
    await cassaforte.sbloccaConBiometria(async () => segreto)
    expect((await leggiDallaCache('k', database))!.dati).toEqual({ v: 2 })
  })

  it('oltre la scadenza offline i dati si cancellano da soli', async () => {
    await cassaforteSbloccata()
    await salvaInCache('k', { v: 1 }, database)
    await cassaforte.aggiornaScadenza('2026-10-01T00:00:00Z')
    await cassaforte.verificaScadenza(new Date('2026-10-02T00:00:00Z'))
    expect(cancellazioni).toEqual(['scaduto'])
    expect(await database.cache.count()).toBe(0)
  })

  it('entro la scadenza restano', async () => {
    await cassaforteSbloccata()
    await cassaforte.aggiornaScadenza('2026-10-30T00:00:00Z')
    await cassaforte.verificaScadenza(new Date('2026-10-02T00:00:00Z'))
    expect(cassaforte.stato.value).toBe('sbloccata')
  })

  it("all'uscita resta solo l'id del dispositivo", async () => {
    await cassaforteSbloccata()
    await salvaInCache('k', { v: 1 }, database)
    await database.meta.put({ chiave: 'dispositivo', valore: 'abc' })
    await cassaforte.cancella('uscita')
    expect(await database.cache.count()).toBe(0)
    expect(await database.protezione.count()).toBe(0)
    expect((await database.meta.get('dispositivo'))?.valore).toBe('abc')
  })

  it('solo online: niente viene salvato', async () => {
    await cassaforte.sceltaSoloOnline('genitore@example.invalid')
    expect(cassaforte.stato.value).toBe('solo_online')
    await salvaInCache('k', { v: 1 }, database)
    expect(await database.cache.count()).toBe(0)
  })
})
