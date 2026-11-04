import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { tieniSchermataDiAvvio } from '@/pwa/avvio'

import { durataAvvio } from '../../scripts/avvio'

function installata(si: boolean) {
  Object.defineProperty(navigator, 'standalone', { value: si, configurable: true })
}

describe('la durata minima della schermata di avvio', () => {
  beforeEach(() => {
    vi.useFakeTimers({ toFake: ['setTimeout'] })
    vi.spyOn(performance, 'now').mockReturnValue(500)
    document.body.innerHTML = '<div id="app"><div class="avvio" data-durata="2"></div></div>'
  })

  afterEach(() => {
    vi.useRealTimers()
    vi.restoreAllMocks()
    Reflect.deleteProperty(navigator, 'standalone')
    document.body.innerHTML = ''
  })

  it('nell app installata resta sopra l app per il tempo che manca', () => {
    installata(true)
    tieniSchermataDiAvvio()
    // Vue empties #app when it mounts: the page must be out of it.
    expect(document.querySelector('#app .avvio')).toBeNull()
    expect(document.querySelector('body > .avvio')).not.toBeNull()
    vi.advanceTimersByTime(1499)
    expect(document.querySelector('.avvio')).not.toBeNull()
    vi.advanceTimersByTime(1)
    expect(document.querySelector('.avvio')).toBeNull()
  })

  it('nel browser non cambia niente', () => {
    installata(false)
    tieniSchermataDiAvvio()
    expect(document.querySelector('#app .avvio')).not.toBeNull()
  })

  it('non aspetta se il tempo è già passato o la durata è zero', () => {
    installata(true)
    vi.mocked(performance.now).mockReturnValue(2500)
    tieniSchermataDiAvvio()
    expect(document.querySelector('#app .avvio')).not.toBeNull()

    vi.mocked(performance.now).mockReturnValue(0)
    document.querySelector<HTMLElement>('.avvio')!.dataset.durata = '0'
    tieniSchermataDiAvvio()
    expect(document.querySelector('#app .avvio')).not.toBeNull()
  })

  it('legge la durata dalla configurazione', () => {
    expect(durataAvvio(undefined)).toBe(2)
    expect(durataAvvio(' ')).toBe(2)
    expect(durataAvvio('0')).toBe(0)
    expect(durataAvvio('1.5')).toBe(1.5)
    expect(() => durataAvvio('due')).toThrow('QDC_DURATA_AVVIO')
    expect(() => durataAvvio('-1')).toThrow('QDC_DURATA_AVVIO')
  })
})
