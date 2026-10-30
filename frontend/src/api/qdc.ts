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
  /** Cash book: the Co.Ca. and the unit treasurers. */
  vede_cassa: boolean
  /** Patrols whose meetings the user may create as the CSQ's delegate. */
  squadriglie_delegate: number[]
  /** Events on BuonaCaccia: registers someone (capi) or themself (adults). */
  eventi_buonacaccia: boolean
  /** Capigruppo: the training camps of the capi, for the Zona. */
  formazione_capi: boolean
  /** May use the app as another user (capigruppo, administrators, unit staff). */
  puo_impersonare: boolean
  /** Set while using the app as another user. */
  impersonazione: { impersonato: string; email: string; scade_il: string } | null
  /** A ragazzo who helps run imprese (CSQ, Consiglio d'impresa): their reparto. */
  imprese_reparto: number | null
}

export interface Impersonazione {
  id: number
  impersonatore: string
  impersonato: string
  motivo: string
  iniziata_il: string
  scade_il: string
  finita_il: string | null
}

export interface CandidatoImpersonazione {
  utente_id: number
  persona_id: number | null
  nome: string
  email: string
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
  /** Profile photo (DEC-201): there is one the user may see; who may upload one. */
  foto?: boolean
  puo_caricare_foto?: boolean
  /** The capi's file (DEC-47, DEC-206), when the person has been a capo. */
  fascicolo_capo?: boolean
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
  /** Additional group roles: capigruppo, group treasurers, technical administrators. */
  incarichi: Incarico[]
  nomina: Scelta[]
  /** Capi of the Co.Ca. serving in no unit for now. */
  a_disposizione: Incarico[]
  nomina_a_disposizione: Scelta[]
  /** For the capigruppo: capi with no service at all. */
  senza_servizio: PersonaBreve[]
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
  // The rest of the AGESCI form and the optional fields (DEC-48, DEC-49). Absent from
  // the camp download (DEC-55) and from copies saved before they existed.
  tessera_sanitaria?: string
  reperibilita_nome?: string
  reperibilita_telefono?: string
  antitetanica?: boolean | null
  note_sanitarie?: string
  gruppo_sanguigno?: string
  medico_curante?: string
  altre_vaccinazioni?: string
}

export interface Sanitarie extends SanitarieIn {
  compilate: boolean
  inserite_da: string | null
  aggiornate_il: string | null
  puo_modificare: boolean
  // Paper (DEC-52, DEC-54).
  firmata_il?: string | null
  da_rifirmare?: boolean
  prescrizione_consegnata_il?: string | null
  puo_registrare_firma?: boolean
}

export type TipoNota = 'STAFF' | 'CSQ'

/** A note on a ragazzo (DEC-39, DEC-40). */
export interface Nota {
  id: number
  tipo: TipoNota
  tipo_nome: string
  testo: string
  autore: string
  creata_il: string
  aggiornata_il: string
  visibile_ragazzo: boolean
  visibile_genitori: boolean
  visibile_csq: boolean
  condivisa_fuori_coca: boolean
  puo_modificare: boolean
  puo_cambiare_visibilita: boolean
}

export interface NoteSchede {
  note: Nota[]
  /** The type a new note by this user would have; null: they write none here. */
  scrive: TipoNota | null
  csq_possibile: boolean
  /** Rules on the relationship with the minor: null for who may not read them (DEC-43). */
  regole: string | null
  regole_aggiornate_il: string | null
  puo_scrivere_regole: boolean
}

export interface NotaIn {
  testo: string
  visibile_ragazzo: boolean
  visibile_genitori: boolean
  visibile_csq: boolean
}

export const percorsoNote = (persona: number) => `/api/v1/persone/${persona}/note`
export const percorsoNota = (nota: number) => `/api/v1/note/${nota}`

