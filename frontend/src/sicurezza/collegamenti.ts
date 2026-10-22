/**
 * Connects the vault to the server answers (DEC-97):
 * - X-QdC-Offline-Fino-Al renews how long this device may stay offline;
 * - 401 with codice "dispositivo_revocato" wipes the device at once.
 */
import { osservaRisposte } from '@/api/http'

import { aggiornaScadenza, cancella } from './cassaforte'

export const INTESTAZIONE_SCADENZA = 'X-QdC-Offline-Fino-Al'
export const CODICE_REVOCATO = 'dispositivo_revocato'

export function collegaCassaforte(): () => void {
  return osservaRisposte(async (risposta, dati) => {
    const scadenza = risposta.headers.get(INTESTAZIONE_SCADENZA)
    if (scadenza) await aggiornaScadenza(scadenza)
    const codice = dati as { codice?: string; detail?: string } | null
    if (
      (risposta.status === 401 || risposta.status === 403) &&
      (codice?.codice === CODICE_REVOCATO || codice?.detail === CODICE_REVOCATO)
    ) {
      await cancella('revocato')
    }
  })
}
