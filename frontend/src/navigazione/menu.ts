/**
 * The menu (DEC-241…DEC-243): groups and entries for the side menu, the Home and the
 * breadcrumb, from one list. An entry shows only to who may use it, and a group with
 * no entries disappears. The flags come from the profile: they only hide entries, the
 * server decides what each page shows (DEC-09).
 */
import type { RouteLocationRaw } from 'vue-router'

import type { Profilo } from '@/api/qdc'

import type { NomeIcona } from './icone'

export interface Voce {
  nome: string
  icona: NomeIcona
  /** A page of the app, or an address outside it (the Django admin). */
  to: RouteLocationRaw
  esterna?: boolean
  /** Shown on the Home cards. */
  descrizione?: string
  /** A counter (requests waiting, corrections to forward). */
  contatore?: number
  /** Indented under the entry before it (a section of that page). */
  sottovoce?: boolean
}

export interface Gruppo {
  chiave: string
  titolo: string
  icona: NomeIcona
  voci: Voce[]
}

/** Counters read apart from the profile (online only). */
export interface Contatori {
  correzioni?: number | null
  /** The email test mode is on: the technical administrator gets Mailpit (DEC-249). */
  email_di_prova?: boolean
}

/** Name of the Progressione personale group for a child (DEC-243). */
export function nomeProgressione(profilo: Profilo): string {
  if (profilo.capo) return 'Progressione personale'
  switch (profilo.branca) {
    case 'lc':
      return profilo.ambiente === 'BOSCO' ? 'Il mio Sentiero' : 'La mia Pista'
    case 'eg':
      return 'Il mio Sentiero'
    case 'rs':
      return 'La mia Strada'
    default:
      return 'Progressione personale'
  }
}

const RAGAZZO = new Set(['lc', 'eg', 'rs'])

/** What the child's Progressione holds, in the words of their branch (DEC-185). */
function descrizioneProgressione(p: Profilo): string {
  if (p.branca === 'rs') return 'Passi, obiettivi e impegni'
  if (p.branca === 'lc') {
    return p.ambiente === 'BOSCO'
      ? 'Momenti, voli e specialità'
      : p.ambiente === 'GIUNGLA'
        ? 'Momenti, prede e specialità'
        : 'Momenti, prede o voli e specialità'
  }
  return 'Tappe, mete e impegni'
}

/** The entries that apply: each one is written as `condition && { … }`. */
function solo(voci: (Voce | false | null | undefined | 0)[]): Voce[] {
  return voci.filter((v): v is Voce => !!v)
}

function progressione(p: Profilo): Voce[] {
  const voci: Voce[] = []
  if (p.persona && !p.capo && RAGAZZO.has(p.branca)) {
    voci.push({
      nome: nomeProgressione(p),
      icona: 'compass',
      to: { name: 'sentiero', params: { id: p.persona.id } },
      descrizione: descrizioneProgressione(p),
    })
  }
  if (p.imprese_reparto) {
    voci.push({
      nome: 'Imprese',
      icona: 'flag',
      to: { name: 'imprese', params: { id: p.imprese_reparto } },
      descrizione: "Posti d'azione e verifiche delle imprese che guidi",
    })
  }
  for (const u of p.unita_servizio ?? []) {
    voci.push({
      nome: u.nome,
      icona: 'compass',
      to: { name: 'sentiero-unita', params: { id: u.id } },
      descrizione: "La progressione dell'unità",
    })
    if (u.tipo === 'REPARTO') {
      voci.push({
        nome: 'Imprese',
        icona: 'flag',
        to: { name: 'imprese', params: { id: u.id } },
        sottovoce: true,
      })
    }
    if (u.tipo === 'CLAN_FUOCO') {
      voci.push({
        nome: 'Carta di clan',
        icona: 'file-earmark-text',
        to: { name: 'carta-clan', params: { id: u.id } },
        sottovoce: true,
      })
    }
    voci.push({
      nome: 'Passaggi',
      icona: 'signpost-split',
      to: { name: 'passaggi', params: { id: u.id } },
      sottovoce: true,
    })
  }
  return voci
}

