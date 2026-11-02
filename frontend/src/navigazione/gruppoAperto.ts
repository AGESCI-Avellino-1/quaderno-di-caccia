/**
 * Which group of the Home was open last (DEC-285): only its key, kept in the browser like
 * the closing of the banners (no personal data). At most one is open at a time.
 */
import type { Gruppo } from '@/navigazione/menu'

export const CHIAVE_GRUPPO_APERTO = 'qdc-home-gruppo-aperto'

/** Groups always shown open on the Home: they are not collapsible. */
export const SEMPRE_APERTI = new Set(['bacheca'])

export function leggiGruppoAperto(): string | null {
  try {
    return localStorage.getItem(CHIAVE_GRUPPO_APERTO)
  } catch {
    return null
  }
}

export function salvaGruppoAperto(chiave: string | null): void {
  try {
    if (chiave) localStorage.setItem(CHIAVE_GRUPPO_APERTO, chiave)
    else localStorage.removeItem(CHIAVE_GRUPPO_APERTO)
  } catch {
    // Private browsing: next time all groups start closed.
  }
}

/** The total of the counters of a group's entries, shown on its title when closed. */
export function totaleContatori(gruppo: Gruppo): number {
  return gruppo.voci.reduce((totale, v) => totale + (v.contatore ?? 0), 0)
}
