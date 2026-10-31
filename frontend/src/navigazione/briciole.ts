/**
 * The breadcrumb (DEC-244): the menu group, the pages above this one (router/pagine.ts)
 * with their own names, then this page. The Home (a tent) comes before, in the component.
 */
import { PAGINE } from '@/router/pagine'

import type { Gruppo, Voce } from './menu'

export interface Briciola {
  nome: string
  /** Where it leads; none for the group and for this page. */
  percorso: string | null
}

/** One page of the chain, from the top down to this one. */
export interface Anello {
  pagina: string
  percorso: string
  nome: string
}

export function briciole(
  catena: Anello[],
  gruppi: Gruppo[],
  profilo: Voce[],
  capo: boolean,
  percorsoDi: (voce: Voce) => string | null,
): Briciola[] {
  if (!catena.length) return []
  const corrente = catena[catena.length - 1]!
  const daMenu = gruppi.flatMap((g) => g.voci)
  // A page the menu offers is reached from the menu: nothing between the group and it
  // (a ragazzo's own sentiero is "Il mio Sentiero", not "Giulia Rossi › Progressione").
  const voce = daMenu.find((v) => percorsoDi(v) === corrente.percorso)
  // A sub-entry (a unit's Passaggi) keeps the entry it hangs from (the unit).
  const madre = voce?.sottovoce
    ? daMenu
        .slice(0, daMenu.indexOf(voce))
        .reverse()
        .find((v) => !v.sottovoce)
    : undefined
  const pagine = voce
    ? [
        ...(madre ? [{ pagina: '', percorso: percorsoDi(madre) ?? '', nome: madre.nome }] : []),
        { ...corrente, nome: voce.nome },
      ]
    : catena
  const visibili = new Set([...daMenu, ...profilo].map(percorsoDi))
  // A page above this one that the menu does not offer (a parent on a child's page
  // never sees "Persone") is left out, and so is one only the capi open.
  const mostrate = pagine.filter((a, i) => {
    if (i === pagine.length - 1 || (madre && i === 0)) return true
    const pagina = PAGINE[a.pagina]
    if (pagina?.soloCapi && !capo) return false
    return visibili.has(a.percorso) || pagina?.sopra !== undefined
  })
  const gruppo = gruppi.find(
    (g) =>
      !(g.voci.length === 1 && g.voci[0]!.nome === g.titolo) &&
      g.voci.some((v) => mostrate.some((b) => b.percorso === percorsoDi(v))),
  )
  return [
    ...(gruppo && gruppo.titolo !== mostrate[mostrate.length - 1]!.nome
      ? [{ nome: gruppo.titolo, percorso: null }]
      : []),
    ...mostrate.map((b, i) => ({
      nome: b.nome,
      percorso: i === mostrate.length - 1 ? null : b.percorso,
    })),
  ]
}
