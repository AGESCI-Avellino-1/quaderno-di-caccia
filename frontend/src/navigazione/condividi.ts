/**
 * «Invita nel gruppo» (DEC-304): the link of the public waiting list (DEC-256) and its QR
 * code, drawn on the device so they work without the network too. The link is the same
 * for everybody: nothing in it says who shares it.
 */
import { encode } from 'uqr'

export function indirizzoListaAttesa(origine = window.location.origin): string {
  return `${origine}/lista-attesa`
}

/** The QR modules, border included: `true` is a dark one. */
export function moduliQr(testo: string): boolean[][] {
  return encode(testo, { ecc: 'M', border: 2 }).data
}

/** One SVG path drawing the dark modules, one unit per module. */
export function percorsoQr(moduli: boolean[][]): string {
  const pezzi: string[] = []
  moduli.forEach((riga, y) =>
    riga.forEach((scuro, x) => {
      if (scuro) pezzi.push(`M${x} ${y}h1v1h-1z`)
    }),
  )
  return pezzi.join('')
}

/** The QR as a PNG image, `lato` pixels wide, black on white for printing. */
export function pngQr(testo: string, lato = 1024): Promise<Blob> {
  const moduli = moduliQr(testo)
  const passo = Math.floor(lato / moduli.length)
  const tela = document.createElement('canvas')
  tela.width = tela.height = passo * moduli.length
  const penna = tela.getContext('2d')
  if (!penna) return Promise.reject(new Error('Il browser non sa disegnare immagini.'))
  penna.fillStyle = '#ffffff'
  penna.fillRect(0, 0, tela.width, tela.height)
  penna.fillStyle = '#000000'
  moduli.forEach((riga, y) =>
    riga.forEach((scuro, x) => {
      if (scuro) penna.fillRect(x * passo, y * passo, passo, passo)
    }),
  )
  return new Promise((risolvi, rifiuta) =>
    tela.toBlob(
      (b) => (b ? risolvi(b) : rifiuta(new Error("Non sono riuscito a creare l'immagine."))),
      'image/png',
    ),
  )
}
