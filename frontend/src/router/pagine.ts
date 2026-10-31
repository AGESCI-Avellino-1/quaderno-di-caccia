/**
 * The name of every page and the page above it: the [Pagina corrente] placeholder of
 * the title (DEC-246) and the breadcrumb (DEC-244). A child route uses the same `id`
 * parameter as its parent (a person's pages under the person, a unit's under the unit).
 * A page with a name of its own (a person, a unit, an event) sets it with `usaPagina`.
 */
export interface Pagina {
  titolo: string
  /** Route name of the page above; none = right under the Home. */
  sopra?: string
}

export const PAGINE: Record<string, Pagina> = {
  home: { titolo: 'Home' },
  accesso: { titolo: 'Accesso' },
  sblocco: { titolo: 'Sblocca' },
  protezione: { titolo: 'Protezione del telefono' },
  invito: { titolo: 'Invito' },
  'verifica-email': { titolo: "Conferma dell'email" },
  'reimposta-password': { titolo: 'Nuova password' },
  persone: { titolo: 'Persone' },
  persona: { titolo: 'Scheda', sopra: 'persone' },
  sanitarie: { titolo: 'Scheda sanitaria', sopra: 'persona' },
  fascicolo: { titolo: 'Fascicolo completo', sopra: 'persona' },
  'fascicolo-capo': { titolo: 'Fascicolo del capo', sopra: 'persona' },
  'fascicolo-anno': { titolo: "Fascicolo dell'anno", sopra: 'persona' },
  sentiero: { titolo: 'Progressione personale', sopra: 'persona' },
  campo: { titolo: 'Al campo' },
  unita: { titolo: 'Unità' },
  'unita-dettaglio': { titolo: 'Unità', sopra: 'unita' },
  'carta-clan': { titolo: 'Carta di clan', sopra: 'unita-dettaglio' },
  'sentiero-unita': { titolo: "Progressione dell'unità", sopra: 'unita-dettaglio' },
  imprese: { titolo: 'Imprese', sopra: 'unita-dettaglio' },
  passaggi: { titolo: 'Passaggi', sopra: 'unita-dettaglio' },
  gruppo: { titolo: 'Incarichi di gruppo' },
  iscrizione: { titolo: 'Iscrizione' },
  'mia-iscrizione': { titolo: 'La mia iscrizione' },
  'iscrizioni-buonastrada': { titolo: 'Iscrizioni da inserire in BuonaStrada' },
  modulistica: { titolo: 'Modulistica' },
  iscrizioni: { titolo: 'Richieste di iscrizione' },
  diritti: { titolo: 'Richieste privacy' },
  squadriglia: { titolo: 'La mia squadriglia' },
  correzioni: { titolo: 'Correzioni da inoltrare' },
  quote: { titolo: 'Quote' },
  banca: { titolo: 'Estratto conto' },
  'pagamenti-da-verificare': { titolo: 'Pagamenti da verificare' },
  bacheca: { titolo: 'Bacheca' },
  'mie-quote': { titolo: 'Le mie quote' },
  eventi: { titolo: 'Eventi' },
  evento: { titolo: 'Evento', sopra: 'eventi' },
  buonacaccia: { titolo: 'Eventi su BuonaCaccia', sopra: 'eventi' },
  'schede-buonacaccia': { titolo: 'Schede degli eventi', sopra: 'buonacaccia' },
  'formazione-capi': { titolo: 'Formazione capi', sopra: 'buonacaccia' },
  impersonazioni: { titolo: 'Impersona' },
  cassa: { titolo: 'Prima nota' },
  spese: { titolo: 'Le mie spese' },
  email: { titolo: 'Privacy' },
  importazione: { titolo: 'Importa da BuonaStrada' },
  dispositivi: { titolo: 'Password e sicurezza' },
  modifiche: { titolo: 'Modifiche da inviare' },
  impostazioni: { titolo: 'Impostazioni' },
  'modello-email': { titolo: 'Modello di email', sopra: 'impostazioni' },
  'non-trovata': { titolo: 'Pagina non trovata' },
}
