/**
 * The start screen (DEC-332): a ruled page with the label of an exercise book. The iPhone
 * and the iPad show an image made for their exact screen, built here from the group's logo;
 * Android draws its own from the manifest; `index.html` shows the same page while the app
 * loads. Built at every build, never kept in git.
 */
import { readFileSync } from 'node:fs'
import { mkdir, writeFile } from 'node:fs/promises'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'

import sharp from 'sharp'

const INDACO = '#462d7b'
const RIGA = '#c8d7ee'
const MARGINE = '#e58a8f'

export const NOME_APP = 'Quaderno di Caccia'

/** CSS width and height, pixel ratio. Portrait; the iPads also turn. */
export const SCHERMI: { l: number; a: number; d: number; ruota?: boolean }[] = [
  { l: 440, a: 956, d: 3 }, // iPhone 16/17 Pro Max
  { l: 430, a: 932, d: 3 }, // iPhone 14 Pro Max, 15/16 Plus
  { l: 428, a: 926, d: 3 }, // iPhone 12/13 Pro Max, 14 Plus
  { l: 420, a: 912, d: 3 }, // iPhone Air
  { l: 414, a: 896, d: 3 }, // iPhone XS Max, 11 Pro Max
  { l: 414, a: 896, d: 2 }, // iPhone XR, 11
  { l: 414, a: 736, d: 3 }, // iPhone 8 Plus
  { l: 402, a: 874, d: 3 }, // iPhone 16/17 Pro
  { l: 393, a: 852, d: 3 }, // iPhone 14/15 Pro, 15/16
  { l: 390, a: 844, d: 3 }, // iPhone 12/13/14
  { l: 375, a: 812, d: 3 }, // iPhone X, XS, 11 Pro, mini
  { l: 375, a: 667, d: 2 }, // iPhone 8, SE
  { l: 768, a: 1024, d: 2, ruota: true }, // iPad
  { l: 810, a: 1080, d: 2, ruota: true },
  { l: 820, a: 1180, d: 2, ruota: true }, // iPad Air
  { l: 834, a: 1194, d: 2, ruota: true }, // iPad Pro 11
  { l: 1024, a: 1366, d: 2, ruota: true }, // iPad Pro 12.9
]

export interface ImmagineAvvio {
  file: string
  larghezza: number
  altezza: number
  media: string
}

/** Every image to make and the media query that picks it. */
export function immaginiAvvio(): ImmagineAvvio[] {
  const voce = (l: number, a: number, d: number, orientamento: string, ls: number, as: number) => ({
    file: `avvio/${l * d}x${a * d}.png`,
    larghezza: l * d,
    altezza: a * d,
    media:
      `(device-width: ${ls}px) and (device-height: ${as}px) and ` +
      `(-webkit-device-pixel-ratio: ${d}) and (orientation: ${orientamento})`,
  })
  return SCHERMI.flatMap(({ l, a, d, ruota }) => [
    voce(l, a, d, 'portrait', l, a),
    ...(ruota ? [voce(a, l, d, 'landscape', l, a)] : []),
  ])
}

/** Seconds the installed app keeps the start screen (DEC-333): `QDC_DURATA_AVVIO`, default 2. */
export function durataAvvio(valore: string | undefined): number {
  const testo = valore?.trim()
  if (!testo) return 2
  if (!/^\d+(\.\d+)?$/.test(testo)) {
    throw new Error(`QDC_DURATA_AVVIO deve essere un numero di secondi: ${testo}`)
  }
  return Number(testo)
}

export function escapeHtml(testo: string): string {
  return testo
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
}

interface Font {
  em: number
  alto: number
  basso: number
  glifi: Record<string, { a: number; d: string }>
}

// The outlines of the bundled Titillium Web (SIL OFL, font/OFL.txt), by character. Text is
// drawn as shapes: the same everywhere, also where the app is built, which has no fonts,
// and sharp's own text ignores a font file on some systems.
const CONTORNI: Record<'Bold' | 'Regular', Font> = JSON.parse(
  readFileSync(join(dirname(fileURLToPath(import.meta.url)), 'font', 'contorni.json'), 'utf-8'),
)