export function gruppiMenu(p: Profilo, contatori: Contatori = {}): Gruppo[] {
  const membro = !!p.persona || p.tutelati.length > 0
  const decide = (p.iscrizioni_da_decidere ?? 0) + (p.iscrizioni_da_verificare ?? 0)
  const gruppi: Gruppo[] = [
    {
      chiave: 'bacheca',
      titolo: 'Bacheca',
      icona: 'megaphone',
      voci: membro
        ? [
            {
              nome: 'Bacheca',
              icona: 'megaphone',
              to: '/bacheca',
              descrizione: 'Avvisi dei capi per la tua unità e per il gruppo',
            },
          ]
        : [],
    },
    {
      chiave: 'famiglia',
      titolo: 'La mia famiglia',
      icona: 'people',
      voci: p.tutelati.map((t) => ({
        nome: `${t.nome} ${t.cognome}`,
        icona: 'person-heart' as const,
        to: { name: 'persona', params: { id: t.id } },
        descrizione: 'Scheda, progressione e fascicolo',
      })),
    },
    {
      chiave: 'gruppo',
      titolo: 'Il mio gruppo',
      icona: 'diagram-3',
      voci: solo([
        p.capo && {
          nome: 'Persone',
          icona: 'person-vcard',
          to: '/persone',
          descrizione: 'Anagrafiche visibili con il tuo ruolo',
        },
        p.capo && {
          nome: 'Unità',
          icona: 'collection',
          to: '/unita',
          descrizione: 'Branchi, cerchi, reparti, clan e Comunità capi',
        },
        (p.capo || p.amministratore_tecnico) && {
          nome: 'Incarichi di gruppo',
          icona: 'person-badge',
          to: '/gruppo',
          descrizione: p.capo
            ? 'Capigruppo, tesorieri, amministratori e capi a disposizione'
            : 'Nomina il primo capogruppo del gruppo',
        },
        (decide > 0 || p.capogruppo || (p.unita_servizio?.length ?? 0) > 0) && {
          nome: 'Richieste di iscrizione',
          icona: 'person-plus',
          to: '/iscrizioni',
          descrizione: 'Nuovi soci da accogliere e moduli da verificare',
          contatore: p.iscrizioni_da_decidere || undefined,
        },
        p.vede_lista_attesa && {
          nome: "Lista d'attesa",
          icona: 'hourglass-split',
          to: '/attesa',
          descrizione: 'Chi vuole entrare nel gruppo, per età e unità consigliata',
        },
        p.capogruppo && {
          nome: 'Modulistica',
          icona: 'file-earmark-text',
          to: '/modulistica',
          descrizione: 'Moduli da firmare per le iscrizioni',
        },
        p.capogruppo && {
          nome: 'Richieste privacy',
          icona: 'shield-lock',
          to: '/diritti',
          descrizione: 'Accesso, copia e cancellazione dei dati',
        },
      ]),
    },
    {
      chiave: 'attivita',
      titolo: 'Attività',
      icona: 'calendar-event',
      voci: solo([
        membro && {
          nome: 'Eventi',
          icona: 'calendar3',
          to: '/eventi',
          descrizione: 'Riunioni, uscite e campi; partecipazione e presenze',
        },
        p.eventi_buonacaccia && {
          nome: 'Eventi su BuonaCaccia',
          icona: 'calendar-event',
          to: '/buonacaccia',
          descrizione: 'Piccole Orme, campetti, formazione: iscrizioni e liberatorie',
          sottovoce: true,
        },
        p.formazione_capi && {
          nome: 'Formazione capi',
          icona: 'award',
          to: '/buonacaccia/formazione',
          descrizione: 'I campi di formazione dei capi, per la Zona',
          sottovoce: true,
        },
        p.capo && {
          nome: 'Al campo',
          icona: 'backpack',
          to: '/campo',
          descrizione: "Contatti, farmaci e allergie dell'unità, anche senza rete",
        },
        p.squadriglie.length > 0 && {
          nome: 'La mia squadriglia',
          icona: 'flag',
          to: '/squadriglia',
          descrizione: 'I numeri di telefono della squadriglia',
        },
      ]),
    },
    {
      chiave: 'progressione',
      titolo: nomeProgressione(p),
      icona: 'compass',
      voci: progressione(p),
    },
    {
      chiave: 'economia',
      titolo: 'Gestione economica',
      icona: 'cash-coin',
      voci: solo([
        (p.gestisce_quote || p.unita_quote.length > 0) && {
          nome: 'Quote',
          icona: 'receipt',
          to: '/quote',
          descrizione: p.gestisce_quote
            ? 'Tipi di quota, emissione e chi ha pagato'
            : 'Chi ha pagato nelle unità',
        },
        ((p.pagamenti_da_verificare ?? 0) > 0 || p.gestisce_quote) && {
          nome: 'Pagamenti da verificare',
          icona: 'check2-square',
          to: '/pagamenti-da-verificare',
          descrizione: 'PayPal e bonifici segnalati dalle famiglie',
          contatore: p.pagamenti_da_verificare || undefined,
        },
        p.vede_cassa && {
          nome: 'Prima nota',
          icona: 'journal-text',
          to: '/cassa',
          descrizione: 'Casse, movimenti, rimborsi e rendiconto',
        },
        p.gestisce_quote && {
          nome: 'Estratto conto',
          icona: 'bank',
          to: '/banca',
          descrizione: 'I movimenti della banca, da abbinare a quote e versamenti',
        },
      ]),
    },
    {
      chiave: 'buonastrada',
      titolo: 'BuonaStrada',
      icona: 'arrow-left-right',
      voci: solo([
        (p.capogruppo || p.amministratore_tecnico) && {
          nome: 'Importa da BuonaStrada',
          icona: 'upload',
          to: '/importazione',
          descrizione: 'Carica l\'export "Ricerca soci" (CSV)',
        },
        p.capogruppo && {
          nome: 'Iscrizioni da inserire',
          icona: 'person-lines-fill',
          to: '/iscrizioni-buonastrada',
          descrizione: 'Nuovi soci completi, da copiare in BuonaStrada',
          contatore: p.iscrizioni_da_inserire || undefined,
        },
        (p.capogruppo || p.amministratore_tecnico) && {
          nome: 'Correzioni da inoltrare',
          icona: 'pencil-square',
          to: '/correzioni',
          descrizione: "Dati corretti nell'app, da mandare alla segreteria",
          contatore: contatori.correzioni || undefined,
        },
      ]),
    },
    {
      chiave: 'amministrazione',
      titolo: 'Amministrazione',
      icona: 'gear',
      voci: solo([
        p.vede_impostazioni && {
          nome: 'Impostazioni',
          icona: 'sliders',
          to: '/impostazioni',
          descrizione: 'Nome e titolo del sito, intestazione delle stampe',
        },
        p.amministratore_tecnico &&
          contatori.email_di_prova && {
            nome: 'Mailpit',
            icona: 'envelope-open',
            to: '/mailpit/',
            esterna: true,
            descrizione: 'Le email trattenute dalla modalità di prova',
          },
        p.amministratore_tecnico && {
          nome: 'Pannello di amministrazione',
          icona: 'tools',
          to: '/admin/',
          esterna: true,
          descrizione: 'Il pannello tecnico di Django',
        },
      ]),
    },
  ]
  return gruppi.filter((g) => g.voci.length > 0)
}

