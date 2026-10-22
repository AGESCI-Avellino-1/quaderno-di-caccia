/** Typed client for the QdC API (/api/v1). Mirrors the ninja schemas in the backend. */
import { richiesta } from './http'

export type Branca = 'generico' | 'capi' | 'lc' | 'eg' | 'rs'

/** Theme name (theme/_branche.scss) for a backend Branca value (LC, EG, RS, COCA). */
export function temaDellaBranca(branca: string): Branca {
  const tema = branca.toLowerCase()
  if (tema === 'coca') return 'capi'
  return (['lc', 'eg', 'rs'] as const).find((b) => b === tema) ?? 'generico'
}

export interface PersonaBreve {
  id: number
  nome: string
  cognome: string
}

export interface Profilo {
  email: string
  persona: PersonaBreve | null
  branca: Branca
  capo: boolean
  capogruppo: boolean
  tesoriere: boolean
  amministratore_tecnico: boolean
  squadriglie_guidate: number[]
  tutelati: PersonaBreve[]
}

export interface PersonaElenco extends PersonaBreve {
  codice_socio: string | null
}

export interface PersonaDettaglio extends PersonaBreve {
  livello_accesso: 'squadriglia' | 'tutore' | 'proprio' | 'completo'
  data_nascita: string | null
  codice_socio: string | null
  email: string | null
  cellulare: string | null
  indirizzo: string | null
  comune: string | null
  consenso_foto: boolean | null
  unita: string[]
}

export interface Unita {
  id: number
  nome: string
  tipo: string
  branca: string
  composizione: string
  ambiente: string
  attiva: boolean
}

export interface EsitoImportazione {
  id: number
  stato: 'ANTEPRIMA' | 'APPLICATA' | 'ANNULLATA'
  riepilogo: {
    persone_create: string[]
    persone_aggiornate: string[]
    genitori_creati: string[]
    unita_create: string[]
    appartenenze_aperte: string[]
    appartenenze_chiuse: string[]
    differenze: {
      persona: string
      campo: string
      valore_app: string
      valore_buonastrada: string
      motivo: string
    }[]
    avvisi: { gravita: string; messaggio: string; riga: number | null }[]
  }
}

// --- Health essentials (DEC-48 core, DEC-55) -------------------------------------------

export type TipoAllergia = 'ALLERGIA' | 'INTOLLERANZA'
export type Gravita = 'LIEVE' | 'MODERATA' | 'GRAVE'

export interface Allergia {
  tipo: TipoAllergia
  sostanza: string
  gravita: Gravita
  reazione: string
  cosa_fare: string
}

export interface Farmaco {
  nome: string
  posologia: string
  orari: string
  autonomo: boolean
  note: string
}

export interface SanitarieIn {
  nessuna_allergia: boolean
  nessun_farmaco: boolean
  allergie: Allergia[]
  farmaci: Farmaco[]
}

export interface Sanitarie extends SanitarieIn {
  compilate: boolean
  inserite_da: string | null
  aggiornate_il: string | null
  puo_modificare: boolean
}

export interface Contatto {
  nome: string
  relazione: string
  cellulare: string
}

export interface SchedaCampo {
  id: number
  nome: string
  cognome: string
  data_nascita: string | null
  contatti: Contatto[]
  sanitarie: Sanitarie
}

export interface Campo {
  unita: string
  scaricato_il: string
  persone: SchedaCampo[]
}

export interface AccessoSensibile {
  quando: string
  chi: string | null
  azione: string
  categoria: string
  dispositivo: string | null
}

// --- Devices (DEC-23, DEC-97) ---------------------------------------------------------

export interface Dispositivo {
  id: string
  nome: string
  utente: string
  ultimo_contatto: string
  revocato_il: string | null
  corrente: boolean
  offline_fino_al: string
}

export const percorsoSanitarie = (persona: number) => `/api/v1/persone/${persona}/sanitarie`

export const api = {
  profilo: () => richiesta<Profilo>('/api/v1/io'),
  unita: () => richiesta<Unita[]>('/api/v1/unita'),
  persone: (unita?: number) =>
    richiesta<PersonaElenco[]>(`/api/v1/persone${unita ? `?unita=${unita}` : ''}`),
  persona: (id: number) => richiesta<PersonaDettaglio>(`/api/v1/persone/${id}`),
  accettaInvito: (token: string) =>
    richiesta<{ email: string; persona: string }>('/api/v1/inviti/accetta', {
      metodo: 'POST',
      corpo: { token },
    }),
  caricaExport: (file: File) => {
    const dati = new FormData()
    dati.append('file', file)
    return richiesta<EsitoImportazione>('/api/v1/importazioni', { metodo: 'POST', corpo: dati })
  },
  sanitarie: (persona: number) => richiesta<Sanitarie>(percorsoSanitarie(persona)),
  campo: (unita: number) => richiesta<Campo>(`/api/v1/campo/${unita}`),
  accessiSensibili: (persona: number) =>
    richiesta<AccessoSensibile[]>(`/api/v1/persone/${persona}/accessi-sensibili`),
  dispositivi: (tutti = false) =>
    richiesta<Dispositivo[]>(`/api/v1/dispositivi${tutti ? '?tutti=true' : ''}`),
  registraDispositivo: (dati: { nome: string; id: string | null }) =>
    richiesta<Dispositivo>('/api/v1/dispositivi', { metodo: 'POST', corpo: dati }),
  statoDispositivo: (id: string) =>
    richiesta<{ revocato: boolean }>(`/api/v1/dispositivi/${id}/stato`),
  revocaDispositivo: (id: string) =>
    richiesta<Dispositivo>(`/api/v1/dispositivi/${id}/revoca`, { metodo: 'POST' }),
  applicaImportazione: (id: number) =>
    richiesta<EsitoImportazione>(`/api/v1/importazioni/${id}/applica`, { metodo: 'POST' }),
}
