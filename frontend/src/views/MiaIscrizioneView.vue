<script setup lang="ts">
import { onMounted, ref } from 'vue'

import { api, type RichiestaIscrizione } from '@/api/qdc'
import { useErrore } from '@/composables/useErrore'

// The family follows its requests here. An account waiting for approval sees only
// this page (the server gives it nothing else). Online only.
const { errore, inCorso, esegui } = useErrore()
const richieste = ref<RichiestaIscrizione[]>([])

onMounted(async () => {
  richieste.value = (await esegui(() => api.mieIscrizioni())) ?? []
})

const data = (iso: string) => new Date(iso).toLocaleDateString('it-IT')
const tema = {
  IN_ATTESA: 'theme-warning',
  APPROVATA: 'theme-success',
  RIFIUTATA: 'theme-secondary',
}
</script>

<template>
  <section>
    <h1 class="h4 mb-3">La mia iscrizione</h1>
    <div v-if="errore" class="alert theme-danger" role="alert">{{ errore }}</div>
    <p v-if="!inCorso && !richieste.length" class="fg-2">Nessuna richiesta di iscrizione.</p>
    <article v-for="r in richieste" :key="r.id" class="card card-body mb-5">
      <div class="d-flex flex-wrap align-items-baseline gap-3">
        <h2 class="h5 mb-0">{{ r.nome }} {{ r.cognome }}</h2>
        <span class="badge" :class="tema[r.stato]">{{ r.stato_nome }}</span>
      </div>
      <p class="fg-2 small mb-3">{{ r.unita }} · richiesta del {{ data(r.creata_il) }}</p>
      <p v-if="r.stato === 'IN_ATTESA'" class="mb-0">
        I capi dell'unità esamineranno la richiesta: riceverai un'email con la risposta.
      </p>
      <p v-else-if="r.stato === 'APPROVATA'" class="mb-0">
        Iscrizione accolta.
        <template v-if="r.scadenza_completamento">
          Entro il <strong>{{ data(r.scadenza_completamento) }}</strong> vanno completati i dati e
          caricati i moduli firmati.
        </template>
      </p>
      <p v-else class="mb-0">Non accolta: {{ r.motivo_rifiuto }}</p>
    </article>
  </section>
</template>
