import { watch } from 'vue'

/**
 * The end of a meeting or of an event follows its start, keeping how long it lasts (DEC-429):
 * a `min` is not enough, some pickers (iPhone's) open on the value they have. A new end nobody
 * wrote yet is proposed; what the user writes as the end sets the new duration.
 */
interface Regole {
  inizio: () => string | undefined
  fine: () => string | undefined
  imposta: (fine: string) => void
  /** From the field's value to a number, and back. */
  leggi: (valore: string) => number
  scrivi: (numero: number) => string
  /** The duration of an end not written yet, or not after the start. */
  durata: number
  /** The shortest duration that makes sense: a day's event ends on the same day. */
  minima?: number
  /** Whether an empty end is proposed (an hour not known yet stays empty). */
  proponi?: boolean
  /** Whether start and end may be compared (hours of the same day). */
  confrontabili?: () => boolean
}

export function useFineCheSegue(r: Regole) {
  let durata: number | undefined
  let impostata: string | undefined
  watch(
    [r.inizio, r.fine],
    ([inizio, fine], [inizioPrima, finePrima] = [undefined, undefined]) => {
      if (inizioPrima === undefined) durata = impostata = undefined // the form just opened
      if (!inizio || (r.confrontabili && !r.confrontabili())) return
      if (fine && fine === impostata && fine !== finePrima) return // what we wrote
      const da = r.leggi(inizio)
      if (Number.isNaN(da)) return
      const cambiatoInizio = inizio !== inizioPrima
      const soloInizio = cambiatoInizio && fine === finePrima
      if (fine && (!soloInizio || (durata === undefined && !inizioPrima))) {
        const lunga = r.leggi(fine) - da
        durata = lunga >= (r.minima ?? 1) ? lunga : undefined
        // Written before the start, and too early for it.
        if (!soloInizio || durata !== undefined) return
      }
      if (!cambiatoInizio || (!fine && r.proponi === false)) return
      impostata = r.scrivi(da + (durata ?? r.durata))
      if (impostata !== fine) r.imposta(impostata)
    },
    { immediate: true },
  )
}

const due = (n: number) => String(n).padStart(2, '0')
const MINUTI_DUE_ORE = 120

/** Fields `type="time"` of one day: never past 23:59. */
export const ORE = {
  leggi: (valore: string) => {
    const [ore, minuti] = valore.split(':').map(Number)
    return ore! * 60 + minuti!
  },
  scrivi: (minuti: number) => {
    const m = Math.min(minuti, 23 * 60 + 59)
    return `${due(Math.floor(m / 60))}:${due(m % 60)}`
  },
  durata: MINUTI_DUE_ORE,
}

const GIORNO = 24 * 3600 * 1000

// As UTC, so a local hour stays the same across the change to daylight saving time.
/** Fields `type="datetime-local"`. */
export const MOMENTI = {
  leggi: (valore: string) => Date.parse(`${valore.slice(0, 16)}Z`),
  scrivi: (ms: number) => new Date(ms).toISOString().slice(0, 16),
  durata: MINUTI_DUE_ORE * 60 * 1000,
}

/** Fields `type="date"`. */
export const GIORNI = {
  leggi: (valore: string) => Date.parse(`${valore}T00:00Z`) / GIORNO,
  scrivi: (giorni: number) => new Date(giorni * GIORNO).toISOString().slice(0, 10),
  durata: 0,
  minima: 0,
}
