import { appInstallata } from './installazione'

/**
 * Keeps the start screen on top of the app in the installed app, until its minimum duration
 * from the opening has passed (DEC-333). To call before mounting: Vue empties `#app`. The app
 * loads underneath, so a slow start does not wait any longer; in the browser nothing changes.
 */
export function tieniSchermataDiAvvio(): void {
  const avvio = document.querySelector<HTMLElement>('#app .avvio')
  if (!avvio || !appInstallata()) return
  const resta = Number(avvio.dataset.durata) * 1000 - performance.now()
  if (!(resta > 0)) return
  document.body.append(avvio)
  setTimeout(() => avvio.remove(), resta)
}
