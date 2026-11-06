import { effectScope, type EffectScope } from 'vue'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { useFinestraVisibile } from '@/composables/useFinestraVisibile'

const ALTO = '--qdc-finestra-alto'
const ALTEZZA = '--qdc-finestra-altezza'

function finestra(offsetTop: number, height: number, scale = 1) {
  const vista = Object.assign(new EventTarget(), { offsetTop, height, scale })
  vi.stubGlobal('visualViewport', vista)
  return vista
}

describe('useFinestraVisibile', () => {
  let scope: EffectScope

  const avvia = () => scope.run(() => useFinestraVisibile())
  const radice = () => document.documentElement.style

  beforeEach(() => {
    scope = effectScope()
    vi.stubGlobal('innerHeight', 900)
    vi.stubGlobal('scrollTo', vi.fn())
  })

  afterEach(() => {
    scope.stop()
    vi.unstubAllGlobals()
    radice().removeProperty(ALTO)
    radice().removeProperty(ALTEZZA)
    document.body.innerHTML = ''
  })

  it('leaves the frame alone when the viewport is right', () => {
    finestra(0, 900)
    avvia()
    expect(radice().getPropertyValue(ALTO)).toBe('')
    expect(radice().getPropertyValue(ALTEZZA)).toBe('')
  })

  it('follows a viewport left shifted and shorter, and lets go when it recovers', () => {
    const vista = finestra(120, 780)
    avvia()
    expect(radice().getPropertyValue(ALTO)).toBe('120px')
    expect(radice().getPropertyValue(ALTEZZA)).toBe('780px')

    Object.assign(vista, { offsetTop: 0, height: 900 })
    vista.dispatchEvent(new Event('resize'))
    expect(radice().getPropertyValue(ALTO)).toBe('')
  })

  it('does not move the page while a text field is being edited', () => {
    const campo = document.body.appendChild(document.createElement('input'))
    const vista = finestra(120, 500)
    vi.stubGlobal('scrollY', 120)
    campo.focus()
    avvia()
    vista.dispatchEvent(new Event('resize'))
    expect(radice().getPropertyValue(ALTO)).toBe('')
    expect(window.scrollTo).not.toHaveBeenCalled()

    campo.blur()
    expect(radice().getPropertyValue(ALTO)).toBe('120px')
    expect(window.scrollTo).toHaveBeenCalledWith(0, 0)
  })

  it('realigns when the camera closes, even with the file field still focused', () => {
    const foto = document.body.appendChild(document.createElement('input'))
    foto.type = 'file'
    const vista = finestra(0, 900)
    avvia()
    foto.focus()
    Object.assign(vista, { offsetTop: 90, height: 810 })
    foto.dispatchEvent(new Event('change', { bubbles: true }))
    expect(radice().getPropertyValue(ALTO)).toBe('90px')
  })

  it('leaves a page zoomed with two fingers alone', () => {
    finestra(200, 400, 2)
    avvia()
    expect(radice().getPropertyValue(ALTO)).toBe('')
  })

  it('stops listening when the scope ends', () => {
    const vista = finestra(0, 900)
    avvia()
    scope.stop()
    Object.assign(vista, { offsetTop: 90, height: 810 })
    vista.dispatchEvent(new Event('resize'))
    expect(radice().getPropertyValue(ALTO)).toBe('')
  })
})
