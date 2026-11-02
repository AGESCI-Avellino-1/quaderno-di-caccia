import { afterEach, describe, expect, it } from 'vitest'

import {
  CHIAVE_CHIUSURA,
  leggiChiusura,
  modoInstallazione,
  ricompare,
  salvaChiusura,
} from '@/pwa/installazione'

const IPHONE =
  'Mozilla/5.0 (iPhone; CPU iPhone OS 18_5 like Mac OS X) AppleWebKit/605.1.15 ' +
  '(KHTML, like Gecko) Version/18.5 Mobile/15E148 Safari/604.1'
const CHROME_IPHONE =
  'Mozilla/5.0 (iPhone; CPU iPhone OS 18_5 like Mac OS X) AppleWebKit/605.1.15 ' +
  '(KHTML, like Gecko) CriOS/140.0.0.0 Mobile/15E148 Safari/604.1'
const MAC_SAFARI =
  'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 ' +
  '(KHTML, like Gecko) Version/18.5 Safari/605.1.15'
const MAC_CHROME =
  'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 ' +
  '(KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36'
const ANDROID_CHROME =
  'Mozilla/5.0 (Linux; Android 15; Pixel 9) AppleWebKit/537.36 (KHTML, like Gecko) ' +
  'Chrome/140.0.0.0 Mobile Safari/537.36'
const ANDROID_FIREFOX = 'Mozilla/5.0 (Android 15; Mobile; rv:140.0) Gecko/140.0 Firefox/140.0'
const WINDOWS_FIREFOX =
  'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:140.0) Gecko/20100101 Firefox/140.0'

const NIENTE = { installata: false, pulsante: false }

describe('dove si può installare l’app', () => {
  it('su iPhone e iPad, con qualunque browser, dà le istruzioni di Condividi', () => {
    expect(modoInstallazione(IPHONE, 5, NIENTE)).toBe('ios')
    expect(modoInstallazione(CHROME_IPHONE, 5, NIENTE)).toBe('ios')
    // iPadOS si presenta come un Mac, ma con lo schermo touch.
    expect(modoInstallazione(MAC_SAFARI, 5, NIENTE)).toBe('ios')
  })

  it('Safari sul Mac e Firefox su Android hanno le loro istruzioni', () => {
    expect(modoInstallazione(MAC_SAFARI, 0, NIENTE)).toBe('mac')
    expect(modoInstallazione(ANDROID_FIREFOX, 5, NIENTE)).toBe('firefox-android')
  })

  it('Chrome ed Edge solo quando il browser offre il pulsante', () => {
    expect(modoInstallazione(ANDROID_CHROME, 5, NIENTE)).toBeNull()
    expect(modoInstallazione(MAC_CHROME, 0, NIENTE)).toBeNull()
    expect(modoInstallazione(ANDROID_CHROME, 5, { installata: false, pulsante: true })).toBe(
      'pulsante',
    )
  })

  it('niente dove non si installa o se l’app è già installata', () => {
    expect(modoInstallazione(WINDOWS_FIREFOX, 0, NIENTE)).toBeNull()
    expect(modoInstallazione(IPHONE, 5, { installata: true, pulsante: false })).toBeNull()
    expect(modoInstallazione(ANDROID_CHROME, 5, { installata: true, pulsante: true })).toBeNull()
  })
})

describe('chiusura del banner', () => {
  afterEach(() => localStorage.clear())

  it('ricompare dopo i giorni impostati', () => {
    const chiusa = '2026-11-01T10:00:00.000Z'
    const giorno = 24 * 60 * 60 * 1000
    const quando = Date.parse(chiusa)
    expect(ricompare(null, 14)).toBe(true)
    expect(ricompare(chiusa, 14, quando + 13 * giorno)).toBe(false)
    expect(ricompare(chiusa, 14, quando + 14 * giorno)).toBe(true)
    expect(ricompare(chiusa, 30, quando + 20 * giorno)).toBe(false)
    expect(ricompare('non una data', 14, quando)).toBe(true)
  })

  it('si ricorda solo la data nel browser', () => {
    salvaChiusura(new Date('2026-11-02T08:00:00.000Z'))
    expect(localStorage.getItem(CHIAVE_CHIUSURA)).toBe('2026-11-02T08:00:00.000Z')
    expect(leggiChiusura()).toBe('2026-11-02T08:00:00.000Z')
  })
})
