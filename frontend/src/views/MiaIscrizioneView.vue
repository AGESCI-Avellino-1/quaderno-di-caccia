<script setup lang="ts">
import { onMounted, ref } from 'vue'

import { api, type RichiestaIscrizione } from '@/api/qdc'
import CompletaIscrizione from '@/components/CompletaIscrizione.vue'
import { useErrore } from '@/composables/useErrore'
import { useSessioneStore } from '@/stores/sessione'

// The family follows its requests here and completes them after the approval. An account
// waiting for approval, or suspended because the deadline passed, sees only this page
// (the server gives it nothing else). Online only.
const { errore, inCorso, esegui } = useErrore()
const sessione = useSessioneStore()
const richieste = ref<RichiestaIscrizione[]>([])

onMounted(async () => {
  richieste.value = (await esegui(() => api.mieIscrizioni())) ?? []
})

async function aggiornata(nuova: RichiestaIscrizione) {
  const prima = richieste.value.find((r) => r.id === nuova.id)?.stato
  richieste.value = richieste.value.map((r) => (r.id === nuova.id ? nuova : r))
  if (prima === 'SOSPESA' && nuova.stato !== 'SOSPESA') await sessione.carica() // active again
}

const data = (iso: string) => new Date(iso).toLocaleDateString('it-IT')
const tema = {
  IN_ATTESA: 'theme-warning',
  APPROVATA: 'theme-info',
  SOSPESA: 'theme-danger',
  COMPLETATA: 'theme-success',
  RIFIUTATA: 'theme-secondary',
}
const daCompletare = (r: RichiestaIscrizione) => r.stato === 'APPROVATA' || r.stato === 'SOSPESA'
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
      <template v-else-if="daCompletare(r)">
        <p class="mb-1">
          <template v-if="r.stato === 'SOSPESA'">
            È scaduto il termine: finché non completi, l'app ti mostra solo questa pagina.
          </template>
          <template v-else-if="r.scadenza_completamento">
            Iscrizione accolta. Completa entro il
            <strong>{{ data(r.scadenza_completamento) }}</strong
            >.
          </template>
        </p>
        <p v-if="r.mancanti.length" class="small mb-0">Mancano: {{ r.mancanti.join(', ') }}.</p>
        <CompletaIscrizione :id="r.id" @cambiata="aggiornata" />
      </template>
      <p v-else-if="r.stato === 'COMPLETATA'" class="mb-0">
        Iscrizione completa: il gruppo la inserirà in BuonaStrada, che darà il codice socio
        definitivo.
      </p>
      <p v-else class="mb-0">Non accolta: {{ r.motivo_rifiuto }}</p>
    </article>
  </section>
</template>
