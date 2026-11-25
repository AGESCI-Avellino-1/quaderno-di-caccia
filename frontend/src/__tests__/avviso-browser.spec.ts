import { readFileSync } from 'node:fs'

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

// DEC-433: public/avviso-browser.js, run as the page does.
const script = readFileSync('public/avviso-browser.js', 'utf8')
const esegui = () => new Function(script)()
const avviso = () => document.getElementById('avviso-browser')

function browser(manca?: string) {
  vi.stubGlobal('CSS', {
    supports: (...argomenti: string[]) => !manca || !argomenti.join(' ').includes(manca),
  })
  vi.stubGlobal('CSSLayerBlockRule', class {})
  vi.stubGlobal('HTMLDialogElement', class {})
  Object.defineProperty(HTMLScriptElement.prototype, 'noModule', {
    value: false,
    configurable: true,
  })
}

describe('warning in browsers too old', () => {
  beforeEach(() => {
    document.body.innerHTML = '<div id="app"></div>'
    sessionStorage.clear()
  })
  afterEach(() => {
    vi.unstubAllGlobals()
    Reflect.deleteProperty(HTMLScriptElement.prototype, 'noModule')
  })

  it('nothing in a browser that works', () => {
    browser()
    esegui()
    expect(avviso()).toBeNull()
  })

  it.each(['light-dark', 'oklch(50%', 'color-mix', 'container-type', ':has'])(
    'shown without %s',
    (manca) => {
      browser(manca)
      esegui()
      expect(avviso()?.textContent).toContain('Il tuo dispositivo non è abbastanza aggiornato')
      expect(document.body.firstElementChild).toBe(avviso())
    },
  )

  it('shown without CSS.supports at all', () => {
    browser()
    vi.stubGlobal('CSS', undefined)
    esegui()
    expect(avviso()).not.toBeNull()
  })

  it('closed, it does not come back until the app is opened again', () => {
    browser('light-dark')
    esegui()
    avviso()!.querySelector('button')!.click()
    expect(avviso()).toBeNull()
    esegui()
    expect(avviso()).toBeNull()
    sessionStorage.clear()
    esegui()
    expect(avviso()).not.toBeNull()
  })
})
