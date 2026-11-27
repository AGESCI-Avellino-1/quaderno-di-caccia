import type {
  AmbitoVoceLibro,
  CondizioneVoce,
  LibroCerimonie,
  SquadrigliaVoceLibro,
  UnitaVoceLibro,
} from '@/api/qdc'

// Whose an entry of the book is (DEC-438), and the conditions the form proposes for it: who
// writes changes or removes them, they are only a start.

export const NOMI_AMBITO: Record<AmbitoVoceLibro, string> = {
  GRUPPO: 'Tutto il gruppo',
  COCA: 'Comunità capi',
  UNITA: 'Una o più unità',
  ALTA_SQ: 'Alta Squadriglia',
  CONSIGLIO_CAPI: 'Consiglio capi',
  SQUADRIGLIE: 'Una o più squadriglie',
  CONSIGLIO_ANZIANI: 'Consiglio degli Anziani',
}

const TIPI_LC = ['BRANCO', 'CERCHIO', 'BRANCO_CERCHIO']

/** The units an entry of that kind may be of, among those given (patrols: none, they are
 * chosen apart). */
export function unitaPer(ambito: AmbitoVoceLibro, unita: UnitaVoceLibro[]): UnitaVoceLibro[] {
  if (ambito === 'ALTA_SQ' || ambito === 'CONSIGLIO_CAPI')
    return unita.filter((u) => u.tipo === 'REPARTO')
  if (ambito === 'CONSIGLIO_ANZIANI') return unita.filter((u) => TIPI_LC.includes(u.tipo))
  if (ambito === 'UNITA') return unita.filter((u) => u.tipo !== 'COMUNITA_CAPI')
  return []
}

/** The kinds one may choose: the group's and the Co.Ca.'s for the capigruppo; the others
 * where one serves a unit of the right type (or a patrol of one's reparto). */
export function ambitiPossibili(
  libro: LibroCerimonie,
  unita: UnitaVoceLibro[],
  squadriglie: SquadrigliaVoceLibro[],
): AmbitoVoceLibro[] {
  const elenco: AmbitoVoceLibro[] = []
  if (libro.puo_tutto_il_gruppo) elenco.push('GRUPPO', 'COCA')
  if (unitaPer('UNITA', unita).length) elenco.push('UNITA')
  if (unitaPer('ALTA_SQ', unita).length) elenco.push('ALTA_SQ', 'CONSIGLIO_CAPI')
  if (squadriglie.length) elenco.push('SQUADRIGLIE')
  if (unitaPer('CONSIGLIO_ANZIANI', unita).length) elenco.push('CONSIGLIO_ANZIANI')
  return elenco
}

/** The conditions proposed for an entry: who belongs to what the entry is of. */
export function condizioniProposte(
  ambito: AmbitoVoceLibro,
  unita: number[],
  squadriglie: number[],
): CondizioneVoce[][] {
  switch (ambito) {
    case 'UNITA':
      return unita.map((id) => [{ tipo: 'unita', unita: id }])
    case 'ALTA_SQ':
      return unita.slice(0, 1).map((id) => [{ tipo: 'alta_squadriglia', unita: id }])
    case 'CONSIGLIO_CAPI':
      return unita.slice(0, 1).map((id) => [{ tipo: 'consiglio_capi', unita: id }])
    case 'SQUADRIGLIE':
      return squadriglie.map((id) => [{ tipo: 'squadriglia', squadriglia: id }])
    case 'CONSIGLIO_ANZIANI':
      return unita.slice(0, 1).map((id) => [
        { tipo: 'unita', unita: id },
        { tipo: 'incarico', ruolo: 'CONSIGLIO_ANZIANI' },
      ])
    default:
      // The capi read everything; the group's reaches the ragazzi/e only by choice.
      return []
  }
}
