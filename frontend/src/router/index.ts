import { createRouter, createWebHistory } from 'vue-router'

import * as cassaforte from '@/sicurezza/cassaforte'
import { controllaRevoca } from '@/sicurezza/dispositivo'
import { useSessioneStore } from '@/stores/sessione'

declare module 'vue-router' {
  interface RouteMeta {
    /** Reachable without login. */
    pubblica?: boolean
    /** Menu guard only: the API enforces the real permission. */
    richiede?: 'capo' | 'importazione'
  }
}

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    { path: '/', name: 'home', component: () => import('@/views/HomeView.vue') },
    {
      path: '/accesso',
      name: 'accesso',
      component: () => import('@/views/AccessoView.vue'),
      meta: { pubblica: true },
    },
    {
      path: '/sblocco',
      name: 'sblocco',
      component: () => import('@/views/SbloccoView.vue'),
      meta: { pubblica: true },
    },
    {
      path: '/protezione',
      name: 'protezione',
      component: () => import('@/views/ProtezioneView.vue'),
    },
    {
      path: '/invito/:token',
      name: 'invito',
      component: () => import('@/views/InvitoView.vue'),
      meta: { pubblica: true },
      props: true,
    },
    {
      path: '/account/verifica-email/:chiave',
      name: 'verifica-email',
      component: () => import('@/views/VerificaEmailView.vue'),
      meta: { pubblica: true },
      props: true,
    },
    {
      path: '/account/reimposta-password/:chiave?',
      name: 'reimposta-password',
      component: () => import('@/views/ReimpostaPasswordView.vue'),
      meta: { pubblica: true },
      props: true,
    },
    { path: '/persone', name: 'persone', component: () => import('@/views/PersoneView.vue') },
    {
      path: '/persone/:id(\\d+)',
      name: 'persona',
      component: () => import('@/views/PersonaView.vue'),
      props: (rotta) => ({ id: Number(rotta.params.id) }),
    },
    {
      path: '/persone/:id(\\d+)/sanitarie',
      name: 'sanitarie',
      component: () => import('@/views/SanitarieView.vue'),
      props: (rotta) => ({ id: Number(rotta.params.id) }),
    },
    {
      path: '/campo',
      name: 'campo',
      component: () => import('@/views/CampoView.vue'),
      meta: { richiede: 'capo' },
    },
    {
      path: '/unita',
      name: 'unita',
      component: () => import('@/views/UnitaView.vue'),
      meta: { richiede: 'capo' },
    },
    {
      path: '/unita/:id(\\d+)',
      name: 'unita-dettaglio',
      component: () => import('@/views/UnitaDettaglioView.vue'),
      props: (rotta) => ({ id: Number(rotta.params.id) }),
      meta: { richiede: 'capo' },
    },
    {
      // Capi, and the technical administrator for the first capogruppo: the API decides.
      path: '/gruppo',
      name: 'gruppo',
      component: () => import('@/views/GruppoView.vue'),
    },
    {
      // Joining from the app with a registration code: reachable without an account.
      path: '/iscrizione/:codice',
      name: 'iscrizione',
      component: () => import('@/views/IscrizioneView.vue'),
      meta: { pubblica: true },
      props: true,
    },
    {
      path: '/mia-iscrizione',
      name: 'mia-iscrizione',
      component: () => import('@/views/MiaIscrizioneView.vue'),
    },
    {
      // Capigruppo: the API decides.
      path: '/iscrizioni-buonastrada',
      name: 'iscrizioni-buonastrada',
      component: () => import('@/views/IscrizioniBuonaStradaView.vue'),
    },
    {
      // Capigruppo: the API decides.
      path: '/modulistica',
      name: 'modulistica',
      component: () => import('@/views/ModulisticaView.vue'),
    },
    {
      // Unit staff and capigruppo: the API lists only what this user decides.
      path: '/iscrizioni',
      name: 'iscrizioni',
      component: () => import('@/views/IscrizioniView.vue'),
    },
    {
      // Capigruppo: the API decides (DEC-102).
      path: '/diritti',
      name: 'diritti',
      component: () => import('@/views/DirittiView.vue'),
    },
    {
      path: '/persone/:id(\\d+)/fascicolo',
      name: 'fascicolo',
      component: () => import('@/views/FascicoloView.vue'),
      props: (rotta) => ({ id: Number(rotta.params.id) }),
    },
    {
      // Patrol members: the API decides (DEC-13).
      path: '/squadriglia',
      name: 'squadriglia',
      component: () => import('@/views/SquadrigliaView.vue'),
    },
    {
      // Capigruppo: the API decides (DEC-31).
      path: '/correzioni',
      name: 'correzioni',
      component: () => import('@/views/CorrezioniView.vue'),
    },
    {
      // Group, Co.Ca. and unit treasurers: the API decides (DEC-80…DEC-84, DEC-92).
      path: '/quote',
      name: 'quote',
      component: () => import('@/views/QuoteView.vue'),
    },
    {
      // The bank statement: group treasurer and capigruppo; the API decides (DEC-221).
      path: '/banca',
      name: 'banca',
      component: () => import('@/views/BancaView.vue'),
    },
    {
      // Notices for the user's units and the group; the API decides (DEC-218).
      path: '/bacheca',
      name: 'bacheca',
      component: () => import('@/views/BachecaView.vue'),
    },
    {
      // The family's own fees: the API decides (DEC-16).
      path: '/mie-quote',
      name: 'mie-quote',
      component: () => import('@/views/MieQuoteView.vue'),
    },
    {
      // Events of the user and their children; every event for the capi (DEC-75).
      path: '/eventi',
      name: 'eventi',
      component: () => import('@/views/EventiView.vue'),
    },
    {
      path: '/eventi/:id(\\d+)',
      name: 'evento',
      component: () => import('@/views/EventoView.vue'),
      props: (rotta) => ({ id: Number(rotta.params.id) }),
    },
    {
      // The capi's file: the capo and the whole Co.Ca. (DEC-206, the API decides).
      path: '/persone/:id(\\d+)/fascicolo-capo',
      name: 'fascicolo-capo',
      component: () => import('@/views/FascicoloCapoView.vue'),
      props: (rotta) => ({ id: Number(rotta.params.id) }),
    },
    {
      // The file of a year: capi, the person, the parents; each section as allowed
      // (DEC-38, the API decides).
      path: '/persone/:id(\\d+)/fascicolo-anno',
      name: 'fascicolo-anno',
      component: () => import('@/views/FascicoloAnnoView.vue'),
      props: (rotta) => ({ id: Number(rotta.params.id) }),
    },
    {
      // The sentiero of one E/G: staff, the ragazzo, parents, CSQ (the API decides).
      path: '/persone/:id(\\d+)/sentiero',
      name: 'sentiero',
      component: () => import('@/views/SentieroView.vue'),
      props: (rotta) => ({ id: Number(rotta.params.id) }),
    },
    {
      // The reparto at a glance: capi (DEC-72).
      path: '/unita/:id(\\d+)/sentiero',
      name: 'sentiero-unita',
      component: () => import('@/views/SentieroUnitaView.vue'),
      props: (rotta) => ({ id: Number(rotta.params.id) }),
      meta: { richiede: 'capo' },
    },
    {
      // Imprese, posti d'azione, specialità di squadriglia: capi (DEC-64, DEC-65); also
      // the CSQ and the Consiglio d'impresa, for what they run (DEC-187, the API decides).
      path: '/unita/:id(\\d+)/imprese',
      name: 'imprese',
      component: () => import('@/views/ImpreseView.vue'),
      props: (rotta) => ({ id: Number(rotta.params.id) }),
    },
    {
      // Passages to the next branch: capi see, unit staff and capigruppo act (DEC-69).
      path: '/unita/:id(\\d+)/passaggi',
      name: 'passaggi',
      component: () => import('@/views/PassaggiView.vue'),
      props: (rotta) => ({ id: Number(rotta.params.id) }),
      meta: { richiede: 'capo' },
    },
    {
      // Using the app as another user: capigruppo, administrators who are capi, unit
      // staff (the API decides).
      path: '/impersonazioni',
      name: 'impersonazioni',
      component: () => import('@/views/ImpersonazioniView.vue'),
      meta: { richiede: 'capo' },
    },
    {
      // Events on BuonaCaccia: the capi's registrations to follow; adults add their own
      // events (DEC-158, DEC-164). The API decides.
      path: '/buonacaccia',
      name: 'buonacaccia',
      component: () => import('@/views/BuonaCacciaView.vue'),
    },
    {
      // Event forms, reusable over the years (DEC-161).
      path: '/buonacaccia/schede',
      name: 'schede-buonacaccia',
      component: () => import('@/views/SchedeBuonaCacciaView.vue'),
      meta: { richiede: 'capo' },
    },
    {
      // Capi training camps for the Zona: the capigruppo (DEC-164).
      path: '/buonacaccia/formazione',
      name: 'formazione-capi',
      component: () => import('@/views/FormazioneCapiView.vue'),
      meta: { richiede: 'capo' },
    },
    {
      // The Co.Ca. and the unit treasurers: the API decides (DEC-85…DEC-88).
      path: '/cassa',
      name: 'cassa',
      component: () => import('@/views/CassaView.vue'),
    },
    {
      // Expenses a capo paid out of pocket (DEC-86).
      path: '/spese',
      name: 'spese',
      component: () => import('@/views/SpeseView.vue'),
      meta: { richiede: 'capo' },
    },
    {
      path: '/email',
      name: 'email',
      component: () => import('@/views/EmailView.vue'),
    },
    {
      path: '/importazione',
      name: 'importazione',
      component: () => import('@/views/ImportazioneView.vue'),
      meta: { richiede: 'importazione' },
    },
    {
      path: '/dispositivi',
      name: 'dispositivi',
      component: () => import('@/views/DispositiviView.vue'),
    },
    { path: '/modifiche', name: 'modifiche', component: () => import('@/views/CodaView.vue') },
    {
      path: '/:percorso(.*)*',
      name: 'non-trovata',
      component: () => import('@/views/NonTrovataView.vue'),
      meta: { pubblica: true },
    },
  ],
})

