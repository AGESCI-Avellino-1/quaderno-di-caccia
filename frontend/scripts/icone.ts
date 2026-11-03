/**
 * The app's icons from one logo (DEC-294): favicons, the iPhone icon, the PWA icons
 * (also "maskable") and the logo of the top bar and of the error pages, which use
 * `icons/icon-192.png`.
 *
 * The icons in `public/` are the AGESCI ones, from `resources/AGESCI.svg`: regenerate
 * them with `node scripts/icone.ts`. A group's own logo (`QDC_LOGO` in `.env`) is
 * applied by `vite.config.ts` to a copy of `public/`, never to the files in git.
 *
 *   node scripts/icone.ts [logo] [cartella]   # SVG or PNG; default the AGESCI logo, public/
 */
import { mkdir, writeFile } from 'node:fs/promises'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'

import sharp from 'sharp'

export const RADICE = join(dirname(fileURLToPath(import.meta.url)), '..', '..')
export const LOGO_AGESCI = join(RADICE, 'resources', 'AGESCI.svg')

const BIANCO = { r: 255, g: 255, b: 255 }

/** File, side in pixels, empty margin on each side as a fraction of the side. */
const ICONE: [string, number, number][] = [
  ['favicon-16x16.png', 16, 0.03],
  ['favicon-32x32.png', 32, 0.03],
  ['apple-touch-icon.png', 180, 0.08],
  ['icons/icon-192.png', 192, 0.08],
  ['icons/icon-512.png', 512, 0.08],
  // Android may cut a maskable icon to a circle: the logo stays in the safe zone.
  ['icons/icon-512-maskable.png', 512, 0.2],
]

/** The logo centred on a white square: icons are opaque (the iPhone wants it). */
async function icona(logo: Buffer, lato: number, margine: number): Promise<Buffer> {
  const interno = Math.round(lato * (1 - 2 * margine))
  // A high density renders an SVG sharp at any size; a PNG ignores it.
  const disegno = await sharp(logo, { density: 1200 })
    .resize(interno, interno, { fit: 'contain', background: { ...BIANCO, alpha: 1 } })
    .flatten({ background: BIANCO })
    .png()
    .toBuffer()
  return sharp({ create: { width: lato, height: lato, channels: 3, background: BIANCO } })
    .composite([{ input: disegno, gravity: 'centre' }])
    .removeAlpha()
    .png()
    .toBuffer()
}

export async function generaIcone(logo: Buffer, cartella: string): Promise<void> {
  for (const [file, lato, margine] of ICONE) {
    const destinazione = join(cartella, file)
    await mkdir(dirname(destinazione), { recursive: true })
    await writeFile(destinazione, await icona(logo, lato, margine))
  }
}

if (process.argv[1] === fileURLToPath(import.meta.url)) {
  const { readFile } = await import('node:fs/promises')
  const logo = process.argv[2] ?? LOGO_AGESCI
  const cartella = process.argv[3] ?? join(RADICE, 'frontend', 'public')
  await generaIcone(await readFile(logo), cartella)
  console.log(`Icone create in ${cartella} dal logo ${logo}.`)
}
