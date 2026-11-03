import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { leggiDallaCache, salvaInCache } from '@/offline/cache'
import type { DatabaseQdc } from '@/offline/db'
import type { creaPasskeyDiSblocco } from '@/sicurezza/biometria'
import * as cassaforte from '@/sicurezza/cassaforte'
import { avvolgi, casuali, chiaveDaPin, svolgi } from '@/sicurezza/cripto'

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

  it('rifiuta PIN che non sono di 6 cifre', async () => {
    await expect(cassaforte.configura('a@b', '1234', ITERAZIONI_TEST)).rejects.toThrow('6 cifre')
    await expect(cassaforte.configura('a@b', '1234567', ITERAZIONI_TEST)).rejects.toThrow('6 cifre')
    await expect(cassaforte.configura('a@b', 'abcdef', ITERAZIONI_TEST)).rejects.toThrow()
  })

  it('un PIN più lungo scelto prima sblocca ancora; il PIN nuovo tiene i dati', async () => {
    await cassaforteSbloccata()
    await salvaInCache('k', { v: 3 }, database)
    // A vault protected before DEC-298 with 8 digits: wrap the same data key again.
    await cassaforte.cambiaPin(PIN, ITERAZIONI_TEST)
    const config = (await database.protezione.get('config'))!
    const chiave = await svolgi(
      config.pin!,
      await chiaveDaPin(PIN, config.pin!.sale, ITERAZIONI_TEST),
    )
    const sale = casuali(16)
    const avvolta = await avvolgi(chiave, await chiaveDaPin('12345678', sale, ITERAZIONI_TEST))
    await database.protezione.put({
      ...config,
      pin: { ...avvolta, sale, iterazioni: ITERAZIONI_TEST },
    })
    cassaforte.blocca()
    await cassaforte.inizializza()

    await cassaforte.sbloccaConPin('12345678')
    await expect(cassaforte.cambiaPin('1234567', ITERAZIONI_TEST)).rejects.toThrow('6 cifre')
    await cassaforte.cambiaPin('654321', ITERAZIONI_TEST)
    cassaforte.blocca()
    await expect(cassaforte.sbloccaConPin('12345678')).rejects.toBeInstanceOf(cassaforte.PinErrato)
    await cassaforte.sbloccaConPin('654321')
    expect((await leggiDallaCache('k', database))!.dati).toEqual({ v: 3 })
  })

  it('il PIN si cambia solo a cassaforte sbloccata', async () => {
    await cassaforteSbloccata()
    cassaforte.blocca()
    await expect(cassaforte.cambiaPin('654321', ITERAZIONI_TEST)).rejects.toBeInstanceOf(
      cassaforte.CassaforteBloccata,
    )
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
    await cassaforte.attivaBiometria(crea)
    expect(cassaforte.biometriaAttiva.value).toBe(true)

    cassaforte.blocca()
    await expect(
      cassaforte.sbloccaConBiometria(async () => crypto.getRandomValues(new Uint8Array(32)).buffer),
    ).rejects.toThrow()
    await cassaforte.sbloccaConBiometria(async () => segreto)
    expect((await leggiDallaCache('k', database))!.dati).toEqual({ v: 2 })
  })

  it('la passkey di accesso resta; la vecchia passkey di sblocco si toglie dal gestore', async () => {
    const segnalate: string[] = []
    vi.stubGlobal('PublicKeyCredential', {
      signalUnknownCredential: vi.fn(async (o: { credentialId: string }) => {
        segnalate.push(o.credentialId)
      }),
    })
    try {
      await cassaforteSbloccata()
      await database.meta.put({ chiave: 'dispositivo_nome', valore: 'Mac di Andrea' })
      const segreto = crypto.getRandomValues(new Uint8Array(32)).buffer
      const crea = vi.fn<typeof creaPasskeyDiSblocco>(async () => ({
        idCredenziale: new Uint8Array([251, 255, 1]).buffer,
        segreto,
      }))
      // The login passkey of this device, named after it (DEC-295).
      await cassaforte.attivaBiometria(crea)
      expect(crea.mock.calls[0]![0]).toBe('Mac di Andrea')
      expect(cassaforte.conVecchiaPasskey()).toBe(false)
      // Switched off or wiped: it still lets you in, so it stays in the manager.
      await cassaforte.disattivaBiometria()
      await cassaforte.attivaBiometria(crea, 'Mac nuovo')
      expect(crea.mock.calls[1]![0]).toBe('Mac nuovo')
      // An old local unlock passkey (before DEC-295)…
      const config = (await database.protezione.get('config'))!
      delete config.biometria!.accesso
      await database.protezione.put(config)
      await cassaforte.inizializza()
      expect(cassaforte.conVecchiaPasskey()).toBe(true)
      expect(segnalate).toEqual([])
      // …goes when a login passkey replaces it (base64url, no padding)…
      await cassaforte.attivaBiometria(crea)
      await vi.waitFor(() => expect(segnalate).toEqual(['-_8B']))
      await cassaforte.cancella('uscita')
      await new Promise((fatto) => setTimeout(fatto, 10))
      expect(segnalate).toEqual(['-_8B'])
    } finally {
      vi.unstubAllGlobals()
    }
  })

  it('una vecchia passkey di sblocco si toglie anche quando i dati si cancellano', async () => {
    const segnalate: string[] = []
    vi.stubGlobal('PublicKeyCredential', {
      signalUnknownCredential: vi.fn(async (o: { credentialId: string }) => {
        segnalate.push(o.credentialId)
      }),
    })
    try {
      await cassaforteSbloccata()
      const segreto = crypto.getRandomValues(new Uint8Array(32)).buffer
      await cassaforte.attivaBiometria(async () => ({
        idCredenziale: new Uint8Array([1, 2, 3]).buffer,
        segreto,
      }))
      const config = (await database.protezione.get('config'))!
      delete config.biometria!.accesso
      await database.protezione.put(config)
      await cassaforte.inizializza()
      await cassaforte.cancella('uscita')
      await vi.waitFor(() => expect(segnalate).toEqual(['AQID']))
    } finally {
      vi.unstubAllGlobals()
    }
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
