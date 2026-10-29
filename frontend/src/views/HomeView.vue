<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { RouterLink, useRouter } from 'vue-router'

import { api } from '@/api/qdc'
import { useSessioneStore } from '@/stores/sessione'

const sessione = useSessioneStore()
// Capigruppo: corrections waiting to be forwarded (DEC-31). Online only; no count offline.
const daInoltrare = ref<number | null>(null)
const router = useRouter()
onMounted(async () => {
  // An account waiting for approval has nothing else to see.
  if (!sessione.profilo?.persona && sessione.profilo?.mie_iscrizioni) {
    await router.replace('/mia-iscrizione')
    return
  }
  if (!sessione.capogruppo) return
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
      <div v-if="sessione.capogruppo" class="col-12 md:col-6">
        <RouterLink to="/correzioni" class="card card-body h-100 text-decoration-none">
          <strong>
            Correzioni da inoltrare
            <span v-if="daInoltrare" class="badge theme-warning ms-1">{{ daInoltrare }}</span>
          </strong>
          <span class="fg-2 small">Dati corretti nell'app, da mandare alla segreteria</span>
        </RouterLink>
      </div>
      <div v-if="sessione.profilo.iscrizioni_da_decidere" class="col-12 md:col-6">
        <RouterLink to="/iscrizioni" class="card card-body h-100 text-decoration-none">
          <strong>
            Richieste di iscrizione
            <span class="badge theme-warning ms-1">{{
              sessione.profilo.iscrizioni_da_decidere
            }}</span>
          </strong>
          <span class="fg-2 small">Nuovi soci da accogliere</span>
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
    <p class="fg-2 small">
      Progressione personale, presenze e cassa arriveranno nelle prossime versioni.
    </p>
  </section>
</template>
