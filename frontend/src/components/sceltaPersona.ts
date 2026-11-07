/** One choice of SceltaPersona.vue (DEC-395): the name as shown, the unit next to it. */
export interface Opzione {
  id: number
  nome: string
  dettaglio?: string
}

const semplice = (testo: string) => testo.normalize('NFD').replace(/\p{M}/gu, '').toLowerCase()

/** Every word written is in the name, in any order: «ros giu» finds Giulia Rossi. */
export function coincide(o: Opzione, testo: string): boolean {
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