/** A line of text as a transparent PNG, smaller if it would not fit in `larghezza`. */
async function scritta(testo: string, font: 'Bold' | 'Regular', pixel: number, larghezza: number) {
  const { em, alto, basso, glifi } = CONTORNI[font]
  const spazio = glifi[' ']?.a ?? em / 4
  let x = 0
  const forme: string[] = []
  for (const carattere of testo) {
    const glifo = glifi[carattere]
    if (glifo) forme.push(`<path transform="translate(${x} 0)" d="${glifo.d}"/>`)
    x += glifo?.a ?? spazio
  }
  const scala = Math.min(pixel / em, larghezza / Math.max(x, 1))
  const l = Math.max(1, Math.ceil(x * scala))
  const a = Math.max(1, Math.ceil((alto + basso) * scala))
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="${l}" height="${a}">
    <g fill="${INDACO}" transform="scale(${scala} ${-scala}) translate(0 ${-alto})">${forme.join('')}</g>
  </svg>`
  return { data: await sharp(Buffer.from(svg)).png().toBuffer(), larghezza: l, altezza: a }
}

function pagina(l: number, a: number, unita: number): string {
  const passo = Math.round(24 * unita)
  const righe: string[] = []
  for (let y = passo; y < a; y += passo) {
    righe.push(`<rect x="0" y="${y}" width="${l}" height="${Math.max(1, Math.round(unita))}"/>`)
  }
  const margine = Math.round(l * 0.15)
  return `<svg xmlns="http://www.w3.org/2000/svg" width="${l}" height="${a}">
    <rect width="${l}" height="${a}" fill="#ffffff"/>
    <g fill="${RIGA}">${righe.join('')}</g>
    <rect x="${margine}" y="0" width="${Math.max(1, Math.round(unita))}" height="${a}" fill="${MARGINE}"/>
  </svg>`
}

/** The ruled page with the label in its centre. */
export async function immagine(
  logo: Buffer,
  gruppo: string,
  larghezza: number,
  altezza: number,
  densita: number,
): Promise<Buffer> {
  const unita = densita
  // A tablet, or a phone on its side, must not get a label as big as the screen.
  const lato = Math.round(Math.min(larghezza * 0.78, altezza * 0.42))
  const interno = lato - Math.round(20 * unita)
  const disegno = await sharp(logo)
    .resize(Math.round(lato * 0.72), Math.round(lato * 0.72), {
      fit: 'contain',
      background: { r: 255, g: 255, b: 255, alpha: 1 },
    })
    .flatten({ background: { r: 255, g: 255, b: 255 } })
    .png()
    .toBuffer()
  const altoDisegno = Math.round(lato * 0.72)
  const scala = lato / (304 * unita)
  const nome = await scritta(NOME_APP, 'Bold', Math.round(19 * unita * scala), interno)
  const sotto = gruppo
    ? await scritta(gruppo, 'Regular', Math.round(13 * unita * scala), interno)
    : null
  const spazio = Math.round(8 * unita)
  const bordo = Math.round(12 * unita)
  const alto =
    bordo * 2 + altoDisegno + spazio + nome.altezza + (sotto ? spazio / 2 + sotto.altezza : 0)
  const x = Math.round((larghezza - lato) / 2)
  const y = Math.round((altezza - alto) / 2)
  const raggio = Math.round(6 * unita)
  const etichetta = `<svg xmlns="http://www.w3.org/2000/svg" width="${lato}" height="${alto}">
    <rect x="${unita / 2}" y="${unita / 2}" width="${lato - unita}" height="${alto - unita}"
      rx="${raggio}" fill="#ffffff" stroke="${INDACO}" stroke-width="${unita}"/>
  </svg>`
  const alCentro = (l: number) => x + Math.round((lato - l) / 2)
  const yNome = y + bordo + altoDisegno + spazio
  const livelli = [
    { input: Buffer.from(etichetta), left: x, top: y },
    { input: disegno, left: alCentro(altoDisegno), top: y + bordo },
    { input: nome.data, left: alCentro(nome.larghezza), top: yNome },
    ...(sotto
      ? [
          {
            input: sotto.data,
            left: alCentro(sotto.larghezza),
            top: yNome + nome.altezza + Math.round(spazio / 2),
          },
        ]
      : []),
  ]
  return sharp(Buffer.from(pagina(larghezza, altezza, unita)))
    .composite(livelli)
    .removeAlpha()
    .png({ palette: true })
    .toBuffer()
}

export async function generaAvvio(
  logo: Buffer,
  gruppo: string,
  cartella: string,
): Promise<ImmagineAvvio[]> {
  const elenco = immaginiAvvio()
  await mkdir(join(cartella, 'avvio'), { recursive: true })
  // Once, big enough for all: an SVG logo at this density takes seconds each time.
  const disegno = await sharp(logo, { density: 1200 })
    .resize(1600, 1600, { fit: 'contain', background: { r: 255, g: 255, b: 255, alpha: 1 } })
    .png()
    .toBuffer()
  for (const voce of elenco) {
    const densita = Number(/ratio: (\d)/.exec(voce.media)![1])
    const dati = await immagine(disegno, gruppo, voce.larghezza, voce.altezza, densita)
    await writeFile(join(cartella, voce.file), dati)
  }
  return elenco
}
