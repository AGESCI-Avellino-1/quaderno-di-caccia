/**
 * The technical data of the Informazioni page (DEC-387), to copy into a report. Reports are
 * public: only what describes the device and the app, never a name, an email, a codice socio,
 * a device id or data of the members. `voci` sees the whole profile and keeps only its kind.
 */
import type { Profilo } from '@/api/qdc'

/** The project's reports, where a group that set no link of its own sends them. */
export const LINK_PROGETTO = 'https://github.com/AGESCI-Avellino-1/quaderno-di-caccia/issues/new'

export interface Voce {
  voce: string
  valore: string
}

export interface Ambiente {
  versioneApp: string
  /** Empty when the server did not answer. */
  versioneServer: string
  installata: boolean
  agente: string
  /** More than 1 on a touch screen: an iPad says it is a Mac. */
  puntiTocco: number
  schermo: { larghezza: number; altezza: number; densita: number }
  lingua: string
  fuso: string
  adesso: Date
  online: boolean
  aggiornamento: 'pronta' | 'sul_server' | 'nessuno'
  stato: 'da_configurare' | 'solo_online' | 'bloccata' | 'sbloccata'
  biometria: 'attivo' | 'supportato' | 'non_disponibile'
  notifiche: 'attive' | 'negate' | 'non_attive' | 'non_supportate'
  inCoda: number
  conErrori: number
  profilo: Profilo | null
}

const MODI: [RegExp, string][] = [
  [/EdgA?\/([\d.]+)/, 'Edge'],
  [/EdgiOS\/([\d.]+)/, 'Edge'],
  [/OPR\/([\d.]+)/, 'Opera'],
  [/SamsungBrowser\/([\d.]+)/, 'Samsung Internet'],
  [/CriOS\/([\d.]+)/, 'Chrome'],
  [/FxiOS\/([\d.]+)/, 'Firefox'],
  [/Firefox\/([\d.]+)/, 'Firefox'],
  [/Chrome\/([\d.]+)/, 'Chrome'],
  [/Version\/([\d.]+).*Safari\//, 'Safari'],
]

export function browserDa(agente: string): string {
  for (const [modo, nome] of MODI) {
    const trovato = modo.exec(agente)
    if (trovato) return `${nome} ${trovato[1]}`
  }
  // An installed app on iOS has no "Version/": it is still Safari's engine.
  if (/AppleWebKit/.test(agente) && /iPhone|iPad|Macintosh/.test(agente)) return 'Safari'
  return 'Non riconosciuto'
}

function sistemaDa(agente: string, puntiTocco: number): string {
  const ios = /(iPhone|iPad)[^)]*OS (\d+(?:_\d+)*)/.exec(agente)
  if (ios) return `${ios[1]}, iOS ${ios[2]!.replace(/_/g, '.')}`
  // Since iPadOS 13 an iPad says it is a Mac; a Mac has no touch screen.
  if (/Macintosh/.test(agente)) return puntiTocco > 1 ? 'iPad' : 'Mac'
  const android = /Android (\d+(?:\.\d+)*)/.exec(agente)
  if (android) return `Android ${android[1]}`
  if (/Windows NT/.test(agente)) return 'Windows'
  if (/Linux/.test(agente)) return 'Linux'
  return 'Non riconosciuto'
}

const AGGIORNAMENTO = {
  pronta: 'Nuova versione pronta',
  sul_server: 'Nuova versione sul server',
  nessuno: 'Nessuno',
}
const PROTEZIONE = {
  da_configurare: 'Da configurare',
  solo_online: 'Solo online',
  bloccata: 'Con PIN, bloccata',
  sbloccata: 'Con PIN, sbloccata',
}
const SBLOCCO = {
  attivo: 'Attivo',
  supportato: 'Supportato, non attivo',
  non_disponibile: 'Non disponibile',
}
const NOTIFICHE = {
  attive: 'Attive',
  negate: 'Permesso negato',
  non_attive: 'Non attive',
  non_supportate: 'Non supportate',
}

function tipoProfilo(profilo: Profilo | null, stato: Ambiente['stato']): string {
  if (stato === 'bloccata') return 'Non noto, app bloccata'
  if (!profilo) return 'Non collegato'
  if (profilo.capogruppo) return 'Capogruppo'
  if (profilo.capo) return 'Capo'
  if (profilo.amministratore_tecnico) return 'Amministratore tecnico'
  if (profilo.tutelati.length) return 'Genitore'
  if (profilo.persona) return 'Ragazzo/a'
  return 'Altro'
}

export function voci(a: Ambiente): Voce[] {
  const inSospeso = a.inCoda + a.conErrori
  const { larghezza, altezza, densita } = a.schermo
  return [
    { voce: "Versione dell'app", valore: `v${a.versioneApp}` },
    { voce: 'Versione del server', valore: a.versioneServer ? `v${a.versioneServer}` : 'Non nota' },
    { voce: 'Modalità', valore: a.installata ? 'App installata' : 'Nel browser' },
    { voce: 'Browser', valore: browserDa(a.agente) },
    {
      voce: 'Dispositivo',
      valore: `${sistemaDa(a.agente, a.puntiTocco)}, schermo ${larghezza}×${altezza} (×${densita})`,
    },
    {
      voce: 'Lingua e ora',
      valore: `${a.lingua}, ${a.fuso}, ${a.adesso.toLocaleString('it-IT')}`,
    },
    { voce: 'Connessione', valore: a.online ? 'In linea' : 'Senza rete' },
    { voce: 'Aggiornamento', valore: AGGIORNAMENTO[a.aggiornamento] },
    { voce: 'Protezione dati', valore: PROTEZIONE[a.stato] },
    { voce: 'Sblocco con impronta o volto', valore: SBLOCCO[a.biometria] },
    { voce: 'Notifiche', valore: NOTIFICHE[a.notifiche] },
    {
      voce: 'Modifiche in sospeso',
      valore: a.conErrori ? `${inSospeso}, di cui ${a.conErrori} con errore` : String(inSospeso),
    },
    { voce: 'Profilo', valore: tipoProfilo(a.profilo, a.stato) },
    // What the lines above come from, for when they read it wrong.
    { voce: 'Dettagli del browser', valore: a.agente },
  ]
}

export function testo(elenco: Voce[]): string {
  return elenco.map((v) => `${v.voce}: ${v.valore}`).join('\n')
}

const PREMESSA = 'Descrivi qui il problema: cosa hai fatto, cosa ti aspettavi, cosa è successo.'

/** An email to the group, private, with the data already in. */
export function linkEmail(email: string, dati: string): string {
  const oggetto = encodeURIComponent('Segnalazione sul Quaderno di Caccia')
  const corpo = encodeURIComponent(`${PREMESSA}\n\n\n--\n${dati}`)
  return `mailto:${email}?subject=${oggetto}&body=${corpo}`
}

/** A new report; GitHub takes the text in the address, another site gets the plain link. */
export function linkSegnalazione(link: string, dati: string): string {
  const indirizzo = new URL(link || LINK_PROGETTO)
  if (indirizzo.hostname === 'github.com' && indirizzo.pathname.endsWith('/issues/new')) {
    indirizzo.searchParams.set('body', `${PREMESSA}\n\n\n---\n${dati}`)
  }
  return indirizzo.toString()
}
