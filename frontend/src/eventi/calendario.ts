/**
 * The calendar page (DEC-286): the month grid, the events of a day, and the choices
 * remembered in the browser (month or list, a capo's view: no personal data, like the
 * Home's open group).
 */
import type { EventoCalendario } from '@/api/qdc'

export type ModoCalendario = 'mese' | 'elenco'

const CHIAVE_MODO = 'qdc-calendario-modo'
const CHIAVE_VISTA = 'qdc-calendario-vista'

/** A local day as "yyyy-mm-dd" (not toISOString: that is UTC, the day may change). */
export function chiaveGiorno(giorno: Date): string {
  const mm = String(giorno.getMonth() + 1).padStart(2, '0')
  const gg = String(giorno.getDate()).padStart(2, '0')
  return `${giorno.getFullYear()}-${mm}-${gg}`
}

/** The weeks shown for a month, Monday first, with the days of the months around. */
export function settimaneDelMese(anno: number, mese: number): Date[][] {
  const primo = new Date(anno, mese, 1)
  // getDay(): 0 = Sunday. Days to go back to reach Monday.
  const indietro = (primo.getDay() + 6) % 7
  const inizio = new Date(anno, mese, 1 - indietro)
  const settimane: Date[][] = []
  const giorno = new Date(inizio)
  do {
    const settimana: Date[] = []
    for (let i = 0; i < 7; i++) {
      settimana.push(new Date(giorno))
      giorno.setDate(giorno.getDate() + 1)
    }
    settimane.push(settimana)
  } while (giorno.getMonth() === mese)
  return settimane
}

/** The events on a local day: those starting, ending or going on that day. */
export function eventiDelGiorno(eventi: EventoCalendario[], giorno: Date): EventoCalendario[] {
  const chiave = chiaveGiorno(giorno)
  return eventi.filter(
    (e) => chiaveGiorno(new Date(e.inizio)) <= chiave && chiaveGiorno(new Date(e.fine)) >= chiave,
  )
}

export function leggiModo(): ModoCalendario {
  try {
    return localStorage.getItem(CHIAVE_MODO) === 'elenco' ? 'elenco' : 'mese'
  } catch {
    return 'mese'
  }
}

export function leggiVista(): string {
  try {
    return localStorage.getItem(CHIAVE_VISTA) ?? ''
  } catch {
    return ''
  }
}

function salva(chiave: string, valore: string): void {
  try {
    localStorage.setItem(chiave, valore)
  } catch {
    // Private browsing: the default next time.
  }
}

export const salvaModo = (modo: ModoCalendario) => salva(CHIAVE_MODO, modo)
export const salvaVista = (vista: string) => salva(CHIAVE_VISTA, vista)
