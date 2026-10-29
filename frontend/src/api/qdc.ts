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
  /** Patrols the user is a member of. */
  squadriglie: number[]
  /** Joining from the app: own requests, and waiting requests this user decides. */
  mie_iscrizioni: number
  iscrizioni_da_decidere: number
  /** Accepted registrations whose signed forms wait for this user's check. */
  iscrizioni_da_verificare?: number
  /** Capigruppo: completed registrations to enter in BuonaStrada. */
  iscrizioni_da_inserire?: number
  /** A capo not yet in BuonaStrada: no sensitive data of other members. */
  capo_in_attesa: boolean
  tutelati: PersonaBreve[]
  /** Fees: the group sets them; units whose payment situation the user may see. */
  gestisce_quote: boolean
  unita_quote: number[]
}

export interface PersonaElenco extends PersonaBreve {
  codice_socio: string | null
}

export interface PersonaDettaglio extends PersonaBreve {
  livello_accesso: 'squadriglia' | 'tutore' | 'proprio' | 'completo'
  data_nascita: string | null
  codice_socio: string | null
  /** Joined from the app, not yet in BuonaStrada. */
  codice_provvisorio?: boolean
  /** Joined from the app and the deadline to complete passed. */
  iscrizione_sospesa?: boolean
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
  /** BuonaStrada code (O1, G1…): unique, unlike the name chosen by the group. */
  codice: string
  /** Created by the import: the group has still to name it. */
  senza_nome?: boolean
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

/** Type, name, code: "Clan/Fuoco Hirpinia (T1)" (DEC-128). The name is
 * the group's and may repeat or be missing; the BuonaStrada code does not. */
export function nomeUnita(u: { nome: string; codice?: string; tipo: string }): string {
  const tipo = TIPI_UNITA.find((t) => t.valore === u.tipo)?.etichetta ?? ''
  const testo = `${tipo} ${u.nome}`.trim()
  return u.codice ? `${testo} (${u.codice})` : testo
}

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

/** Which side wins when the app and BuonaStrada disagree. */
export type Lato = 'APP' | 'BUONASTRADA'

export interface EsitoImportazione {
  id: number
  stato: 'ANTEPRIMA' | 'APPLICATA' | 'ANNULLATA'
  /** When the BuonaStrada data were updated, as stated at upload. */
  dati_aggiornati_al: string | null
  riepilogo: {
    persone_create: string[]
    persone_aggiornate: string[]
    genitori_creati: string[]
    unita_create: string[]
    appartenenze_aperte: string[]
    appartenenze_chiuse: string[]
    /** Members who joined from the app, now with their real code. Missing in older imports. */
    iscrizioni_recepite?: string[]
    /** Corrections BuonaStrada now has: closed (DEC-31). Missing in older imports. */
    correzioni_recepite?: string[]
    differenze: {
      persona: string
      campo: string
      valore_app: string
      valore_buonastrada: string
      motivo: string
      /** Missing in older imports, made before the choice existed. */
      chiave?: string
      data_app?: string | null
      proposta?: Lato
      scelta?: Lato
    }[]
    avvisi: { gravita: string; messaggio: string; riga: number | null }[]
  }
}

// --- Phones within the patrol (DEC-13) ------------------------------------------------

export interface TelefonoMembro extends PersonaBreve {
  incarico: string | null
  telefono: string | null
  /** First name of the parent whose phone it is, when the child has none. */
  del_genitore: string | null
}

export interface MiaSquadriglia {
  id: number
  nome: string
  reparto: string
  sono_capo: boolean
  membri: TelefonoMembro[]
  /** Parents' phones: for the capo squadriglia only. */
  genitori: { figlio_id: number; nome: string; cognome: string; telefono: string }[]
}

export interface ImpostazioneTelefono {
  in_squadriglia: boolean
  /** The child's own BuonaStrada mobile, "" if none: when present it is the one shown. */
  proprio: string
  /** Parent or guardian chosen for this child. */
  genitore_id: number | null
  /** Parent or guardian chosen for all the children without a phone. */
  famiglia_id: number | null
  nascosto: boolean
  genitori: Scelta[]
}

// --- Joining from the app (registration codes) ----------------------------------------

export interface CodiceIscrizione {
  id: number
  codice: string
  /** Link to share; the QR code encodes it. */
  link: string
  tipo: 'UNITA' | 'PERSONALE'
  tipo_nome: string
  scadenza: string
  usi: number
  valido: boolean
  creato_il: string
}

export interface InfoCodice {
  codice: string
  unita: string
  per_capi: boolean
}

export interface DatiIscrizione {
  nome: string
  cognome: string
  data_nascita: string
  codice_fiscale: string
  email: string
  genitore_nome: string
  genitore_cognome: string
  genitore_codice_fiscale: string
}

export type StatoIscrizione =
  'IN_ATTESA' | 'APPROVATA' | 'SOSPESA' | 'COMPLETATA' | 'INSERITA' | 'RECEPITA' | 'RIFIUTATA'

export interface RichiestaIscrizione {
  id: number
  unita: string
  unita_id: number
  stato: StatoIscrizione
  stato_nome: string
  nome: string
  cognome: string
  data_nascita: string
  codice_fiscale: string
  email: string
  per_minore: boolean
  genitore: string | null
  richiesta_da: string | null
  creata_il: string
  scadenza_completamento: string | null
  motivo_rifiuto: string
  persona_id: number | null
  /** What the family still has to complete, in words. */
  mancanti: string[]
}

export interface Completamento {
  sesso: string
  luogo_nascita: string
  indirizzo: string
  civico: string
  comune: string
  provincia: string
  cap: string
  /** The member's own: required for adults and minors in Clan/Fuoco or Noviziato. */
  cellulare: string
  email: string
  contatti_obbligatori?: boolean
  /** For a minor, the parent's mobile; null for an adult member. */
  cellulare_genitore: string | null
  /** For a minor: one parent with exclusive custody, or both (null: not said yet). */
  genitore_unico: boolean | null
  altro_genitore: AltroGenitore | null
}

export interface AltroGenitore {
  nome: string
  cognome: string
  codice_fiscale: string
  cellulare: string
  email: string
}

export const qrCodice = (id: number) => `/api/v1/codici-iscrizione/${id}/qr.svg`

export interface ModuloVuoto {
  id: number
  titolo: string
  attivo: boolean
}

export interface ModuliFirmati {
  allegati: { id: number; nome_file: string; tipo_contenuto: string; caricato_il: string }[]
  verificati_il: string | null
  /** Who approves checks the forms and reports the consents. */
  puo_verificare: boolean
}

export interface Consensi {
  consenso_iscrizione: boolean
  consenso_foto: boolean
  consenso_commerciale: boolean
  consenso_riviste: boolean
}

export interface DaInserire {
  id: number
  colonne: string[]
  valori: string[]
  stato: 'COMPLETATA' | 'INSERITA'
}

export const esportazioneBuonaStrada = (formato: 'xlsx' | 'pdf') =>
  `/api/v1/iscrizioni-buonastrada.${formato}`

export const fileModulo = (id: number) => `/api/v1/modulistica/${id}/file`
export const fileModuloFirmato = (id: number) => `/api/v1/moduli-firmati/${id}/file`

function conFile(campi: Record<string, string>, file: File): FormData {
  const dati = new FormData()
  for (const [nome, valore] of Object.entries(campi)) dati.append(nome, valore)
  dati.append('file', file)
  return dati
}

// --- What the parents of an adult see (DEC-26) ----------------------------------------

export interface SceltaVisibilita {
  contatti: boolean
  sanitarie: boolean
  scheda: boolean
  quote: boolean
}

export interface VisibilitaGenitori extends SceltaVisibilita {
  decisa_il: string | null
  /** Names of the parents concerned. */
  genitori: string[]
}

// --- Requests from data subjects (DEC-102) --------------------------------------------

export const TIPI_RICHIESTA: Scelta[] = [
  { valore: 'ACCESSO', etichetta: 'Accesso ai dati' },
  { valore: 'ESPORTAZIONE', etichetta: 'Copia dei dati (portabilità)' },
  { valore: 'RETTIFICA', etichetta: 'Rettifica' },
  { valore: 'CANCELLAZIONE', etichetta: 'Cancellazione' },
  { valore: 'ALTRO', etichetta: 'Altro (limitazione, opposizione…)' },
]

export interface RichiestaDiritti {
  id: number
  persona: PersonaBreve
  tipo: string
  tipo_nome: string
  richiedente: string
  ricevuta_il: string
  /** Answer due by (one month). */
  scadenza: string
  note: string
  inoltrata_nazionale_il: string | null
  evasa_il: string | null
  registrata_da: string | null
}

export interface NuovaRichiesta {
  persona_id: number
  tipo: string
  richiedente: string
  ricevuta_il: string
  note: string
}

export interface AnteprimaCancellazione {
  anonimizza: boolean
  /** Why the registry data stay, when they do. */
  motivo_anagrafica: string | null
  voci: string[]
}

/** Everything the app holds about a person: sections of values, lists or nothing. */
export type Fascicolo = { persona: PersonaBreve; generato_il: string } & Record<string, unknown>

// --- Corrections to BuonaStrada data (DEC-31) ------------------------------------------

export type StatoCorrezione = 'IN_ATTESA' | 'INOLTRATA' | 'RECEPITA' | 'SUPERATA' | 'SCARTATA'

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
  /** Non-medical dietary needs (vegetarian…): the need, never the reason. */
  esigenze_alimentari: string
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

// --- Fees and payments (amounts are decimal strings, e.g. "12.50") --------------------------

export type CategoriaQuota = 'CENSIMENTO' | 'GRUPPO' | 'MENSILE'
export type Destinatari = 'TUTTI' | 'RAGAZZI' | 'CAPI' | 'UNITA'
export type MetodoPagamento = 'CONTANTI' | 'BONIFICO' | 'ALTRO'

export interface TipoQuotaIn {
  nome: string
  categoria: CategoriaQuota
  anno: number
  importo: string
  sconto_famiglia: string
  destinatari: Destinatari
  unita: number[]
  scadenza: string | null
  mesi: number[]
  giorno_scadenza: number | null
}

export interface TipoQuota extends TipoQuotaIn {
  id: number
  categoria_nome: string
  destinatari_nome: string
  anno_etichetta: string
  emesse: number
}

export interface Quota {
  id: number
  persona_id: number
  persona: string
  descrizione: string
  categoria: CategoriaQuota
  periodo: string
  scadenza: string
  importo: string
  sconto: string
  /** Seen by the Co.Ca. and by the family on its own fees; the note only by the Co.Ca. */
  agevolazione: { importo: string; decisa_il: string; nota: string } | null
  dovuto: string
  pagato: string
  residuo: string
  annullata: boolean
  motivo_annullamento: string
}

export interface QuotePersona {
  quote: Quota[]
  /** Open fees of the rest of the family, to record one payment over several. */
  famiglia: Quota[]
  puo_registrare: boolean
  puo_gestire: boolean
  puo_agevolare: boolean
}

export interface PagamentoIn {
  data: string
  metodo: MetodoPagamento
  versato_da: string
  note: string
  righe: { quota_id: number; importo: string }[]
}

export interface Pagamento {
  id: number
  numero: string
  data: string
  importo: string
  metodo: MetodoPagamento
  metodo_nome: string
  versato_da: string
  note: string
  righe: { quota_id: number; persona: string; descrizione: string; importo: string }[]
  registrato_da: string | null
  ricevuta_inviata_il: string | null
  annullato: boolean
  motivo_annullamento: string
}

export interface MieQuote {
  quote: Quota[]
  pagamenti: Pagamento[]
  link_pagamento: string
}

export interface RigaSituazione {
  persona_id: number
  persona: string
  dovuto: string
  pagato: string
  residuo: string
  scadute: number
}

export interface Coniugi {
  id: number
  persona: string
  coniuge: string
}

export const PERCORSO_PAGAMENTI = '/api/v1/pagamenti'
export const ricevutaPdf = (pagamento: number) => `/api/v1/pagamenti/${pagamento}/ricevuta.pdf`

/** "12.50" → "12,50 €" */
export function euro(valore: string | number): string {
  return `${Number(valore).toLocaleString('it-IT', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} €`
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
  miaSquadriglia: () => richiesta<MiaSquadriglia[]>('/api/v1/mia-squadriglia'),
  telefonoSquadriglia: (persona: number) =>
    richiesta<ImpostazioneTelefono>(`/api/v1/persone/${persona}/telefono-squadriglia`),
  impostaTelefonoSquadriglia: (
    persona: number,
    dati: { genitore_id: number | null; per_tutti_i_figli: boolean; nascosto: boolean },
  ) =>
    richiesta<ImpostazioneTelefono>(`/api/v1/persone/${persona}/telefono-squadriglia`, {
      metodo: 'PUT',
      corpo: dati,
    }),
  codiciIscrizione: (unita: number) =>
    richiesta<{ puo_creare: boolean; codici: CodiceIscrizione[] }>(
      `/api/v1/unita/${unita}/codici-iscrizione`,
    ),
  creaCodiceIscrizione: (unita: number, dati: { tipo: string; scadenza: string }) =>
    richiesta<CodiceIscrizione>(`/api/v1/unita/${unita}/codici-iscrizione`, {
      metodo: 'POST',
      corpo: dati,
    }),
  disattivaCodice: (id: number) =>
    richiesta<CodiceIscrizione>(`/api/v1/codici-iscrizione/${id}/disattiva`, { metodo: 'POST' }),
  infoCodice: (codice: string) =>
    richiesta<InfoCodice>(`/api/v1/iscrizione/${encodeURIComponent(codice)}`),
  chiediIscrizione: (codice: string, dati: DatiIscrizione) =>
    richiesta<{ serve_account: boolean; richiesta_id: number | null }>(
      `/api/v1/iscrizione/${encodeURIComponent(codice)}`,
      { metodo: 'POST', corpo: dati },
    ),
  mieIscrizioni: () => richiesta<RichiestaIscrizione[]>('/api/v1/mie-iscrizioni'),
  iscrizioniDaDecidere: (tutte = false) =>
    richiesta<RichiestaIscrizione[]>(`/api/v1/iscrizioni${tutte ? '?tutte=true' : ''}`),
  approvaIscrizione: (id: number, scadenza: string) =>
    richiesta<RichiestaIscrizione>(`/api/v1/iscrizioni/${id}/approva`, {
      metodo: 'POST',
      corpo: { scadenza_completamento: scadenza },
    }),
  completamento: (id: number) =>
    richiesta<Completamento & { richiesta: RichiestaIscrizione }>(
      `/api/v1/iscrizioni/${id}/completamento`,
    ),
  completa: (id: number, dati: Completamento) =>
    richiesta<Completamento & { richiesta: RichiestaIscrizione }>(
      `/api/v1/iscrizioni/${id}/completamento`,
      { metodo: 'PUT', corpo: dati },
    ),
  modulistica: () =>
    richiesta<{ puo_gestire: boolean; moduli: ModuloVuoto[] }>('/api/v1/modulistica'),
  caricaModulo: (titolo: string, file: File) =>
    richiesta<ModuloVuoto>('/api/v1/modulistica', {
      metodo: 'POST',
      corpo: conFile({ titolo }, file),
    }),
  attivaModulo: (id: number, attivo: boolean) =>
    richiesta<ModuloVuoto>(`/api/v1/modulistica/${id}/attivo`, {
      metodo: 'POST',
      corpo: { attivo },
    }),
  moduliFirmati: (iscrizione: number) =>
    richiesta<ModuliFirmati>(`/api/v1/iscrizioni/${iscrizione}/moduli`),
  caricaModuloFirmato: (iscrizione: number, file: File) =>
    richiesta<ModuliFirmati>(`/api/v1/iscrizioni/${iscrizione}/moduli`, {
      metodo: 'POST',
      corpo: conFile({}, file),
    }),
  togliModuloFirmato: (id: number) =>
    richiesta<ModuliFirmati>(`/api/v1/moduli-firmati/${id}`, { metodo: 'DELETE' }),
  verificaModuli: (iscrizione: number, consensi: Consensi) =>
    richiesta<RichiestaIscrizione>(`/api/v1/iscrizioni/${iscrizione}/verifica-moduli`, {
      metodo: 'POST',
      corpo: consensi,
    }),
  iscrizioniBuonaStrada: () => richiesta<DaInserire[]>('/api/v1/iscrizioni-buonastrada'),
  segnaInserita: (id: number) =>
    richiesta<RichiestaIscrizione>(`/api/v1/iscrizioni/${id}/inserita`, { metodo: 'POST' }),
  rifiutaIscrizione: (id: number, motivo: string) =>
    richiesta<RichiestaIscrizione>(`/api/v1/iscrizioni/${id}/rifiuta`, {
      metodo: 'POST',
      corpo: { motivo },
    }),
  visibilitaGenitori: (persona: number) =>
    richiesta<VisibilitaGenitori>(`/api/v1/persone/${persona}/visibilita-genitori`),
  scegliVisibilitaGenitori: (persona: number, dati: SceltaVisibilita) =>
    richiesta<VisibilitaGenitori>(`/api/v1/persone/${persona}/visibilita-genitori`, {
      metodo: 'PUT',
      corpo: dati,
    }),
  richiesteDiritti: () => richiesta<RichiestaDiritti[]>('/api/v1/richieste-diritti'),
  registraRichiesta: (dati: NuovaRichiesta) =>
    richiesta<RichiestaDiritti>('/api/v1/richieste-diritti', { metodo: 'POST', corpo: dati }),
  aggiornaRichiesta: (
    id: number,
    dati: { inoltrata_nazionale_il?: string | null; evasa_il?: string | null },
  ) =>
    richiesta<RichiestaDiritti>(`/api/v1/richieste-diritti/${id}`, {
      metodo: 'PATCH',
      corpo: dati,
    }),
  fascicolo: (persona: number) => richiesta<Fascicolo>(`/api/v1/persone/${persona}/fascicolo`),
  anteprimaCancellazione: (persona: number) =>
    richiesta<AnteprimaCancellazione>(`/api/v1/persone/${persona}/cancellazione`),
  cancella: (persona: number, cognome: string) =>
    richiesta<AnteprimaCancellazione>(`/api/v1/persone/${persona}/cancellazione`, {
      metodo: 'POST',
      corpo: { cognome },
    }),
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
  caricaExport: (file: File, aggiornatoAl: string) => {
    const dati = new FormData()
    dati.append('file', file)
    dati.append('aggiornato_al', aggiornatoAl)
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
  tipiQuota: (anno?: number) =>
    richiesta<TipoQuota[]>(`/api/v1/quote/tipi${anno ? `?anno=${anno}` : ''}`),
  creaTipoQuota: (dati: TipoQuotaIn) =>
    richiesta<TipoQuota>('/api/v1/quote/tipi', { metodo: 'POST', corpo: dati }),
  modificaTipoQuota: (id: number, dati: TipoQuotaIn) =>
    richiesta<TipoQuota>(`/api/v1/quote/tipi/${id}`, { metodo: 'PUT', corpo: dati }),
  emettiQuote: (id: number) =>
    richiesta<{ emesse: number }>(`/api/v1/quote/tipi/${id}/emetti`, { metodo: 'POST' }),
  quotePersona: (persona: number, anno?: number) =>
    richiesta<QuotePersona>(`/api/v1/persone/${persona}/quote${anno ? `?anno=${anno}` : ''}`),
  pagamentiPersona: (persona: number, anno?: number) =>
    richiesta<Pagamento[]>(`/api/v1/persone/${persona}/pagamenti${anno ? `?anno=${anno}` : ''}`),
  annullaQuota: (id: number, motivo: string) =>
    richiesta<Quota>(`/api/v1/quote/${id}/annulla`, { metodo: 'POST', corpo: { motivo } }),
  agevola: (id: number, dati: { importo: string; decisa_il: string; nota: string }) =>
    richiesta<Quota>(`/api/v1/quote/${id}/agevolazione`, { metodo: 'PUT', corpo: dati }),
  togliAgevolazione: (id: number) =>
    richiesta<Quota>(`/api/v1/quote/${id}/agevolazione`, { metodo: 'DELETE' }),
  situazioneQuote: (unita: number, anno?: number) =>
    richiesta<RigaSituazione[]>(
      `/api/v1/quote/situazione?unita=${unita}${anno ? `&anno=${anno}` : ''}`,
    ),
  reinviaRicevuta: (id: number) =>
    richiesta<Pagamento>(`/api/v1/pagamenti/${id}/invia`, { metodo: 'POST' }),
  annullaPagamento: (id: number, motivo: string) =>
    richiesta<Pagamento>(`/api/v1/pagamenti/${id}/annulla`, { metodo: 'POST', corpo: { motivo } }),
  mieQuote: (anno?: number) =>
    richiesta<MieQuote>(`/api/v1/mie-quote${anno ? `?anno=${anno}` : ''}`),
  coniugi: () => richiesta<Coniugi[]>('/api/v1/quote/coniugi'),
  aggiungiConiugi: (persona_id: number, coniuge_id: number) =>
    richiesta<Coniugi>('/api/v1/quote/coniugi', {
      metodo: 'POST',
      corpo: { persona_id, coniuge_id },
    }),
  togliConiugi: (id: number) =>
    richiesta<void>(`/api/v1/quote/coniugi/${id}`, { metodo: 'DELETE' }),
  impostazioniQuote: () => richiesta<{ link_pagamento: string }>('/api/v1/quote/impostazioni'),
  salvaImpostazioniQuote: (link_pagamento: string) =>
    richiesta<{ link_pagamento: string }>('/api/v1/quote/impostazioni', {
      metodo: 'PUT',
      corpo: { link_pagamento },
    }),
  applicaImportazione: (id: number, scelte: Record<string, Lato>) =>
    richiesta<EsitoImportazione>(`/api/v1/importazioni/${id}/applica`, {
      metodo: 'POST',
      corpo: { scelte },
    }),
}
