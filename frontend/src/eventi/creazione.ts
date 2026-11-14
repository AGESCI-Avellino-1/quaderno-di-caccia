/**
 * Who may open the forms of a new event or new meetings, from the profile the server gives:
 * the capi, the CSQ, and for meetings who has the CSQ's delegation (DEC-139, DEC-267). The
 * server checks again on saving. Shared by the Eventi and Riunioni pages and the calendar's
 * «+» (DEC-412).
 */
import type { Profilo } from '@/api/qdc'

export function puoCreareEventi(p: Profilo | null): boolean {
  return !!p && (p.capo || p.squadriglie_guidate.length > 0)
}

export function puoCreareRiunioni(p: Profilo | null): boolean {
  return puoCreareEventi(p) || (!!p && p.squadriglie_delegate.length > 0)
}

/** The day passed by the calendar in `?giorno=`: only a real date. */
export function giornoDaQuery(valore: unknown): string | null {
  if (typeof valore !== 'string' || !/^\d{4}-\d{2}-\d{2}$/.test(valore)) return null
  return Number.isNaN(new Date(`${valore}T12:00:00`).getTime()) ? null : valore
}
