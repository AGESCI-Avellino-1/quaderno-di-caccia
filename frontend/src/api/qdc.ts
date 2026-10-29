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

// --- Accounts and invitations (DEC-21, DEC-24, DEC-25) ---------------------------------

export interface Invito {
  id: number
  email: string
  creato_il: string
  scadenza: string
  usato_il: string | null
  valido: boolean
}

export interface SchedaAccount extends PersonaBreve {
  ha_account: boolean
  puo_invitare: boolean
  richiede_consenso_genitore: boolean
  /** The person's own address from the registry, proposed in the form. */
  email: string | null
  inviti: Invito[]
}

export interface StatoAccount {
  persona: SchedaAccount
  genitori: SchedaAccount[]
  metodi_consenso: { valore: string; etichetta: string }[]
}

export interface NuovoInvito {
  persona_id: number
  email: string
  consenso_genitore_da_id?: number
  consenso_genitore_metodo?: string
}

export interface Unita {
  id: number
  nome: string
  tipo: string
  branca: string
  composizione: string
  ambiente: string
  attiva: boolean
  collegata_a: number | null
  nota_collegamento: string
}

// --- Units, staff and roles (DEC-10, DEC-11, DEC-14, DEC-18) --------------------------

export interface Scelta {
  valore: string
  etichetta: string
}

/** Same values as the backend TextChoices (organizzazione/models.py). */
export const TIPI_UNITA: Scelta[] = [
  { valore: 'BRANCO', etichetta: 'Branco' },
  { valore: 'CERCHIO', etichetta: 'Cerchio' },
  { valore: 'BRANCO_CERCHIO', etichetta: 'Branco/Cerchio' },
  { valore: 'REPARTO', etichetta: 'Reparto' },
  { valore: 'NOVIZIATO', etichetta: 'Noviziato' },
  { valore: 'CLAN_FUOCO', etichetta: 'Clan/Fuoco' },
  { valore: 'COMUNITA_CAPI', etichetta: 'Comunità Capi' },
]
export const COMPOSIZIONI: Scelta[] = [
  { valore: 'M', etichetta: 'Maschile' },
  { valore: 'F', etichetta: 'Femminile' },
  { valore: 'X', etichetta: 'Mista' },
]
export const AMBIENTI: Scelta[] = [
  { valore: 'NESSUNO', etichetta: 'Nessuno' },
  { valore: 'GIUNGLA', etichetta: 'Giungla' },
  { valore: 'BOSCO', etichetta: 'Bosco' },
]

export interface UnitaIn {
  nome: string
  tipo: string
  composizione: string
  ambiente: string
  collegata_a: number | null
  nota_collegamento: string
  attiva: boolean
}

export interface Incarico {
  id: number
  ruolo: string
  ruolo_nome: string
  persona: PersonaBreve
  data_inizio: string
  data_fine: string | null
}

/** An active patrol membership (DEC-65). */
export interface Membro {
  id: number
  persona: PersonaBreve
  data_inizio: string
}

export interface Squadriglia {
  id: number
  nome: string
  sesso: 'M' | 'F'
  attiva: boolean
  membri: Membro[]
  incarichi: Incarico[]
  /** Roles the user may assign (and close) here: the backend policy decides. */
  nomina: Scelta[]
}

export interface UnitaDettaglio {
  unita: Unita
  incarichi: Incarico[]
  squadriglie: Squadriglia[]
  puo_modificare: boolean
  /** Ragazzi of a reparto who are in no patrol today. */
  senza_squadriglia: PersonaBreve[]
  /** Single-sex check: members without a sex, or of the other sex without an exception. */
  avvisi: string[]
  puo_gestire_squadriglie: boolean
  nomina: Scelta[]
}

/** Exception to single-sex patrols decided by the Co.Ca. Special-category data: capi
 * only, never cached on the device. */
export interface Deroga {
  id: number
  reparto: string
  sesso_squadriglia: 'M' | 'F'
  squadriglie_ammesse: string
  data_decisione: string
  motivazione: string
  registrata_da: string | null
  revocata_il: string | null
  valida: boolean
}

export interface DerogheSquadriglia {
  deroghe: Deroga[]
  puo_gestire: boolean
  /** Reparti the person belongs to (valore = unit id). */
  reparti: Scelta[]
}

export interface NuovaDeroga {
  reparto_id: number
  sesso_squadriglia: string
  data_decisione: string
  motivazione: string
}

export interface IncarichiGruppo {
  incarichi: Incarico[]
  nomina: Scelta[]
}

/** Where a role is held: the group (nothing), a unit or a patrol. */
export type DoveIncarico = { unita_id: number } | { squadriglia_id: number } | object

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
    /** Corrections BuonaStrada now has: closed (DEC-31). Missing in older imports. */
    correzioni_recepite?: string[]
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

// --- Corrections to BuonaStrada data (DEC-31) ------------------------------------------

export type StatoCorrezione = 'IN_ATTESA' | 'INOLTRATA' | 'RECEPITA' | 'SCARTATA'

export interface Correzione {
  id: number
  campo: string
  etichetta: string
  /** Values as text: dates YYYY-MM-DD, yes/no "True"/"False", "" when empty. */
  valore_precedente: string
  valore_corretto: string
  stato: StatoCorrezione
  stato_nome: string
  creata_il: string
  richiesta_da: string | null
  inoltrata_il: string | null
  chiusa_il: string | null
  motivo_scarto: string
}

