/** One choice of SceltaDaElenco.vue (DEC-395, DEC-397): the name as shown, a detail next to it
 * (a person's unit). The id is a person's, or a catalog's code. */
export interface Opzione<K extends number | string = number> {
  id: K
  nome: string
  dettaglio?: string
}

const semplice = (testo: string) => testo.normalize('NFD').replace(/\p{M}/gu, '').toLowerCase()

/** Every word written is in the name, in any order: «ros giu» finds Giulia Rossi. */
export function coincide(o: Opzione<number | string>, testo: string): boolean {
  const nome = semplice(o.nome)
  return semplice(testo)
    .split(/\s+/)
    .filter(Boolean)
    .every((parola) => nome.includes(parola))
}

/** From the people of an API: «Cognome Nome» and the unit. */
export function opzioniDa(
  persone: { id: number; nome: string; cognome: string; unita?: string }[],
): Opzione[] {
  return persone.map((p) => ({ id: p.id, nome: `${p.cognome} ${p.nome}`, dettaglio: p.unita }))
}
