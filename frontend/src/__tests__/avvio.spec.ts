import { readFile } from 'node:fs/promises'

import sharp from 'sharp'
import { describe, expect, it } from 'vitest'

import { escapeHtml, immagine, immaginiAvvio } from '../../scripts/avvio'

describe('la schermata di avvio', () => {
  it('ha un immagine per ogni schermo, senza doppioni', () => {
    const elenco = immaginiAvvio()
    expect(new Set(elenco.map((i) => i.file)).size).toBe(elenco.length)
    expect(new Set(elenco.map((i) => i.media)).size).toBe(elenco.length)
    // The iPhone 18 Pro Max of the report (1320×2868).
    const grande = elenco.find((i) => i.file === 'avvio/1320x2868.png')!
    expect(grande.media).toContain('device-width: 440px')
    expect(grande.media).toContain('ratio: 3')
    // An iPad on its side: the device keeps its portrait sizes in the query.
    const girato = elenco.find((i) => i.file === 'avvio/2048x1536.png')!
    expect(girato.media).toContain('device-width: 768px')
    expect(girato.media).toContain('landscape')
  })

  it('crea l immagine della misura giusta, senza trasparenze', async () => {
    const logo = await readFile('public/icons/icon-512.png')
    const dati = await immagine(logo, 'AGESCI Gruppo <Prova> & co', 750, 1334, 2)
    const info = await sharp(dati).metadata()
    expect([info.width, info.height]).toEqual([750, 1334])
    expect(info.hasAlpha).toBe(false)
    const lungo = await immagine(
      logo,
      'Un nome di gruppo davvero molto lungo '.repeat(4),
      750,
      1334,
      2,
    )
    expect((await sharp(lungo).metadata()).width).toBe(750)
    const senza = await immagine(logo, '', 750, 1334, 2)
    expect(senza.length).toBeGreaterThan(0)
  })

  it('protegge il nome del gruppo', () => {
    expect(escapeHtml('A & <b>"')).toBe('A &amp; &lt;b&gt;&quot;')
  })
})
