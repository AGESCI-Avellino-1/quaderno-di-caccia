/**
 * When an event happens, in words. An event on BuonaCaccia may know only the day, of its
 * start, of its end or of both (DEC-391).
 */
interface ConOrario {
  inizio: string
  fine: string
  senza_ora_inizio?: boolean
  senza_ora_fine?: boolean
}

const giorno = (d: Date) =>
  d.toLocaleDateString('it-IT', { weekday: 'short', day: 'numeric', month: 'short' })
const ora = (d: Date) => d.toLocaleTimeString('it-IT', { hour: '2-digit', minute: '2-digit' })

/** With `oreSuPiuGiorni`, the hours of an event of several days too. */
export function quandoEvento(e: ConOrario, oreSuPiuGiorni = false): string {
  const inizio = new Date(e.inizio)
  const fine = new Date(e.fine)
  if (inizio.toDateString() === fine.toDateString()) {
    if (e.senza_ora_inizio && e.senza_ora_fine) return giorno(inizio)
    if (e.senza_ora_fine) return `${giorno(inizio)}, dalle ${ora(inizio)}`
    if (e.senza_ora_inizio) return `${giorno(inizio)}, fino alle ${ora(fine)}`
    return `${giorno(inizio)}, ${ora(inizio)}–${ora(fine)}`
  }
  if (!oreSuPiuGiorni) return `dal ${giorno(inizio)} al ${giorno(fine)}`
  const dal = e.senza_ora_inizio ? giorno(inizio) : `${giorno(inizio)} ${ora(inizio)}`
  const al = e.senza_ora_fine ? giorno(fine) : `${giorno(fine)} ${ora(fine)}`
  return `${dal} – ${al}`
}

/** One moment on the page of the event. */
export function dataEOra(iso: string, senzaOra?: boolean): string {
  return new Date(iso).toLocaleString('it-IT', {
    weekday: 'short',
    day: 'numeric',
    month: 'long',
    year: 'numeric',
    ...(senzaOra ? {} : { hour: '2-digit', minute: '2-digit' }),
  })
}