export interface CorrezioneElenco extends Correzione {
  persona: { id: number; nome: string; cognome: string; codice_socio: string | null }
}

export interface CampoCorreggibile {
  campo: string
  etichetta: string
  tipo: 'testo' | 'data' | 'numero' | 'si_no' | 'scelta'
  valore: string
  scelte: Scelta[]
  /** The open correction, if any: the value is "in attesa di BuonaStrada". */
  correzione: Correzione | null
}

/** A correction value for people: "Sì"/"No", dd/mm/yyyy, the choice label, "—". */
export function valoreLeggibile(testo: string, scelte: Scelta[] = []): string {
  if (testo === '') return '—'
  if (testo === 'True') return 'Sì'
  if (testo === 'False') return 'No'
  const data = /^(\d{4})-(\d{2})-(\d{2})$/.exec(testo)
  if (data) return `${data[3]}/${data[2]}/${data[1]}`
  return scelte.find((s) => s.valore === testo)?.etichetta ?? testo
}

export interface SchedaCorrezioni {
  campi: CampoCorreggibile[]
  chiuse: Correzione[]
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
  unita: (tutte = false) => richiesta<Unita[]>(`/api/v1/unita${tutte ? '?tutte=true' : ''}`),
  dettaglioUnita: (id: number) => richiesta<UnitaDettaglio>(`/api/v1/unita/${id}`),
  creaUnita: (dati: UnitaIn) => richiesta<Unita>('/api/v1/unita', { metodo: 'POST', corpo: dati }),
  modificaUnita: (id: number, dati: UnitaIn) =>
    richiesta<Unita>(`/api/v1/unita/${id}`, { metodo: 'PUT', corpo: dati }),
  creaSquadriglia: (unita: number, dati: { nome: string; sesso: string }) =>
    richiesta<Squadriglia>(`/api/v1/unita/${unita}/squadriglie`, { metodo: 'POST', corpo: dati }),
  modificaSquadriglia: (id: number, dati: { nome: string; sesso: string; attiva: boolean }) =>
    richiesta<Squadriglia>(`/api/v1/squadriglie/${id}`, { metodo: 'PUT', corpo: dati }),
  incarichiDiGruppo: () => richiesta<IncarichiGruppo>('/api/v1/gruppo/incarichi'),
  capi: () => richiesta<PersonaBreve[]>('/api/v1/capi'),
  aggiungiMembro: (squadriglia: number, persona: number) =>
    richiesta<Membro>(`/api/v1/squadriglie/${squadriglia}/membri`, {
      metodo: 'POST',
      corpo: { persona_id: persona },
    }),
  togliMembro: (id: number) =>
    richiesta<{ id: number; rimosso: boolean }>(`/api/v1/membri-squadriglia/${id}/termina`, {
      metodo: 'POST',
    }),
  deroghe: (persona: number) =>
    richiesta<DerogheSquadriglia>(`/api/v1/persone/${persona}/deroghe-squadriglia`),
  registraDeroga: (persona: number, dati: NuovaDeroga) =>
    richiesta<Deroga>(`/api/v1/persone/${persona}/deroghe-squadriglia`, {
      metodo: 'POST',
      corpo: dati,
    }),
  revocaDeroga: (id: number) =>
    richiesta<Deroga>(`/api/v1/deroghe-squadriglia/${id}/revoca`, { metodo: 'POST' }),
  correzioniPersona: (persona: number) =>
    richiesta<SchedaCorrezioni>(`/api/v1/persone/${persona}/correzioni`),
  correggi: (persona: number, dati: { campo: string; valore: string }) =>
    richiesta<SchedaCorrezioni>(`/api/v1/persone/${persona}/correzioni`, {
      metodo: 'POST',
      corpo: dati,
    }),
  correzioni: (aperte = true) =>
    richiesta<CorrezioneElenco[]>(`/api/v1/correzioni${aperte ? '' : '?aperte=false'}`),
  inoltraCorrezione: (id: number) =>
    richiesta<CorrezioneElenco>(`/api/v1/correzioni/${id}/inoltra`, { metodo: 'POST' }),
  scartaCorrezione: (id: number, motivo: string) =>
    richiesta<CorrezioneElenco>(`/api/v1/correzioni/${id}/scarta`, {
      metodo: 'POST',
      corpo: { motivo },
    }),
  nomina: (dati: { persona_id: number; ruolo: string } & DoveIncarico) =>
    richiesta<Incarico>('/api/v1/incarichi', { metodo: 'POST', corpo: dati }),
  terminaIncarico: (id: number) =>
    richiesta<{ id: number; rimosso: boolean }>(`/api/v1/incarichi/${id}/termina`, {
      metodo: 'POST',
      corpo: {},
    }),
  persone: (unita?: number) =>
    richiesta<PersonaElenco[]>(`/api/v1/persone${unita ? `?unita=${unita}` : ''}`),
  persona: (id: number) => richiesta<PersonaDettaglio>(`/api/v1/persone/${id}`),
  statoAccount: (persona: number) => richiesta<StatoAccount>(`/api/v1/persone/${persona}/account`),
  invita: (dati: NuovoInvito) =>
    richiesta<{ id: number }>('/api/v1/inviti', { metodo: 'POST', corpo: dati }),
  annullaInvito: (id: number) =>
    richiesta<Invito>(`/api/v1/inviti/${id}/annulla`, { metodo: 'POST' }),
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