export interface Intestazione {
  denominazione_sociale: string
  codice_fiscale: string
  sede_indirizzo: string
  sede_cap: string
  sede_comune: string
  sede_provincia: string
  telefono: string
  cellulare: string
  email: string
  pec: string
  sito: string
  runts_repertorio: string
  runts_data: string | null
  logo?: boolean
  puo_modificare?: boolean
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
  /** For the Co.Ca. only, in evidence at camp (DEC-43, DEC-95). */
  regole_rapporto?: string
  /** A small copy of the profile photo, as a data URL (DEC-201). */
  foto?: string | null
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
  /** Default: the unit's cash box for cash, else the bank account. */
  cassa_id?: number | null
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
  /** The capigruppo and group treasurer; who recorded it, until a cash check. */
  puo_annullare: boolean
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

// --- Cash book --------------------------------------------------------------------------------

export type TipoCassa = 'BANCA' | 'CONTANTI'
export type TipoMovimento = 'ENTRATA' | 'USCITA' | 'GIROCONTO' | 'RETTIFICA'

export interface VoceModelloD {
  id: string
  lato: 'E' | 'U'
  riga: string
  titolo_riga: string
  nome: string
}

export interface CassaIn {
  nome: string
  tipo: TipoCassa
  unita_id: number | null
  saldo_iniziale: string
  data_saldo_iniziale: string
  attiva: boolean
}

export interface Cassa extends CassaIn {
  id: number
  /** Hidden from an R/S treasurer on the shared bank account. */
  saldo: string | null
  puo_registrare: boolean
  senza_giustificativo: number
}

export interface MovimentoIn {
  cassa_id: number
  tipo: TipoMovimento
  data: string
  importo: string
  descrizione: string
  voce_id: string
  unita_id: number | null
  cassa_destinazione_id: number | null
  evento_id: number | null
  /** Base64 data URL: the record can wait, encrypted, in the offline queue. */
  giustificativo: string
}

export interface Movimento {
  id: number
  cassa_id: number
  cassa: string
  tipo: TipoMovimento
  tipo_nome: string
  data: string
  importo: string
  effetto: string
  descrizione: string
  voce_riga: string
  voce_nome: string
  unita_id: number | null
  cassa_destinazione: string | null
  ha_giustificativo: boolean
  senza_giustificativo: boolean
  storno_di: number | null
  stornato: boolean
  motivo_storno: string
  da_quote: boolean
  evento_id: number | null
  evento: string | null
  registrato_da: string | null
  creato_il: string
}

export interface Verifica {
  id: number
  data: string
  saldo_contato: string
  saldo_app: string
  differenza: string
  motivo: string
  registrata_da: string | null
}

export interface SpesaAnticipata {
  id: number
  capo_id: number
  capo: string
  data: string
  importo: string
  descrizione: string
  unita_id: number | null
  ha_giustificativo: boolean
  stato: 'da_rimborsare' | 'rimborsata' | 'respinta'
  rimborsata_il: string | null
  motivo_rifiuto: string
  puo_rimborsare: boolean
}

export interface ModelloD {
  anno_bilancio: string
  anno_etichetta: string
  righe: { lato: 'E' | 'U'; riga: string; titolo: string; totale: string }[]
  entrate: string
  uscite: string
  rettifiche: string
  saldi: Cassa[]
}

// --- Events and attendance ---------------------------------------------------------------------

export type TipoEvento =
  'RIUNIONE' | 'USCITA' | 'CAMPO' | 'AUTOFINANZIAMENTO' | 'MISSIONE' | 'ALTRO'
/** Who of the reparti involved is invited: all, CSQ, CSQ and VCSQ, Alta Squadriglia. */
export type Cerchia = 'TUTTI' | 'CONCA' | 'CONCAVI' | 'ALTA_SQ'
export type LivelloEvento = 'GRUPPO' | 'BRANCA' | 'UNITA' | 'SQUADRIGLIA' | 'ESTERNO'
export type StatoPartecipazione = 'INVITATO' | 'NON_PARTECIPA' | 'NON_INVITATO'
export type StatoPresenza = 'PRESENTE' | 'ASSENTE' | 'GIUSTIFICATO'

export interface EventoIn {
  titolo: string
  tipo: TipoEvento
  livello: LivelloEvento
  branca: string | null
  unita: number[]
  squadriglia_id: number | null
  inizio: string
  fine: string
  luogo: string
  descrizione: string
  /** A patrol's mission: for the parents and the capi, not the ragazzi. */
  note_genitori: string
  cerchia: Cerchia
}

export interface MiaPartecipazione {
  persona_id: number
  persona: string
  stato: StatoPartecipazione
  /** The staff's reason when not invited: the family reads it. */
  motivo: string
  puo_segnalare: boolean
}

export interface Evento {
  id: number
  titolo: string
  tipo: TipoEvento
  tipo_nome: string
  livello: LivelloEvento
  livello_nome: string
  branca: string
  unita: number[]
  unita_nomi: string[]
  squadriglia_id: number | null
  squadriglia: string | null
  inizio: string
  fine: string
  luogo: string
  descrizione: string
  /** null: not for this user (the ragazzi). */
  note_genitori: string | null
  cerchia: Cerchia
  cerchia_nome: string
  riunione: boolean
  annullato: boolean
  motivo_annullamento: string
  mie: MiaPartecipazione[]
  puo_gestire: boolean
  /** The event's fee, also in instalments (DEC-77); null: no fee. */
  quota: QuotaEvento | null
}

export interface RataEvento {
  descrizione: string
  importo: string
  scadenza: string
}

export interface QuotaEvento {
  nome: string
  rate: RataEvento[]
  totale: string
  sconto_famiglia: string
}

export interface QuotaPartecipante {
  quota_id: number
  descrizione: string
  scadenza: string
  importo: string
  dovuto: string
  pagato: string
  residuo: string
  annullata: boolean
}

export interface BudgetEvento {
  partecipanti: number
  /** All the staff of the units involved, with their own contribution per head. */
  staff: number
  quota_staff: string
  quota: string | null
  contributo: string
  totale: string
  /** Which of the three the app computed. */
  calcolato: 'quota' | 'contributo' | 'totale'
}

export interface RendicontoEvento {
  budget: BudgetEvento | null
  entrate: string
  uscite: string
  saldo: string
  quote_dovute: string
  quote_incassate: string
  agevolazioni: string
  puo_gestire: boolean
}

export interface SituazioneQuoteEvento {
  persona_id: number
  persona: string
  quote: QuotaPartecipante[]
}

export interface Partecipante {
  persona_id: number
  cognome: string
  nome: string
  stato: StatoPartecipazione
  motivo: string
  presenza: StatoPresenza | null
}

export interface DettaglioEvento extends Evento {
  partecipanti: Partecipante[]
  puo_presenze: boolean
  puo_non_invitare: boolean
  /** The participants' medical forms (DEC-195). */
  puo_stampare_schede?: boolean
}

export interface RiunioneRicorrente {
  id: number
  giorno_settimana: number
  ora_inizio: string
  ora_fine: string
  luogo: string
  dal: string
  al: string
  riunioni: number
}

/** Optional emails; access codes, invitations, security warnings, registration and
 * receipts are always sent. */
export interface PreferenzeEmail {
  eventi: boolean
  promemoria_quote: boolean
  maggiore_eta: boolean
  riepiloghi: boolean
}

/** The personal calendar; a capo has three views (their unit; Co.Ca. and their unit;
 * the whole group), everyone else one. */
export interface Calendario {
  url: string
  viste: { vista: string; nome: string; url: string }[]
}

export interface Delega {
  persona_id: number | null
  persona: string | null
  puo_delegare: boolean
}

export interface AltaSquadriglia {
  anno: number
  persone: number[]
  puo_scegliere: boolean
}

export const percorsoPresenze = (evento: number) => `/api/v1/eventi/${evento}/presenze`
export const foglioPresenze = (evento: number) => `/api/v1/eventi/${evento}/foglio-presenze.pdf`

// --- Events on BuonaCaccia (DEC-158…DEC-164) -----------------------------------------------

export type TipoDomanda =
  'SCELTA_SINGOLA' | 'SCELTA_MULTIPLA' | 'BREVE' | 'LUNGA' | 'SI_NO' | 'FOTO'
export type StatoIscrizioneBC = 'AMMESSO' | 'IN_ATTESA' | 'NON_AMMESSO' | 'CANCELLATA'
export type ModoLiberatoria = 'APP' | 'ALTRI_CANALI'
export type TipoCampoFormazione = 'CFT' | 'CFM' | 'CFA' | 'CCG' | 'MODULO' | 'ALTRO'
export type RispostaScheda = string | string[] | boolean

export const TIPI_DOMANDA: [TipoDomanda, string][] = [
  ['SCELTA_SINGOLA', 'Scelta singola'],
  ['SCELTA_MULTIPLA', 'Scelta multipla'],
  ['BREVE', 'Risposta breve'],
  ['LUNGA', 'Risposta lunga'],
  ['SI_NO', 'Sì / no'],
  ['FOTO', 'Foto'],
]

export const TIPI_CAMPO: [TipoCampoFormazione, string][] = [
  ['CFT', 'Campo di Formazione Tirocinanti (CFT)'],
  ['CFM', 'Campo di Formazione Metodologica (CFM)'],
  ['CFA', 'Campo di Formazione Associativa (CFA)'],
  ['CCG', 'Campo per Capigruppo (CCG)'],
  ['MODULO', 'Modulo formativo'],
  ['ALTRO', 'Altro'],
]

export interface Domanda {
  id: string
  tipo: TipoDomanda
  testo: string
  opzioni: string[]
  obbligatoria: boolean
}

export interface VersioneScheda {
  id: number
  modello_id: number
  nome: string
  numero: number
  domande: Domanda[]
  chiede_foto: boolean
}

export interface SchedaBC {
  id: number
  nome: string
  ultima: VersioneScheda
  versioni: number
  usata: number
}

export interface EventoBCIn {
  titolo: string
  tipo: TipoEvento
  inizio: string
  fine: string
  luogo: string
  descrizione: string
  formazione_capi: boolean
  piccole_orme: boolean
  tipo_campo: TipoCampoFormazione | null
  specifica: string
}

export interface EventoBCTrovato {
  id: number
  titolo: string
  inizio: string
  fine: string
  luogo: string
  formazione_capi: boolean
  piccole_orme: boolean
}

export interface QuotaIscrizioneBC {
  id: number
  importo: string
  scadenza: string
  dovuto: string
  pagato: string
  residuo: string
  annullata: boolean
}

export interface IscrizioneBC {
  id: number
  evento_id: number
  evento: string
  inizio: string
  persona_id: number
  persona: string
  stato: StatoIscrizioneBC
  stato_nome: string
  attiva: boolean
  iscritto_il: string
  scadenza: string
  limite_cancellazione: string
  cancellata_il: string | null
  /** Only for who manages the registration. */
  link_gestione: string | null
  modo_liberatoria: ModoLiberatoria
  scadenza_liberatoria: string
  scadenza_liberatoria_fissata: boolean
  liberatoria_da_firmare: boolean
  liberatoria_firmata: boolean
  liberatoria_ricevuta_il: string | null
  liberatoria_caricata_il: string | null
  esito_liberatoria: '' | 'VALIDATA' | 'RIGETTATA'
  motivo_rigetto: string
  risposte: Record<string, RispostaScheda>
  risposte_il: string | null
  risposte_mancanti: string[]
  foto: boolean
  /** Capi only. */
  presentazione: string | null
  // Piccole Orme: what does not fit (lived before, not in Responsabilità, too short).
  avvisi: string[]
  scheda_inviata_il: string | null
  pagata_il: string | null
  quota: QuotaIscrizioneBC | null
  puo_gestire: boolean
  /** The family: release form, answers. */
  puo_rispondere: boolean
  /** Answers and photo: the family or who manages the registration. */
  puo_scrivere_scheda: boolean
  puo_togliere_quota: boolean
}

export interface IscrizioneBCIn {
  persona_id: number
  iscritto_il: string
  stato: StatoIscrizioneBC
  link_gestione: string
  modo_liberatoria: ModoLiberatoria
  scadenza_liberatoria: string | null
  importo: string | null
  scadenza_quota: string | null
}

export interface AdultoBC {
  persona_id: number
  persona: string
  partecipa: boolean
  quota_versata: string | null
  puo_modificare: boolean
}

export interface DettaglioBC {
  id: number
  titolo: string
  tipo: TipoEvento
  inizio: string
  fine: string
  luogo: string
  descrizione: string
  annullato: boolean
  formazione_capi: boolean
  piccole_orme: boolean
  tipo_campo: TipoCampoFormazione | ''
  tipo_campo_nome: string
  specifica: string
  scheda: VersioneScheda | null
  iscrizioni: IscrizioneBC[]
  adulti: AdultoBC[]
  puo_gestire: boolean
  puo_iscrivere: boolean
  puo_partecipare: boolean
}

export interface PassiBC {
  liberatoria_ricevuta_il?: string | null
  liberatoria_caricata_il?: string | null
  scheda_inviata_il?: string | null
  pagata_il?: string | null
}

export interface RiepilogoBC {
  persona: string
  righe: { domanda: string; tipo: TipoDomanda; risposta: string }[]
  presentazione: string
  foto: boolean
}

export interface FormazioneCapo {
  persona_id: number
  persona: string
  evento_id: number
  evento: string
  dal: string
  al: string
  luogo: string
  tipo_campo: string
  quota_versata: string | null
}

// --- Progressione Personale E/G (DEC-56…DEC-74, DEC-171…DEC-173) -------------------------

export type Precisione = 'GIORNO' | 'MESE' | 'ANNO' | 'IGNOTA'
export type FaseProgressione = 'SCOPERTA' | 'COMPETENZA' | 'RESPONSABILITA'
export type StatoPercorso =
  'BOZZA' | 'CONCORDATO' | 'IN_CORSO' | 'DA_VERIFICARE' | 'CONCLUSO' | 'INTERROTTO'
export type AzionePercorso =
  'concorda' | 'avvia' | 'proponi_verifica' | 'prosegui' | 'convalida' | 'interrompi'

export interface DataParziale {
  data: string | null
  precisione: Precisione
}

export interface TappaSentiero {
  id: number
  fase: FaseProgressione
  fase_nome: string
  inizio: DataParziale
  collocamento: boolean
  motivazione: string
  completata: DataParziale | null
  in_corso: boolean
  distintivo: DataParziale | null
  nota_rettifica: string
}

export interface RevisionePercorso {
  testo: string
  criterio_verifica: string
  termine: string | null
  sostituita_il: string
}

/** An image or a PDF on an item of the Progressione (DEC-42, DEC-202). */
export interface AllegatoPP {
  id: number
  titolo: string
  tipo_file: string
  caricato_il: string
}

export type TipoVoceAllegato = 'mete' | 'impegni' | 'competenze'
export const allegatoPP = (id: number) => `/api/v1/allegati-pp/${id}`

/** The file of a year (DEC-38, DEC-203): sections of labelled rows. */
export interface SezioneFascicolo {
  titolo: string
  voci: { etichetta: string; valore: string }[]
  vuota: string
}

export interface FascicoloAnno {
  persona_id: number
  persona: string
  anno: number
  etichetta: string
  sezioni: SezioneFascicolo[]
  foto: boolean
  anni: { anno: number; etichetta: string }[]
}

/** The capi's file (DEC-47, DEC-134, DEC-206…DEC-208). */
export interface FascicoloCapo {
  persona_id: number
  persona: string
  livello_formazione: number | null
  anno_ingresso_coca: number | null
  numero_nomina: string
  data_nomina: string | null
  anni_di_servizio: number
  anni: {
    anno: number
    etichetta: string
    ruoli: string[]
    in_coca: boolean
    ricostruiti: { id: number; testo: string }[]
  }[]
  formazione: {
    id: number | null
    tipo: string
    tipo_nome: string
    specifica: string
    data: string
    precisione: Precisione
    luogo: string
    note: string
    da_buonacaccia: boolean
  }[]
  puo_modificare: boolean
  tipi_formazione: Scelta[]
  ruoli_passati: Scelta[]
}

export interface ServizioPassatoIn {
  anno: number
  unita_testo: string
  ruolo: string
  note: string
}

export interface FormazioneIn {
  tipo: string
  specifica: string
  data: string
  precisione: Precisione
  luogo: string
  note: string
}

/** Associative years: closed, reopened (DEC-45, DEC-209, DEC-210). */
export interface AnniGruppo {
  anni: {
    anno: number
    etichetta: string
    in_corso: boolean
    chiuso_il: string | null
    riaperto_fino_al: string | null
    motivo_riapertura: string
  }[]
  da_chiudere: number | null
}

/** Archiving two years after leaving (DEC-44, DEC-211). */
export interface ArchivioGruppo {
  drive_configurato: boolean
  /** With the parents that go with them (DEC-214). */
  da_archiviare: { id: number; nome: string; uscita: string; genitori: string[] }[]
  archiviate: { nome: string; nome_file: string; archiviata_il: string }[]
}

export interface EsitoImportazione {
  persona_id: number
  persona: string
  periodi: number
  note: number
  anni_di_servizio: number
  formazione: number
}

export const trasferimentoJson = (persona: number) =>
  `/api/v1/persone/${persona}/trasferimento.json`

export const fotoProfilo = (persona: number) => `/api/v1/persone/${persona}/foto`
export const fascicoloAnnoPdf = (persona: number, anno: number) =>
  `/api/v1/persone/${persona}/fascicolo-anno.pdf?anno=${anno}`
export const reportPassaggioPdf = (passaggio: number, persona: number) =>
  `/api/v1/passaggi/${passaggio}/report/${persona}.pdf`

export interface PercorsoPersonale {
  id: number
  testo: string
  termine: string | null
  stato: StatoPercorso
  stato_nome: string
  proposto_dal_ragazzo: boolean
  concordato_il: string | null
  avviato_il: string | null
  verifica_proposta: boolean
  verificato_il: string | null
  sede: string
  sede_nome: string
  interrotto_il: string | null
  motivo_interruzione: string
  revisioni: RevisionePercorso[]
  allegati?: AllegatoPP[]
}

export interface MetaEG extends PercorsoPersonale {
  riservata: boolean
}

export interface ImpegnoEG extends PercorsoPersonale {
  criterio_verifica: string
  mete: number[]
  // L/C: the stagione of a preda or volo.
  stagione_id: number | null
  stagione: string
}

export type StatoStagione = 'PREVISTA' | 'APERTA' | 'CHIUSA' | 'ANNULLATA'

/** A stagione di caccia o di volo of a branco or cerchio (DEC-66, DEC-183). */
export interface Stagione {
  id: number
  nome: string
  stato: StatoStagione
  stato_nome: string
  inizio_previsto: string
  fine_prevista: string
  lancio: string | null
  chiusa_il: string | null
  prede: number
  conquistate: number
  da_rileggere: string[]
  avvisi: string[]
}

export interface StagioniUnita {
  unita: string
  stagioni: Stagione[]
  puo_gestire: boolean
}

export interface StagioneIn {
  nome: string
  inizio_previsto: string
  fine_prevista: string
}

export type TipoConclusione = 'PARTENZA' | 'SALUTO_FRATERNO' | 'INTERRUZIONE' | 'TRASFERIMENTO'

/** A Punto della Strada (DEC-67); `riservato` is null for who may not read it (DEC-180). */
export interface PuntoStrada {
  id: number
  periodo_id: number
  data: string
  sintesi: string
  servizio: string
  riservato: string | null
  /** The rover's or scolta's own reading (DEC-188). */
  voce: string | null
  obiettivi: number[]
}

export interface PuntoStradaIn {
  data: string
  sintesi: string
  servizio: string
  riservato?: string
  obiettivi: number[]
}

export interface PeriodoBranca {
  id: number
  branca: string
  branca_nome: string
  inizio: DataParziale
  fine: string | null
  motivo_fine: string
  attivo: boolean
  passaggio: {
    data: string
    da: string
    a: string
    data_cerimonia: string | null
    sintesi: string
  } | null
  promessa: DataParziale | null
  tappe: TappaSentiero[]
  // R/S only (DEC-67).
  firma_carta: DataParziale | null
  conclusione: {
    tipo: TipoConclusione
    tipo_nome: string
    data: DataParziale
    nota: string
  } | null
}

export type StatoPassaggio = 'PREPARATO' | 'ESEGUITO' | 'ANNULLATO' | 'RETTIFICATO'

export interface PersonaPassaggio {
  persona_id: number
  persona: string
  sintesi: string
  rettificata: boolean
  motivo_rettifica: string
}

export interface PassaggioBranca {
  id: number
  unita_origine_id: number
  unita_origine: string
  unita_destinazione_id: number
  unita_destinazione: string
  data: string
  data_decisione: string | null
  data_cerimonia: string | null
  stato: StatoPassaggio
  stato_nome: string
  motivo_annullamento: string
  nota_rettifica: string
  persone: PersonaPassaggio[]
  puo_gestire: boolean
}

export interface PassaggiUnita {
  unita: string
  in_uscita: PassaggioBranca[]
  in_entrata: PassaggioBranca[]
  ragazzi: { id: number; nome: string }[]
  destinazioni: { id: number; nome: string }[]
  puo_preparare: boolean
}

export interface PassaggioIn {
  unita_destinazione_id: number
  data: string
  data_decisione: string | null
  data_cerimonia: string | null
  persone: { persona_id: number; sintesi: string }[]
}

export type TipoCompetenza = 'SPECIALITA' | 'BREVETTO' | 'SPECIALITA_SQ' | 'SPECIALITA_LC'
export type StatoCompetenza =
  'PROPOSTO' | 'IN_CORSO' | 'DA_VERIFICARE' | 'RICONOSCIUTO' | 'INTERROTTO'
export type AzioneCompetenza =
  'avvia' | 'proponi_verifica' | 'prosegui' | 'riconosci' | 'interrompi'

export interface Competenza {
  id: number
  tipo: TipoCompetenza
  tipo_nome: string
  codice: string
  nome: string
  stato: StatoCompetenza
  stato_nome: string
  carta: string
  maestro: string
  confronto: string
  collegati: number[]
  avviato_il: string | null
  verifica_proposta: boolean
  riconosciuto: DataParziale | null
  storico: boolean
  distintivo: DataParziale | null
  interrotto_il: string | null
  motivo_interruzione: string
  allegati?: AllegatoPP[]
}

export interface PostoAzione {
  id: number
  impresa_id: number
  impresa: string
  impresa_livello: string
  persona_id: number
  persona: string
  ruolo: string
  impegno_id: number | null
  verificato_il: string | null
  sede_nome: string
}

export interface VoceCatalogo {
  codice: string
  nome: string
}

export interface CataloghiPP {
  specialita: VoceCatalogo[]
  brevetti: VoceCatalogo[]
  specialita_squadriglia: VoceCatalogo[]
  specialita_lc: VoceCatalogo[]
}

export type LivelloImpresa = 'REPARTO' | 'SQUADRIGLIA' | 'ALTA_SQ'

export interface ImpresaEG {
  id: number
  livello: LivelloImpresa
  livello_nome: string
  squadriglia_id: number | null
  squadriglia: string | null
  titolo: string
  descrizione: string
  dal: string
  al: string | null
  posti: PostoAzione[]
  /** Reparto and Alta Squadriglia: the Consiglio d'impresa (DEC-187). */
  consiglio: { id: number; nome: string }[]
  puo_modificare: boolean
  puo_gestire_posti: boolean
}

export interface ImpreseReparto {
  reparto_id: number
  reparto: string
  imprese: ImpresaEG[]
  squadriglie: {
    id: number
    nome: string
    competenze: Competenza[]
    individuali: { id: number; testo: string }[]
  }[]
  ragazzi: { id: number; nome: string }[]
  puo_gestire: boolean
  /** The staff, or a CSQ for their patrol's imprese. */
  puo_creare: boolean
  sedi: Scelta[]
}

export interface SchedaProgressione {
  persona_id: number
  persona: string
  periodi: PeriodoBranca[]
  mete: MetaEG[]
  impegni: ImpegnoEG[]
  competenze: Competenza[]
  posti_azione: PostoAzione[]
  punti_strada: PuntoStrada[]
  puo_gestire: boolean
  puo_proporre: boolean
  puo_proporre_verifica: boolean
  sedi: Scelta[]
  tipi_conclusione: Scelta[]
  // L/C (DEC-66, DEC-184, DEC-185).
  ambiente: 'GIUNGLA' | 'BOSCO' | null
  stagioni: { id: number; nome: string; stato: StatoStagione }[]
  piccole_orme: { evento: string; inizio: string; fine: string; stato: string }[]
  puo_scrivere_voce: boolean
}

export interface RagazzoSentiero {
  persona_id: number
  persona: string
  sentiero_aperto: boolean
  tappa: string | null
  tappa_dal: DataParziale | null
  distintivo: boolean
  promessa: boolean
  impegni_in_corso: number
  impegni_da_verificare: number
  bozze: number
  mete_aperte: number
  specialita: number
  brevetto: string | null
}

export interface SentieroUnita {
  unita: string
  branca: string
  ragazzi: RagazzoSentiero[]
  puo_gestire: boolean
}

/** Paths of the writes that may wait in the offline queue (DEC-95). */
export const percorsoNuovoImpegno = (persona: number) =>
  `/api/v1/persone/${persona}/progressione/impegni`
export const percorsoAzione = (tipo: 'mete' | 'impegni', id: number, azione: AzionePercorso) =>
  `/api/v1/progressione/${tipo}/${id}/${azione}`

export const percorsoAzioneCompetenza = (id: number, azione: AzioneCompetenza) =>
  `/api/v1/competenze/${id}/${azione}`

const MESI = [
  'gennaio',
  'febbraio',
  'marzo',
  'aprile',
  'maggio',
  'giugno',
  'luglio',
  'agosto',
  'settembre',
  'ottobre',
  'novembre',
  'dicembre',
]

/** "il 12/03/2025", "a marzo 2025", "nel 2025": a partial date after a verb. */
export function quandoParziale(d: DataParziale | null): string {
  if (!d?.data) return d ? '(data non documentata)' : ''
  const [anno, mese] = d.data.split('-')
  if (d.precisione === 'ANNO') return `nel ${anno}`
  if (d.precisione === 'MESE') return `a ${MESI[Number(mese) - 1]} ${anno}`
  return `il ${testoDataParziale(d)}`
}

/** A partial date as Italians read it: 12/03/2025, 03/2025, 2025 (DEC-70). */
export function testoDataParziale(d: DataParziale | null): string {
  if (!d?.data) return d ? 'data non documentata' : ''
  const [anno, mese, giorno] = d.data.split('-')
  if (d.precisione === 'ANNO') return anno!
  if (d.precisione === 'MESE') return `${mese}/${anno}`
  return `${giorno}/${mese}/${anno}`
}

const bc = (iscrizione: number, resto = '') =>
  `/api/v1/buonacaccia/iscrizioni/${iscrizione}${resto}`
export const fileLiberatoria = (iscrizione: number) => bc(iscrizione, '/liberatoria')
export const fileLiberatoriaFirmata = (iscrizione: number) => bc(iscrizione, '/liberatoria-firmata')
export const fileFotoBC = (iscrizione: number) => bc(iscrizione, '/foto')
export const fileFormazione = (anno: number) => `/api/v1/buonacaccia/formazione.xlsx?anno=${anno}`

export const PERCORSO_MOVIMENTI = '/api/v1/movimenti'
export const PERCORSO_SPESE_ANTICIPATE = '/api/v1/spese-anticipate'
export const giustificativoMovimento = (id: number) => `/api/v1/movimenti/${id}/giustificativo`
export const giustificativoSpesa = (id: number) => `/api/v1/spese-anticipate/${id}/giustificativo`

export const PERCORSO_PAGAMENTI = '/api/v1/pagamenti'
export const ricevutaPdf = (pagamento: number) => `/api/v1/pagamenti/${pagamento}/ricevuta.pdf`
export const moduloSanitarioPdf = (persona: number) =>
  `/api/v1/persone/${persona}/sanitarie/modulo.pdf`
export const schedeSanitarieEventoPdf = (evento: number) =>
  `/api/v1/eventi/${evento}/schede-sanitarie.pdf`

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
  cartaSanitaria: (
    persona: number,
    dati: { firmata_il: string | null; prescrizione_consegnata_il: string | null },
  ) =>
    richiesta<Sanitarie>(`/api/v1/persone/${persona}/sanitarie/carta`, {
      metodo: 'PUT',
      corpo: dati,
    }),
  reperibilitaEvento: (evento: number, persona: number) =>
    richiesta<{ nome: string; telefono: string } | null>(
      `/api/v1/eventi/${evento}/reperibilita/${persona}`,
    ),
  salvaReperibilitaEvento: (evento: number, persona: number, nome: string, telefono: string) =>
    richiesta<{ nome: string; telefono: string } | null>(
      `/api/v1/eventi/${evento}/reperibilita/${persona}`,
      { metodo: 'PUT', corpo: { nome, telefono } },
    ),
  note: (persona: number) => richiesta<NoteSchede>(percorsoNote(persona)),
  regoleRapporto: (persona: number, testo: string) =>
    richiesta<NoteSchede>(`/api/v1/persone/${persona}/regole-rapporto`, {
      metodo: 'PUT',
      corpo: { testo },
    }),
  intestazione: () => richiesta<Intestazione>('/api/v1/gruppo/intestazione'),
  salvaIntestazione: (dati: Intestazione) =>
    richiesta<Intestazione>('/api/v1/gruppo/intestazione', { metodo: 'PUT', corpo: dati }),
  caricaLogo: (file: File) => {
    const corpo = new FormData()
    corpo.append('file', file)
    return richiesta<Intestazione>('/api/v1/gruppo/logo', { metodo: 'POST', corpo })
  },
  togliLogo: () => richiesta<Intestazione>('/api/v1/gruppo/logo', { metodo: 'DELETE' }),
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
  eventi: (filtri: { dal?: string; al?: string; unita?: number } = {}) => {
    const parametri = new URLSearchParams(
      Object.entries(filtri)
        .filter(([, v]) => v !== undefined)
        .map(([k, v]) => [k, String(v)]),
    )
    return richiesta<Evento[]>(`/api/v1/eventi?${parametri}`)
  },
  evento: (id: number) => richiesta<DettaglioEvento>(`/api/v1/eventi/${id}`),
  creaEvento: (dati: EventoIn) =>
    richiesta<Evento>('/api/v1/eventi', { metodo: 'POST', corpo: dati }),
  modificaEvento: (id: number, dati: EventoIn) =>
    richiesta<Evento>(`/api/v1/eventi/${id}`, { metodo: 'PUT', corpo: dati }),
  annullaEvento: (id: number, motivo: string) =>
    richiesta<Evento>(`/api/v1/eventi/${id}/annulla`, { metodo: 'POST', corpo: { motivo } }),
  partecipa: (evento: number, persona: number, partecipa: boolean) =>
    richiesta<Evento>(`/api/v1/eventi/${evento}/partecipanti/${persona}/partecipa`, {
      metodo: 'POST',
      corpo: { partecipa },
    }),
  nonInvitare: (evento: number, persona: number, motivo: string) =>
    richiesta<DettaglioEvento>(`/api/v1/eventi/${evento}/partecipanti/${persona}/non-invitare`, {
      metodo: 'POST',
      corpo: { motivo },
    }),
  reinvita: (evento: number, persona: number) =>
    richiesta<DettaglioEvento>(`/api/v1/eventi/${evento}/partecipanti/${persona}/reinvita`, {
      metodo: 'POST',
    }),
  riunioni: (unita: number) => richiesta<RiunioneRicorrente[]>(`/api/v1/unita/${unita}/riunioni`),
  creaRiunioni: (unita: number, dati: Omit<RiunioneRicorrente, 'id' | 'riunioni'>) =>
    richiesta<RiunioneRicorrente>(`/api/v1/unita/${unita}/riunioni`, {
      metodo: 'POST',
      corpo: dati,
    }),
  togliRiunioni: (id: number) =>
    richiesta<RiunioneRicorrente>(`/api/v1/riunioni/${id}`, { metodo: 'DELETE' }),
  fissaQuotaEvento: (
    evento: number,
    dati: { nome: string; rate: RataEvento[]; sconto_famiglia: string },
  ) => richiesta<Evento>(`/api/v1/eventi/${evento}/quota`, { metodo: 'PUT', corpo: dati }),
  rendicontoEvento: (evento: number) =>
    richiesta<RendicontoEvento>(`/api/v1/eventi/${evento}/rendiconto`),
  fissaBudget: (
    evento: number,
    dati: {
      quota: string | null
      contributo: string | null
      totale: string | null
      quota_staff: string
    },
  ) =>
    richiesta<RendicontoEvento>(`/api/v1/eventi/${evento}/budget`, {
      metodo: 'PUT',
      corpo: dati,
    }),
  quoteEvento: (evento: number) =>
    richiesta<SituazioneQuoteEvento[]>(`/api/v1/eventi/${evento}/quote`),
  importoPartecipante: (evento: number, quota: number, importo: string) =>
    richiesta<QuotaPartecipante>(`/api/v1/eventi/${evento}/quote/${quota}`, {
      metodo: 'PUT',
      corpo: { importo },
    }),
  preferenzeEmail: () => richiesta<PreferenzeEmail>('/api/v1/io/email'),
  scegliPreferenzeEmail: (dati: PreferenzeEmail) =>
    richiesta<PreferenzeEmail>('/api/v1/io/email', { metodo: 'PUT', corpo: dati }),
  calendario: () => richiesta<Calendario>('/api/v1/calendario'),
  rigeneraCalendario: () =>
    richiesta<Calendario>('/api/v1/calendario/rigenera', { metodo: 'POST' }),
  fuoriPrimaNota: () =>
    richiesta<{ pagamenti: number; importo: string }>('/api/v1/pagamenti-fuori-prima-nota'),
  riportaInPrimaNota: (cassa_id: number | null) =>
    richiesta<{ riportati: number }>('/api/v1/pagamenti-fuori-prima-nota', {
      metodo: 'POST',
      corpo: { cassa_id },
    }),
  delega: (squadriglia: number) => richiesta<Delega>(`/api/v1/squadriglie/${squadriglia}/delega`),
  delegaA: (squadriglia: number, persona_id: number) =>
    richiesta<Delega>(`/api/v1/squadriglie/${squadriglia}/delega`, {
      metodo: 'PUT',
      corpo: { persona_id },
    }),
  revocaDelega: (squadriglia: number) =>
    richiesta<Delega>(`/api/v1/squadriglie/${squadriglia}/delega`, { metodo: 'DELETE' }),
  altaSquadriglia: (reparto: number) =>
    richiesta<AltaSquadriglia>(`/api/v1/unita/${reparto}/alta-squadriglia`),
  scegliAltaSquadriglia: (reparto: number, anno: number, persone: number[]) =>
    richiesta<AltaSquadriglia>(`/api/v1/unita/${reparto}/alta-squadriglia`, {
      metodo: 'PUT',
      corpo: { anno, persone },
    }),
  vociModelloD: () => richiesta<VoceModelloD[]>('/api/v1/voci-modello-d'),
  casse: () => richiesta<Cassa[]>('/api/v1/casse'),
  creaCassa: (dati: CassaIn) => richiesta<Cassa>('/api/v1/casse', { metodo: 'POST', corpo: dati }),
  modificaCassa: (id: number, dati: CassaIn) =>
    richiesta<Cassa>(`/api/v1/casse/${id}`, { metodo: 'PUT', corpo: dati }),
  movimenti: (filtri: { cassa?: number; anno?: number; unita?: number } = {}) => {
    const parametri = new URLSearchParams(
      Object.entries(filtri)
        .filter(([, v]) => v !== undefined)
        .map(([k, v]) => [k, String(v)]),
    )
    return richiesta<Movimento[]>(`/api/v1/movimenti?${parametri}`)
  },
  storna: (id: number, motivo: string) =>
    richiesta<Movimento>(`/api/v1/movimenti/${id}/storno`, { metodo: 'POST', corpo: { motivo } }),
  aggiungiGiustificativo: (id: number, giustificativo: string) =>
    richiesta<Movimento>(`/api/v1/movimenti/${id}/giustificativo`, {
      metodo: 'POST',
      corpo: { giustificativo },
    }),
  verifiche: (cassa: number) => richiesta<Verifica[]>(`/api/v1/casse/${cassa}/verifiche`),
  verificaCassa: (cassa: number, dati: { data: string; saldo_contato: string; motivo: string }) =>
    richiesta<Verifica>(`/api/v1/casse/${cassa}/verifiche`, { metodo: 'POST', corpo: dati }),
  speseAnticipate: () => richiesta<SpesaAnticipata[]>('/api/v1/spese-anticipate'),
  rimborsaSpesa: (id: number, cassa_id: number) =>
    richiesta<SpesaAnticipata>(`/api/v1/spese-anticipate/${id}/rimborsa`, {
      metodo: 'POST',
      corpo: { cassa_id },
    }),
  respingiSpesa: (id: number, motivo: string) =>
    richiesta<SpesaAnticipata>(`/api/v1/spese-anticipate/${id}/respingi`, {
      metodo: 'POST',
      corpo: { motivo },
    }),
  modelloD: (anno?: number) =>
    richiesta<ModelloD>(`/api/v1/modello-d${anno ? `?anno=${anno}` : ''}`),
  cercaEventiBC: (cerca: string) =>
    richiesta<EventoBCTrovato[]>(`/api/v1/buonacaccia/eventi?cerca=${encodeURIComponent(cerca)}`),
  creaEventoBC: (dati: EventoBCIn) =>
    richiesta<EventoBCTrovato>('/api/v1/buonacaccia/eventi', { metodo: 'POST', corpo: dati }),
  modificaEventoBC: (id: number, dati: EventoBCIn) =>
    richiesta<EventoBCTrovato>(`/api/v1/buonacaccia/eventi/${id}`, { metodo: 'PUT', corpo: dati }),
  eventoBC: (id: number) => richiesta<DettaglioBC>(`/api/v1/buonacaccia/eventi/${id}`),
  schedaEventoBC: (id: number, versione_id: number | null) =>
    richiesta<DettaglioBC>(`/api/v1/buonacaccia/eventi/${id}/scheda`, {
      metodo: 'PUT',
      corpo: { versione_id },
    }),
  partecipanteBC: (
    evento: number,
    dati: { persona_id: number; partecipa: boolean; quota_versata: string | null },
  ) =>
    richiesta<DettaglioBC>(`/api/v1/buonacaccia/eventi/${evento}/partecipanti`, {
      metodo: 'PUT',
      corpo: dati,
    }),
  iscriviBC: (evento: number, dati: IscrizioneBCIn) =>
    richiesta<IscrizioneBC>(`/api/v1/buonacaccia/eventi/${evento}/iscrizioni`, {
      metodo: 'POST',
      corpo: dati,
    }),
  iscrizioniBC: (tutte = false) =>
    richiesta<IscrizioneBC[]>(`/api/v1/buonacaccia/iscrizioni${tutte ? '?tutte=true' : ''}`),
  aggiornaIscrizioneBC: (
    id: number,
    dati: Partial<{
      iscritto_il: string
      stato: StatoIscrizioneBC
      link_gestione: string
      modo_liberatoria: ModoLiberatoria
      scadenza_liberatoria: string | null
      scadenza_liberatoria_predefinita: boolean
    }>,
  ) => richiesta<IscrizioneBC>(bc(id), { metodo: 'PUT', corpo: dati }),
  chiudiIscrizioneBC: (id: number, stato: 'CANCELLATA' | 'NON_AMMESSO', il: string) =>
    richiesta<IscrizioneBC>(bc(id, '/chiudi'), { metodo: 'POST', corpo: { stato, il } }),
  quotaIscrizioneBC: (id: number, importo: string, scadenza: string) =>
    richiesta<IscrizioneBC>(bc(id, '/quota'), { metodo: 'PUT', corpo: { importo, scadenza } }),
  togliQuotaBC: (id: number) => richiesta<IscrizioneBC>(bc(id, '/togli-quota'), { metodo: 'POST' }),
  passiBC: (id: number, passi: PassiBC) =>
    richiesta<IscrizioneBC>(bc(id, '/passi'), { metodo: 'PUT', corpo: passi }),
  esitoLiberatoriaBC: (id: number, esito: 'VALIDATA' | 'RIGETTATA', motivo = '') =>
    richiesta<IscrizioneBC>(bc(id, '/esito-liberatoria'), {
      metodo: 'POST',
      corpo: { esito, motivo },
    }),
  caricaLiberatoriaBC: (id: number, file: File) =>
    richiesta<IscrizioneBC>(bc(id, '/liberatoria'), { metodo: 'POST', corpo: conFile({}, file) }),
  caricaLiberatoriaFirmataBC: (id: number, file: File) =>
    richiesta<IscrizioneBC>(bc(id, '/liberatoria-firmata'), {
      metodo: 'POST',
      corpo: conFile({}, file),
    }),
  risposteBC: (id: number, risposte: Record<string, RispostaScheda>) =>
    richiesta<IscrizioneBC>(bc(id, '/risposte'), { metodo: 'PUT', corpo: { risposte } }),
  caricaFotoBC: (id: number, file: File) =>
    richiesta<IscrizioneBC>(bc(id, '/foto'), { metodo: 'POST', corpo: conFile({}, file) }),
  usaFotoProfiloBC: (id: number) =>
    richiesta<IscrizioneBC>(bc(id, '/foto-profilo'), { metodo: 'POST' }),
  caricaFotoProfilo: (persona: number, file: Blob) => {
    const corpo = new FormData()
    corpo.append('file', file, 'foto.jpg')
    return richiesta<PersonaDettaglio>(fotoProfilo(persona), { metodo: 'POST', corpo })
  },
  caricaAllegatoPP: (tipo: TipoVoceAllegato, voce: number, titolo: string, file: File) =>
    richiesta<SchedaProgressione>(`/api/v1/allegati-pp/${tipo}/${voce}`, {
      metodo: 'POST',
      corpo: conFile({ titolo }, file),
    }),
  togliAllegatoPP: (id: number) =>
    richiesta<SchedaProgressione>(allegatoPP(id), { metodo: 'DELETE' }),
  anniGruppo: () => richiesta<AnniGruppo>('/api/v1/gruppo/anni'),
  chiudiAnno: (anno: number) =>
    richiesta<AnniGruppo>(`/api/v1/gruppo/anni/${anno}/chiudi`, { metodo: 'POST' }),
  riapriAnno: (anno: number, fino_al: string, motivo: string) =>
    richiesta<AnniGruppo>(`/api/v1/gruppo/anni/${anno}/riapri`, {
      metodo: 'POST',
      corpo: { fino_al, motivo },
    }),
  archivio: () => richiesta<ArchivioGruppo>('/api/v1/archivio'),
  archivia: (persona: number) =>
    richiesta<ArchivioGruppo>(`/api/v1/archivio/${persona}`, { metodo: 'POST' }),
  importaTrasferimento: (file: File) =>
    richiesta<EsitoImportazione>('/api/v1/trasferimenti', {
      metodo: 'POST',
      corpo: conFile({}, file),
    }),
  fascicoloCapo: (persona: number) =>
    richiesta<FascicoloCapo>(`/api/v1/persone/${persona}/fascicolo-capo`),
  nuovoServizioPassato: (persona: number, dati: ServizioPassatoIn) =>
    richiesta<FascicoloCapo>(`/api/v1/persone/${persona}/fascicolo-capo/servizi`, {
      metodo: 'POST',
      corpo: dati,
    }),
  togliServizioPassato: (id: number) =>
    richiesta<FascicoloCapo>(`/api/v1/servizi-passati/${id}`, { metodo: 'DELETE' }),
  nuovaFormazione: (persona: number, dati: FormazioneIn) =>
    richiesta<FascicoloCapo>(`/api/v1/persone/${persona}/fascicolo-capo/formazione`, {
      metodo: 'POST',
      corpo: dati,
    }),
  modificaFormazione: (id: number, dati: FormazioneIn) =>
    richiesta<FascicoloCapo>(`/api/v1/formazione-capi/${id}`, { metodo: 'PUT', corpo: dati }),
  togliFormazione: (id: number) =>
    richiesta<FascicoloCapo>(`/api/v1/formazione-capi/${id}`, { metodo: 'DELETE' }),
  fascicoloAnno: (persona: number, anno?: number) =>
    richiesta<FascicoloAnno>(
      `/api/v1/persone/${persona}/fascicolo-anno${anno ? `?anno=${anno}` : ''}`,
    ),
  presentazioneBC: (id: number, testo: string) =>
    richiesta<IscrizioneBC>(bc(id, '/presentazione'), { metodo: 'PUT', corpo: { testo } }),
  riepilogoBC: (id: number) => richiesta<RiepilogoBC>(bc(id, '/riepilogo')),
  schedeBC: () => richiesta<SchedaBC[]>('/api/v1/buonacaccia/schede'),
  creaSchedaBC: (dati: { nome: string; domande: Domanda[] }) =>
    richiesta<SchedaBC>('/api/v1/buonacaccia/schede', { metodo: 'POST', corpo: dati }),
  nuovaVersioneSchedaBC: (id: number, dati: { nome: string; domande: Domanda[] }) =>
    richiesta<SchedaBC>(`/api/v1/buonacaccia/schede/${id}`, { metodo: 'PUT', corpo: dati }),
  formazioneCapi: (anno: number) =>
    richiesta<FormazioneCapo[]>(`/api/v1/buonacaccia/formazione?anno=${anno}`),
  candidatiImpersonazione: (cerca: string) =>
    richiesta<CandidatoImpersonazione[]>(
      `/api/v1/impersonazione/candidati?cerca=${encodeURIComponent(cerca)}`,
    ),
  impersonabile: (persona: number) =>
    richiesta<{ puo: boolean }>(`/api/v1/persone/${persona}/impersonabile`),
  iniziaImpersonazione: (dati: { utente_id?: number; persona_id?: number; motivo: string }) =>
    richiesta<Impersonazione>('/api/v1/impersonazione', { metodo: 'POST', corpo: dati }),
  fineImpersonazione: () =>
    richiesta<{ ok: boolean }>('/api/v1/impersonazione/fine', { metodo: 'POST' }),
  impersonazioniMie: () => richiesta<Impersonazione[]>('/api/v1/impersonazioni/mie'),
  impersonazioni: () => richiesta<Impersonazione[]>('/api/v1/impersonazioni'),
  progressione: (persona: number) =>
    richiesta<SchedaProgressione>(`/api/v1/persone/${persona}/progressione`),
  apriSentiero: (persona: number, quando: DataParziale) =>
    richiesta<SchedaProgressione>(`/api/v1/persone/${persona}/progressione/sentiero`, {
      metodo: 'POST',
      corpo: quando,
    }),
  promessa: (periodo: number, quando: DataParziale) =>
    richiesta<SchedaProgressione>(`/api/v1/progressione/periodi/${periodo}/promessa`, {
      metodo: 'POST',
      corpo: quando,
    }),
  rettificaPromessa: (periodo: number, quando: DataParziale, motivo: string) =>
    richiesta<SchedaProgressione>(`/api/v1/progressione/periodi/${periodo}/promessa`, {
      metodo: 'PUT',
      corpo: { ...quando, motivo },
    }),
  firmaCarta: (periodo: number, quando: DataParziale) =>
    richiesta<SchedaProgressione>(`/api/v1/progressione/periodi/${periodo}/carta`, {
      metodo: 'POST',
      corpo: quando,
    }),
  rettificaCarta: (periodo: number, quando: DataParziale, motivo: string) =>
    richiesta<SchedaProgressione>(`/api/v1/progressione/periodi/${periodo}/carta`, {
      metodo: 'PUT',
      corpo: { ...quando, motivo },
    }),
  avviaResponsabilita: (tappa: number, quando: DataParziale) =>
    richiesta<SchedaProgressione>(`/api/v1/progressione/tappe/${tappa}/responsabilita`, {
      metodo: 'POST',
      corpo: quando,
    }),
  concludi: (periodo: number, dati: DataParziale & { tipo: TipoConclusione; nota: string }) =>
    richiesta<SchedaProgressione>(`/api/v1/progressione/periodi/${periodo}/conclusione`, {
      metodo: 'POST',
      corpo: dati,
    }),
  nuovoPuntoStrada: (periodo: number, dati: PuntoStradaIn) =>
    richiesta<SchedaProgressione>(`/api/v1/progressione/periodi/${periodo}/punti-strada`, {
      metodo: 'POST',
      corpo: dati,
    }),
  vocePuntoStrada: (id: number, testo: string) =>
    richiesta<SchedaProgressione>(`/api/v1/punti-strada/${id}/voce`, {
      metodo: 'PUT',
      corpo: { testo },
    }),
  consiglioImpresa: (impresa: number, persone: number[]) =>
    richiesta<ImpreseReparto>(`/api/v1/imprese/${impresa}/consiglio`, {
      metodo: 'PUT',
      corpo: { persone },
    }),
  modificaPuntoStrada: (id: number, dati: PuntoStradaIn) =>
    richiesta<SchedaProgressione>(`/api/v1/punti-strada/${id}`, { metodo: 'PUT', corpo: dati }),
  riconosciTappa: (tappa: number, quando: DataParziale, storico = false) =>
    richiesta<SchedaProgressione>(`/api/v1/progressione/tappe/${tappa}/riconosci`, {
      metodo: 'POST',
      corpo: { ...quando, storico },
    }),
  stagioni: (unita: number) => richiesta<StagioniUnita>(`/api/v1/unita/${unita}/stagioni`),
  nuovaStagione: (unita: number, dati: StagioneIn) =>
    richiesta<StagioniUnita>(`/api/v1/unita/${unita}/stagioni`, { metodo: 'POST', corpo: dati }),
  modificaStagione: (id: number, dati: StagioneIn) =>
    richiesta<StagioniUnita>(`/api/v1/stagioni/${id}`, { metodo: 'PUT', corpo: dati }),
  passoStagione: (id: number, azione: 'lancia' | 'chiudi' | 'annulla', il: string | null) =>
    richiesta<StagioniUnita>(`/api/v1/stagioni/${id}/${azione}`, {
      metodo: 'POST',
      corpo: { il },
    }),
  collocaTappa: (
    tappa: number,
    dati: DataParziale & { fase: FaseProgressione; motivazione: string },
  ) =>
    richiesta<SchedaProgressione>(`/api/v1/progressione/tappe/${tappa}/colloca`, {
      metodo: 'POST',
      corpo: dati,
    }),
  distintivoTappa: (tappa: number, quando: DataParziale) =>
    richiesta<SchedaProgressione>(`/api/v1/progressione/tappe/${tappa}/distintivo`, {
      metodo: 'POST',
      corpo: quando,
    }),
  rettificaTappa: (
    tappa: number,
    campo: 'inizio' | 'completata' | 'distintivo',
    quando: DataParziale,
    motivo: string,
  ) =>
    richiesta<SchedaProgressione>(`/api/v1/progressione/tappe/${tappa}`, {
      metodo: 'PUT',
      corpo: { ...quando, campo, motivo },
    }),
  nuovaMeta: (
    persona: number,
    dati: { testo: string; termine: string | null; riservata: boolean },
  ) =>
    richiesta<SchedaProgressione>(`/api/v1/persone/${persona}/progressione/mete`, {
      metodo: 'POST',
      corpo: dati,
    }),
  riformula: (
    tipo: 'mete' | 'impegni',
    id: number,
    dati: {
      testo: string
      termine: string | null
      criterio_verifica?: string
      riservata?: boolean
      mete?: number[]
    },
  ) =>
    richiesta<SchedaProgressione>(`/api/v1/progressione/${tipo}/${id}`, {
      metodo: 'PUT',
      corpo: dati,
    }),
  sentieroUnita: (unita: number) => richiesta<SentieroUnita>(`/api/v1/unita/${unita}/progressione`),
  cataloghiPP: () => richiesta<CataloghiPP>('/api/v1/progressione/cataloghi'),
  nuovaCompetenza: (
    persona: number,
    dati: {
      tipo: TipoCompetenza
      codice: string
      carta: string
      maestro: string
      conquistata: DataParziale | null
    },
  ) =>
    richiesta<SchedaProgressione>(`/api/v1/persone/${persona}/progressione/competenze`, {
      metodo: 'POST',
      corpo: dati,
    }),
  modificaCompetenza: (
    id: number,
    dati: { carta: string; maestro: string; confronto: string; collegati: number[] },
  ) => richiesta<unknown>(`/api/v1/competenze/${id}`, { metodo: 'PUT', corpo: dati }),
  distintivoCompetenza: (id: number, quando: DataParziale) =>
    richiesta<unknown>(`/api/v1/competenze/${id}/distintivo`, { metodo: 'POST', corpo: quando }),
  impreseReparto: (unita: number) => richiesta<ImpreseReparto>(`/api/v1/unita/${unita}/imprese`),
  nuovaImpresa: (
    unita: number,
    dati: {
      livello: LivelloImpresa
      squadriglia_id: number | null
      titolo: string
      descrizione: string
      dal: string
      al: string | null
    },
  ) => richiesta<ImpreseReparto>(`/api/v1/unita/${unita}/imprese`, { metodo: 'POST', corpo: dati }),
  nuovoPosto: (impresa: number, dati: { persona_id: number; ruolo: string }) =>
    richiesta<ImpreseReparto>(`/api/v1/imprese/${impresa}/posti`, { metodo: 'POST', corpo: dati }),
  verificaPosto: (posto: number, dati: { il: string; sede: string; sede_descrizione: string }) =>
    richiesta<ImpreseReparto>(`/api/v1/posti-azione/${posto}/verifica`, {
      metodo: 'POST',
      corpo: dati,
    }),
  nuovaSpecialitaSquadriglia: (
    squadriglia: number,
    dati: { codice: string; carta: string; conquistata: DataParziale | null },
  ) =>
    richiesta<ImpreseReparto>(`/api/v1/squadriglie/${squadriglia}/competenze`, {
      metodo: 'POST',
      corpo: dati,
    }),
  passaggiUnita: (unita: number) => richiesta<PassaggiUnita>(`/api/v1/unita/${unita}/passaggi`),
  preparaPassaggio: (unita: number, dati: PassaggioIn) =>
    richiesta<PassaggiUnita>(`/api/v1/unita/${unita}/passaggi`, { metodo: 'POST', corpo: dati }),
  modificaPassaggio: (id: number, dati: PassaggioIn) =>
    richiesta<PassaggiUnita>(`/api/v1/passaggi/${id}`, { metodo: 'PUT', corpo: dati }),
  eseguiPassaggio: (id: number) =>
    richiesta<PassaggiUnita>(`/api/v1/passaggi/${id}/esegui`, { metodo: 'POST' }),
  annullaEsecuzione: (id: number, motivo: string, persone: number[] | null) =>
    richiesta<PassaggiUnita>(`/api/v1/passaggi/${id}/annulla-esecuzione`, {
      metodo: 'POST',
      corpo: { motivo, persone },
    }),
  correggiDataPassaggio: (id: number, data: string, motivo: string) =>
    richiesta<PassaggiUnita>(`/api/v1/passaggi/${id}/correggi-data`, {
      metodo: 'POST',
      corpo: { data, motivo },
    }),
  annullaPassaggio: (id: number, motivo: string) =>
    richiesta<PassaggiUnita>(`/api/v1/passaggi/${id}/annulla`, {
      metodo: 'POST',
      corpo: { motivo },
    }),
  applicaImportazione: (id: number, scelte: Record<string, Lato>) =>
    richiesta<EsitoImportazione>(`/api/v1/importazioni/${id}/applica`, {
      metodo: 'POST',
      corpo: { scelte },
    }),
}
