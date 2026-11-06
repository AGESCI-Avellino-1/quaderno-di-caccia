/**
 * Keeps the page frame on the part of the screen the phone really shows (DEC-370).
 *
 * After the keyboard or the camera, iOS can leave the visual viewport shifted and shorter
 * than the window, and only restarting the app clears it (WebKit bug 297779). `.qdc-cornice`
 * does not scroll, so the header would stay out of reach: the frame follows the viewport
 * instead. While a field is being edited nothing changes, iOS is moving the page on purpose
 * to show it; a page zoomed with two fingers is left alone too.
 */
import { onScopeDispose } from 'vue'

const ALTO = '--qdc-finestra-alto'
const ALTEZZA = '--qdc-finestra-altezza'
/** iOS updates the viewport a moment after the keyboard or the camera has gone. */
const RITARDO_CONTROLLO_MS = 400

const CAMPI_DI_TESTO =
  'input:not([type="file"], [type="checkbox"], [type="radio"], [type="button"], [type="submit"]), textarea, select, [contenteditable="true"]'

function staScrivendo(): boolean {
  return document.activeElement?.matches(CAMPI_DI_TESTO) ?? false
}

function allinea() {
  const vista = window.visualViewport
  const radice = document.documentElement.style
  if (!vista) return
  const zoom = Math.abs(vista.scale - 1) > 0.01
  const spostata =
    Math.abs(vista.offsetTop) >= 1 || Math.abs(vista.height - window.innerHeight) >= 1
  if (zoom || staScrivendo() || !spostata) {
    radice.removeProperty(ALTO)
    radice.removeProperty(ALTEZZA)
  } else {
    radice.setProperty(ALTO, `${vista.offsetTop}px`)
    radice.setProperty(ALTEZZA, `${vista.height}px`)
  }
  if (!zoom && !staScrivendo() && window.scrollY !== 0) window.scrollTo(0, 0)
}

export function useFinestraVisibile() {
  const vista = window.visualViewport
  if (!vista) return

  let timer: number | undefined
  const allineaOraEDopo = () => {
    allinea()
    window.clearTimeout(timer)
    timer = window.setTimeout(allinea, RITARDO_CONTROLLO_MS)
  }

  vista.addEventListener('resize', allinea)
  vista.addEventListener('scroll', allinea)
  // `change` is the file field when the camera closes.
  for (const evento of ['focusin', 'focusout', 'change', 'visibilitychange']) {
    document.addEventListener(evento, allineaOraEDopo)
  }
  for (const evento of ['focus', 'pageshow']) window.addEventListener(evento, allineaOraEDopo)
  allinea()

  onScopeDispose(() => {
    window.clearTimeout(timer)
    vista.removeEventListener('resize', allinea)
    vista.removeEventListener('scroll', allinea)
    for (const evento of ['focusin', 'focusout', 'change', 'visibilitychange']) {
      document.removeEventListener(evento, allineaOraEDopo)
    }
    for (const evento of ['focus', 'pageshow']) window.removeEventListener(evento, allineaOraEDopo)
  })
}
