<script setup lang="ts">
import { RouterLink } from 'vue-router'

import { useSessioneStore } from '@/stores/sessione'

const sessione = useSessioneStore()
</script>

<template>
  <section v-if="sessione.profilo">
    <h1 class="h4 mb-5">Ciao {{ sessione.profilo.persona?.nome ?? sessione.profilo.email }}</h1>
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
      <div v-if="sessione.puoImportare" class="col-12 md:col-6">
        <RouterLink to="/importazione" class="card card-body h-100 text-decoration-none">
          <strong>Importa da BuonaStrada</strong>
          <span class="fg-2 small">Carica l'export "Ricerca soci" (CSV)</span>
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
