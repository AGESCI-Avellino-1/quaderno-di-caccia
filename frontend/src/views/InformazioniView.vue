<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'

import Icona from '@/components/Icona.vue'
import { useRete } from '@/composables/useRete'
import { needRefresh, versioneInferiore } from '@/pwa/aggiornamento'
import { linkEmail, linkSegnalazione, testo, voci, type Ambiente } from '@/pwa/informazioni'
import { appInstallata } from '@/pwa/installazione'
import { attiveQui, notificheSupportate, permesso } from '@/pwa/notifiche'
import { biometriaForseDisponibile } from '@/sicurezza/biometria'
import { biometriaAttiva, stato } from '@/sicurezza/cassaforte'
import { useSessioneStore } from '@/stores/sessione'
import { useSitoStore } from '@/stores/sito'

// Open also before the login and with the app locked, when it helps most (DEC-387): it reads
// nothing protected. What ends up in a report is decided in pwa/informazioni.ts.
const sito = useSitoStore()
const sessione = useSessioneStore()
const { online, inCoda, conErrori } = useRete()

const biometriaPossibile = ref(false)
const notificheAttive = ref(false)
const copiato = ref(false)
const errore = ref('')

onMounted(async () => {
  biometriaPossibile.value = await biometriaForseDisponibile().catch(() => false)
  // It asks the server: not before the login, nor offline.
  if (sessione.autenticato && online.value && notificheSupportate()) {
    notificheAttive.value = await attiveQui().catch(() => false)
  }
})

const ambiente = computed<Ambiente>(() => ({
  versioneApp: __VERSIONE_APP__,
  versioneServer: sito.versioneServer,
  installata: appInstallata(),
  agente: navigator.userAgent,
  puntiTocco: navigator.maxTouchPoints,
  schermo: {
    larghezza: window.screen.width,
    altezza: window.screen.height,
    densita: window.devicePixelRatio,
  },
  lingua: navigator.language,
  fuso: Intl.DateTimeFormat().resolvedOptions().timeZone,
  adesso: new Date(),
  online: online.value,
  aggiornamento: needRefresh.value
    ? 'pronta'
    : versioneInferiore(__VERSIONE_APP__, sito.versioneServer)
      ? 'sul_server'
      : 'nessuno',
  stato: stato.value,
  biometria: biometriaAttiva.value
    ? 'attivo'
    : biometriaPossibile.value
      ? 'supportato'
      : 'non_disponibile',
  notifiche: !notificheSupportate()
    ? 'non_supportate'
    : notificheAttive.value
      ? 'attive'
      : permesso() === 'denied'
        ? 'negate'
        : 'non_attive',
  inCoda: inCoda.value,
  conErrori: conErrori.value,
  profilo: sessione.profilo,
}))
const elenco = computed(() => voci(ambiente.value))
const dati = computed(() => testo(elenco.value))
const email = computed(() => sito.sito.email_gruppo ?? '')

async function copia() {
  errore.value = ''
  copiato.value = false
  try {
    // The time of the copy, not of when the page opened.
    await navigator.clipboard.writeText(testo(voci({ ...ambiente.value, adesso: new Date() })))
    copiato.value = true
  } catch {
    errore.value = 'Non sono riuscito a copiare: seleziona il testo e copialo a mano.'
  }
}
</script>

<template>
  <section>
    <h1 class="h4 mb-1">Informazioni</h1>
    <p class="mb-5">
      Il Quaderno di Caccia è l'app del gruppo scout: soci e famiglie, progressione personale,
      eventi e presenze, quote e cassa. Se qualcosa non va, questi dati aiutano a capire il perché:
      non contengono nomi né altri dati personali.
    </p>
    <div class="card card-body mb-5">
      <dl class="row small mb-0">
        <template v-for="v in elenco" :key="v.voce">
          <dt class="col-12 md:col-4">{{ v.voce }}</dt>
          <dd class="col-12 md:col-8 text-break mb-1">{{ v.valore }}</dd>
        </template>
      </dl>
    </div>
    <div class="d-flex flex-wrap gap-3 mb-3">
      <button type="button" class="btn btn-solid theme-primary" @click="copia">
        <Icona nome="clipboard" /> Copia le informazioni
      </button>
    </div>
    <div v-if="copiato" class="alert theme-success small" role="status">Informazioni copiate.</div>
    <div v-if="errore" class="alert theme-danger small" role="alert">{{ errore }}</div>
    <h2 class="h5 mt-7">Segnala un problema</h2>
    <p v-if="email" class="small mb-3">
      <a :href="linkEmail(email, dati)">Scrivi al gruppo</a>: un'email privata, con questi dati già
      inseriti.
    </p>
    <p class="small mb-1">
      <a
        :href="linkSegnalazione(sito.sito.link_segnalazioni ?? '', dati)"
        target="_blank"
        rel="noopener"
        >Apri una segnalazione</a
      >: di base su GitHub, dove serve un account.
    </p>
    <div class="alert theme-warning small" role="note">
      <div>
        Le segnalazioni su GitHub sono pubbliche: le può leggere chiunque. Non scrivere nomi, numeri
        di telefono, dati sanitari o altri dati personali.
      </div>
    </div>
  </section>
</template>