let inizializzata = false

router.beforeEach(async (verso) => {
  if (!inizializzata) {
    await cassaforte.inizializza() // also wipes data past the offline expiry (DEC-97)
    await controllaRevoca() // a lost phone wipes itself here, before the PIN is asked
    inizializzata = true
  }
  // Data just wiped (revocation, expiry, wrong PINs): to the login page, saying why.
  const motivo = cassaforte.ultimoMotivo.value
  if (motivo && motivo !== 'uscita') {
    cassaforte.ultimoMotivo.value = null
    useSessioneStore().dimentica()
    if (verso.name !== 'accesso' || verso.query.motivo !== motivo) {
      return { name: 'accesso', query: { motivo } }
    }
  }
  // Locked vault: nothing (not even the cached profile) is readable before unlocking.
  if (cassaforte.stato.value === 'bloccata') {
    if (verso.name === 'sblocco') return true
    return { name: 'sblocco', query: { prossima: verso.fullPath } }
  }
  if (verso.name === 'sblocco') return { name: 'home' }

  const sessione = useSessioneStore()
  if (!sessione.pronta) await sessione.carica()
  if (verso.meta.pubblica) return true
  if (!sessione.autenticato) return { name: 'accesso', query: { prossima: verso.fullPath } }
  // First login on this device: choose PIN or "solo online" before anything else.
  // An account still waiting for its registration has no data to protect yet.
  if (
    cassaforte.stato.value === 'da_configurare' &&
    sessione.profilo?.persona &&
    verso.name !== 'protezione'
  ) {
    return { name: 'protezione', query: { prossima: verso.fullPath } }
  }
  if (verso.meta.richiede === 'capo' && !sessione.capo) return { name: 'home' }
  if (verso.meta.richiede === 'importazione' && !sessione.puoImportare) return { name: 'home' }
  return true
})

export default router
