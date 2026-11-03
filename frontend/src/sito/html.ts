/**
 * What the text editor may contain (DEC-250, DEC-305), mirrored from the server's list in
 * `backend/apps/impostazioni/html.py`, which is the one that counts: here it only tells
 * whoever writes HTML by hand what will be dropped.
 */
const TAG = new Set(
  'p br strong b em i u s ul ol li a h2 h3 table thead tbody tr th td img'.split(' '),
)
const ATTRIBUTI: Record<string, Set<string>> = {
  a: new Set(['href']),
  img: new Set(['src', 'alt', 'width']),
  th: new Set(['colspan', 'rowspan', 'style']),
  td: new Set(['colspan', 'rowspan', 'style']),
  p: new Set(['style']),
  h2: new Set(['style']),
  h3: new Set(['style']),
}
const ALLINEAMENTO = /^\s*text-align\s*:\s*(left|center|right)\s*;?\s*$/i
const IMMAGINI = '/api/v1/immagini/'

/** The parts of `html` the server will drop, each once, as they would be written. */
export function nonPermessi(html: string): string[] {
  const corpo = new DOMParser().parseFromString(html, 'text/html').body
  const tolti = new Set<string>()
  for (const el of Array.from(corpo.querySelectorAll('*'))) {
    const tag = el.tagName.toLowerCase()
    if (!TAG.has(tag)) {
      tolti.add(`<${tag}>`)
      continue
    }
    for (const { name, value } of Array.from(el.attributes)) {
      const permessi = ATTRIBUTI[tag]
      if (!permessi?.has(name)) tolti.add(`${name}="…" in <${tag}>`)
      else if (name === 'style' && !ALLINEAMENTO.test(value)) tolti.add(`style="${value}"`)
      else if (tag === 'img' && name === 'src' && !value.startsWith(IMMAGINI)) {
        tolti.add("un'immagine non caricata nell'app")
      }
    }
  }
  return [...tolti]
}
