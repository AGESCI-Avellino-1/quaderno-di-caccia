// Warns where the browser is too old for Bootstrap 6 (DEC-433), from an idea of
// django-agesci-campania-theme 3.0.0a5. A classic ES5 script, outside the bundle and before the
// app: it must run right where the app cannot. It checks the features, not the version, so an
// old browser that works sees nothing. Its styles are here, not to depend on Bootstrap.
;(function () {
  'use strict'

  var CHIAVE = 'qdc-avviso-browser-chiuso'
  var TESTO =
    'Il tuo dispositivo non è abbastanza aggiornato per usare bene il Quaderno di Caccia: ' +
    'aggiornalo o apri l’app da un altro dispositivo.'

  function supporta(proprieta, valore) {
    return CSS.supports(proprieta, valore)
  }

  function compatibile() {
    return (
      !!(window.CSS && CSS.supports) &&
      supporta('color', 'light-dark(red, blue)') &&
      supporta('color', 'oklch(50% 0.1 20)') &&
      supporta('color', 'color-mix(in oklch, red, blue)') &&
      supporta('container-type', 'inline-size') &&
      CSS.supports('selector(:has(a))') &&
      'CSSLayerBlockRule' in window &&
      'HTMLDialogElement' in window &&
      'noModule' in document.createElement('script')
    )
  }

  if (compatibile()) return
  try {
    if (sessionStorage.getItem(CHIAVE)) return
  } catch (e) {
    void e // storage blocked: shown anyway
  }

  var avviso = document.createElement('div')
  avviso.id = 'avviso-browser'
  avviso.setAttribute('role', 'alert')
  // Over the start screen too, which stays there if the app does not start.
  avviso.style.cssText =
    'position:-webkit-sticky;position:sticky;top:0;z-index:10000;display:-webkit-flex;display:flex;' +
    '-webkit-align-items:center;align-items:center;padding:12px 16px;background:#fff3cd;' +
    'color:#332701;border-bottom:1px solid #997404;font:16px/1.4 sans-serif'
  var testo = document.createElement('span')
  testo.style.cssText = '-webkit-flex:1;flex:1'
  testo.textContent = TESTO
  var chiudi = document.createElement('button')
  chiudi.type = 'button'
  chiudi.textContent = 'Chiudi'
  chiudi.style.cssText =
    'margin-left:16px;padding:6px 12px;background:#332701;color:#fff;border:0;border-radius:4px;' +
    'font:inherit;cursor:pointer'
  chiudi.onclick = function () {
    avviso.parentNode.removeChild(avviso)
    try {
      sessionStorage.setItem(CHIAVE, '1')
    } catch (e) {
      void e // storage blocked: it comes back at the next page
    }
  }
  avviso.appendChild(testo)
  avviso.appendChild(chiudi)
  document.body.insertBefore(avviso, document.body.firstChild)
})()
