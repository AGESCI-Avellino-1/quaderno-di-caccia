/**
 * Placeholders such as [Gruppo] in the title and footer the group writes (DEC-246,
 * DEC-247). The server refuses unknown ones; here they are filled in, because only
 * the PWA knows the page being shown.
 */
import type { Sito } from '@/api/qdc'

export const SEGNAPOSTO_TITOLO = [
  ['Nome sito', 'il nome del sito, es. Quaderno di Caccia'],
  ['Sigla sito', 'la sigla del sito, es. QdC'],
  ['Gruppo', 'il nome del gruppo, es. AGESCI Avellino 1'],
  ['Sigla gruppo', 'la sigla del gruppo, es. AV1'],
  ['Anno', "l'anno scout, es. 2025/26"],
  ['Pagina corrente', 'il nome della pagina aperta, es. Eventi'],
] as const

export const SITO_DI_BASE: Sito = {
  nome_sito: 'Quaderno di Caccia',
  sigla_sito: 'QdC',
  gruppo: '',
  sigla_gruppo: '',
  anno: '',
  titolo_completo: '[Nome sito] - [Gruppo]',
  titolo_breve: '[Sigla sito] - [Sigla gruppo]',
  riga_piede: '',
}

/** Fill in the placeholders; an empty abbreviation falls back to the name. */
export function riempi(testo: string, sito: Sito, pagina = ''): string {
  const valori: Record<string, string> = {
    'nome sito': sito.nome_sito,
    'sigla sito': sito.sigla_sito || sito.nome_sito,
    gruppo: sito.gruppo,
    'sigla gruppo': sito.sigla_gruppo || sito.gruppo,
    anno: sito.anno,
    'pagina corrente': pagina,
  }
  const VUOTO = '\uE000'
  const pieno = testo.replace(/\[([^[\]]+)\]/g, (tutto, nome: string) => {
    const valore = valori[nome.trim().toLowerCase()]
    if (valore === undefined) return tutto
    return valore || VUOTO
  })
  // An empty placeholder (no group yet, no page) takes one separator with it, so the
  // title never shows a dangling " - ".
  return pieno
    .replace(/\s*[-–·|:]\s*\uE000/g, '')
    .replace(/\uE000\s*[-–·|:]\s*/g, '')
    .replaceAll(VUOTO, '')
    .replace(/\s{2,}/g, ' ')
    .trim()
}