/** The profile menu under the avatar (DEC-242); lock and logout are buttons apart. */
export function vociProfilo(p: Profilo): Voce[] {
  const membro = !!p.persona || p.tutelati.length > 0
  return solo([
    p.persona && {
      nome: 'Il mio profilo',
      icona: 'person-circle',
      to: { name: 'persona', params: { id: p.persona.id } },
      descrizione: 'La tua scheda',
    },
    p.persona && {
      nome: 'Privacy',
      icona: 'shield-check',
      to: '/email',
      descrizione: 'Quali email ricevere e chi vede i tuoi dati',
    },
    {
      nome: 'Password e sicurezza',
      icona: 'key',
      to: '/dispositivi',
      descrizione: 'Password, passkey, dispositivi e protezione del telefono',
    },
    membro && {
      nome: 'Le mie quote',
      icona: 'wallet2',
      to: '/mie-quote',
      descrizione: 'Quote da pagare, pagamenti e ricevute',
    },
    p.capo &&
      !p.capo_in_attesa && {
        nome: 'Le mie spese',
        icona: 'receipt-cutoff',
        to: '/spese',
        descrizione: 'Quello che hai pagato per il gruppo, da farti rimborsare',
      },
    p.mie_iscrizioni > 0 && {
      nome: 'La mia iscrizione',
      icona: 'person-lines-fill',
      to: '/mia-iscrizione',
      descrizione: 'Stato delle richieste, dati e moduli da completare',
    },
    p.puo_impersonare &&
      !p.impersonazione && {
        nome: 'Impersona',
        icona: 'incognito',
        to: '/impersonazioni',
        descrizione: "Usa l'app come un'altra persona, per aiutarla",
      },
  ])
}
