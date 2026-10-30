<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { RouterLink, useRouter } from 'vue-router'

import { api } from '@/api/qdc'
import { useSessioneStore } from '@/stores/sessione'

const sessione = useSessioneStore()
// Capigruppo: corrections waiting to be forwarded (DEC-31). Online only; no count offline.
const daInoltrare = ref<number | null>(null)
// Capigruppo and the technical administrator handle corrections (the API decides).
const gestisceCorrezioni = computed(
  () => sessione.capogruppo || !!sessione.profilo?.amministratore_tecnico,
)
const router = useRouter()
onMounted(async () => {
  // The counters on the cards change while the app is open: read the profile again.
  if (navigator.onLine) await sessione.carica()
  // An account waiting for approval has nothing else to see.
  if (!sessione.profilo?.persona && sessione.profilo?.mie_iscrizioni) {
    await router.replace('/mia-iscrizione')
    return
  }
  if (!gestisceCorrezioni.value) return
  try {
    daInoltrare.value = (await api.correzioni()).filter((c) => c.stato === 'IN_ATTESA').length
  } catch {
    daInoltrare.value = null
  }
})
</script>

<template>
  <section v-if="sessione.profilo">
    <h1 class="h4 mb-5">Ciao {{ sessione.profilo.persona?.nome ?? sessione.profilo.email }}</h1>
    <div v-if="sessione.profilo.capo_in_attesa" class="alert theme-info small" role="status">
      <div>
        Sei iscritto dall'app e non ancora in BuonaStrada: fino ad allora non vedi i contatti, i
        dati sanitari e gli altri dati delicati dei soci.
      </div>
    </div>
    <div class="row g-5">
      <div v-if="sessione.capo" class="col-12 md:col-6">
        <RouterLink to="/campo" class="card card-body h-100 text-decoration-none">
          <strong>Al campo</strong>
          <span class="fg-2 small">Contatti, farmaci e allergie dell'unità, anche senza rete</span>
        </RouterLink>
      </div>
      <div v-if="sessione.capo" class="col-12 md:col-6">
        <RouterLink to="/persone" class="card card-body h-100 text-decoration-none">
          <strong>Persone</strong>
          <span class="fg-2 small">Anagrafiche visibili con il tuo ruolo</span>
        </RouterLink>
      </div>
      <div v-if="sessione.capo" class="col-12 md:col-6">
        <RouterLink to="/unita" class="card card-body h-100 text-decoration-none">
          <strong>Unità</strong>
          <span class="fg-2 small">Branchi, Reparti, Clan e Co.Ca.</span>
        </RouterLink>
      </div>
      <div v-if="sessione.profilo.amministratore_tecnico && !sessione.capo" class="col-12 md:col-6">
        <RouterLink to="/gruppo" class="card card-body h-100 text-decoration-none">
          <strong>Capigruppo</strong>
          <span class="fg-2 small">Nomina il primo capogruppo del gruppo</span>
        </RouterLink>
      </div>
      <div
        v-if="sessione.profilo.gestisce_quote || sessione.profilo.unita_quote.length"
        class="col-12 md:col-6"
      >
        <RouterLink to="/quote" class="card card-body h-100 text-decoration-none">
          <strong>Quote</strong>
          <span class="fg-2 small">
            {{
              sessione.profilo.gestisce_quote
                ? 'Tipi di quota, emissione e chi ha pagato'
                : 'Chi ha pagato nelle unità'
            }}
          </span>
        </RouterLink>
      </div>
      <div
        v-if="sessione.profilo.persona || sessione.profilo.tutelati.length"
        class="col-12 md:col-6"
      >
        <RouterLink to="/eventi" class="card card-body h-100 text-decoration-none">
          <strong>Eventi</strong>
          <span class="small fg-2">Riunioni, uscite e campi; partecipazione e presenze</span>
        </RouterLink>
      </div>
      <div
        v-if="sessione.profilo.puo_impersonare && !sessione.profilo.impersonazione"
        class="col-12 md:col-6"
      >
        <RouterLink to="/impersonazioni" class="card card-body h-100 text-decoration-none">
          <strong>Usa l'app al posto di un altro</strong>
          <span class="small fg-2">Per aiutare qualcuno a compilare o vedere un problema</span>
        </RouterLink>
      </div>
      <div v-if="sessione.profilo.eventi_buonacaccia" class="col-12 md:col-6">
        <RouterLink to="/buonacaccia" class="card card-body h-100 text-decoration-none">
          <strong>Eventi su BuonaCaccia</strong>
          <span class="small fg-2">
            Piccole Orme, campetti, formazione: iscrizioni, scadenze e liberatorie
          </span>
        </RouterLink>
      </div>
      <div v-if="sessione.profilo.persona" class="col-12 md:col-6">
        <RouterLink to="/email" class="card card-body h-100 text-decoration-none">
          <strong>Le mie email</strong>
          <span class="small fg-2">Scegli quali email ricevere</span>
        </RouterLink>
      </div>
      <div v-if="sessione.profilo.vede_cassa" class="col-12 md:col-6">
        <RouterLink to="/cassa" class="card card-body h-100 text-decoration-none">
          <strong>Prima nota</strong>
          <span class="fg-2 small">Casse, movimenti, rimborsi e rendiconto</span>
        </RouterLink>
      </div>
      <div v-if="sessione.capo && !sessione.profilo.capo_in_attesa" class="col-12 md:col-6">
        <RouterLink to="/spese" class="card card-body h-100 text-decoration-none">
          <strong>Le mie spese</strong>
          <span class="fg-2 small">Quello che hai pagato per il gruppo, da farti rimborsare</span>
        </RouterLink>
      </div>
      <div
        v-if="sessione.profilo.persona || sessione.profilo.tutelati.length"
        class="col-12 md:col-6"
      >
        <RouterLink to="/mie-quote" class="card card-body h-100 text-decoration-none">
          <strong>Le mie quote</strong>
          <span class="fg-2 small">Quote da pagare, pagamenti e ricevute</span>
        </RouterLink>
      </div>
      <div v-if="gestisceCorrezioni" class="col-12 md:col-6">
        <RouterLink to="/correzioni" class="card card-body h-100 text-decoration-none">
          <strong>
            Correzioni da inoltrare
            <span v-if="daInoltrare" class="badge theme-warning ms-1">{{ daInoltrare }}</span>
          </strong>
          <span class="fg-2 small">Dati corretti nell'app, da mandare alla segreteria</span>
        </RouterLink>
      </div>
      <div
        v-if="sessione.profilo.iscrizioni_da_decidere || sessione.profilo.iscrizioni_da_verificare"
        class="col-12 md:col-6"
      >
        <RouterLink to="/iscrizioni" class="card card-body h-100 text-decoration-none">
          <strong>
            Richieste di iscrizione
            <span v-if="sessione.profilo.iscrizioni_da_decidere" class="badge theme-warning ms-1">{{
              sessione.profilo.iscrizioni_da_decidere
            }}</span>
          </strong>
          <span class="fg-2 small">
            Nuovi soci da accogliere<template v-if="sessione.profilo.iscrizioni_da_verificare"
              >, moduli da verificare ({{ sessione.profilo.iscrizioni_da_verificare }})</template
            >
          </span>
        </RouterLink>
      </div>
      <div v-if="sessione.profilo.mie_iscrizioni" class="col-12 md:col-6">
        <RouterLink to="/mia-iscrizione" class="card card-body h-100 text-decoration-none">
          <strong>La mia iscrizione</strong>
          <span class="fg-2 small">Stato delle richieste, dati e moduli da completare</span>
        </RouterLink>
      </div>
      <div v-if="sessione.capogruppo" class="col-12 md:col-6">
        <RouterLink to="/iscrizioni-buonastrada" class="card card-body h-100 text-decoration-none">
          <strong>
            Iscrizioni da inserire in BuonaStrada
            <span v-if="sessione.profilo.iscrizioni_da_inserire" class="badge theme-warning ms-1">{{
              sessione.profilo.iscrizioni_da_inserire
            }}</span>
          </strong>
          <span class="fg-2 small">Nuovi soci completi, da copiare in BuonaStrada</span>
        </RouterLink>
      </div>
      <div v-if="sessione.capogruppo" class="col-12 md:col-6">
        <RouterLink to="/modulistica" class="card card-body h-100 text-decoration-none">
          <strong>Modulistica</strong>
          <span class="fg-2 small">Moduli da firmare per le iscrizioni</span>
        </RouterLink>
      </div>
      <div v-if="sessione.capogruppo" class="col-12 md:col-6">
        <RouterLink to="/diritti" class="card card-body h-100 text-decoration-none">
          <strong>Richieste degli interessati</strong>
          <span class="fg-2 small">Accesso, copia e cancellazione dei dati</span>
        </RouterLink>
      </div>
      <div v-if="sessione.puoImportare" class="col-12 md:col-6">
        <RouterLink to="/importazione" class="card card-body h-100 text-decoration-none">
          <strong>Importa da BuonaStrada</strong>
          <span class="fg-2 small">Carica l'export "Ricerca soci" (CSV)</span>
        </RouterLink>
      </div>
      <div v-if="sessione.profilo.squadriglie?.length" class="col-12 md:col-6">
        <RouterLink to="/squadriglia" class="card card-body h-100 text-decoration-none">
          <strong>La mia squadriglia</strong>
          <span class="fg-2 small">I numeri di telefono della squadriglia</span>
        </RouterLink>
      </div>
      <div v-for="tutelato in sessione.profilo.tutelati" :key="tutelato.id" class="col-12 md:col-6">
        <RouterLink
          :to="{ name: 'persona', params: { id: tutelato.id } }"
          class="card card-body h-100 text-decoration-none"
        >
          <strong>{{ tutelato.nome }} {{ tutelato.cognome }}</strong>
          <span class="fg-2 small">Scheda di tuo figlio/a</span>
        </RouterLink>
      </div>
      <div
        v-if="sessione.profilo.persona && !sessione.capo && sessione.profilo.branca === 'eg'"
        class="col-12 md:col-6"
      >
        <RouterLink
          :to="{ name: 'sentiero', params: { id: sessione.profilo.persona.id } }"
          class="card card-body h-100 text-decoration-none"
        >
          <strong>Il mio sentiero</strong>
          <span class="fg-2 small">Tappe, mete e impegni</span>
        </RouterLink>
      </div>
      <div v-if="sessione.profilo.persona && !sessione.capo" class="col-12 md:col-6">
        <RouterLink
          :to="{ name: 'persona', params: { id: sessione.profilo.persona.id } }"
          class="card card-body h-100 text-decoration-none"
        >
          <strong>La mia scheda</strong>
        </RouterLink>
      </div>
    </div>
    <p class="small mt-7">
      <RouterLink to="/dispositivi">Dispositivi e protezione di questo telefono</RouterLink>
    </p>
  </section>
</template>
