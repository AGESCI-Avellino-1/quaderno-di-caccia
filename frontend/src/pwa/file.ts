/** Files in the app installed on an iPhone (issue #12): iOS opens a link to a file, even
 * one served as an attachment, full screen inside the app, with no way back and no way to
 * share or save it. There the file is fetched instead and offered through the share sheet
 * (`FileDaSalvare.vue`). Everywhere else the links work as they always did.
 *
 * The file stays in memory until the person chooses: nothing is kept on the device. */
import { shallowRef } from 'vue'

import { ErroreApi } from '@/api/http'
import { testoErrore } from '@/composables/useErrore'

export type FileInArrivo =
  { stato: 'attesa' } | { stato: 'pronto'; file: File } | { stato: 'errore'; messaggio: string }

export const fileInArrivo = shallowRef<FileInArrivo | null>(null)

/** `navigator.standalone` exists on iOS only, true in the installed app. */
export function pwaSuIos(): boolean {
  return (navigator as Navigator & { standalone?: boolean }).standalone === true
}

const ESTENSIONI: Record<string, string> = {
  'application/pdf': '.pdf',
  'image/jpeg': '.jpg',
  'image/png': '.png',
}

/** The name in `Content-Disposition`, else the last part of the address; the extension
 * from the type when the name has none (some files are served without a name). */
export function nomeDelFile(risposta: Response, indirizzo: string): string {
  const intestazione = risposta.headers.get('Content-Disposition') ?? ''
  const codificato = /filename\*=UTF-8''([^;]+)/i.exec(intestazione)?.[1]
  const semplice = /filename="?([^";]+)"?/i.exec(intestazione)?.[1]
  let nome = semplice?.trim() ?? ''
  if (codificato) {
    try {
      nome = decodeURIComponent(codificato)
    } catch {
      // Malformed: the plain name, or the address, will do.
    }
  }
  if (!nome) nome = new URL(indirizzo, location.origin).pathname.split('/').pop() || 'file'
  const tipo = (risposta.headers.get('Content-Type') ?? '').split(';')[0]!.trim()
  return nome.includes('.') ? nome : nome + (ESTENSIONI[tipo] ?? '')
}

/** The link to one of the app's files a click landed on, if any. Every link to the API is
 * a file: pages and data are read with `fetch`. */
export function linkAFile(evento: MouseEvent): HTMLAnchorElement | null {
  if (evento.defaultPrevented || evento.metaKey || evento.ctrlKey || evento.shiftKey) return null
  const link = (evento.target as Element | null)?.closest?.('a[href]')
  if (!(link instanceof HTMLAnchorElement)) return null
  const indirizzo = new URL(link.href, location.origin)
  if (indirizzo.origin !== location.origin) return null
  return indirizzo.pathname.startsWith('/api/v1/') ? link : null
}

export async function scaricaFile(indirizzo: string): Promise<void> {
  const attesa: FileInArrivo = { stato: 'attesa' }
  fileInArrivo.value = attesa
  let esito: FileInArrivo
  try {
    const risposta = await fetch(indirizzo, { credentials: 'same-origin' })
    if (!risposta.ok) {
      const json = risposta.headers.get('Content-Type')?.includes('application/json')
      throw new ErroreApi(risposta.status, json ? await risposta.json() : null)
    }
    const contenuto = await risposta.blob()
    const nome = nomeDelFile(risposta, indirizzo)
    esito = { stato: 'pronto', file: new File([contenuto], nome, { type: contenuto.type }) }
  } catch (e) {
    esito = { stato: 'errore', messaggio: testoErrore(e) }
  }
  // Closed while it was on its way: nothing more to show.
  if (fileInArrivo.value === attesa) fileInArrivo.value = esito
}

/** A file made in the page (a QR code, an address book, a JSON export). */
export function salvaFile(contenuto: Blob, nome: string): void {
  if (pwaSuIos()) {
    const file = new File([contenuto], nome, { type: contenuto.type })
    fileInArrivo.value = { stato: 'pronto', file }
    return
  }
  const link = document.createElement('a')
  link.href = URL.createObjectURL(contenuto)
  link.download = nome
  link.click()
  URL.revokeObjectURL(link.href)
}
