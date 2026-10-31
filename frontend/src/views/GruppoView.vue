<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'

import { api, type IncarichiGruppo } from '@/api/qdc'
import CopiaLocale from '@/components/CopiaLocale.vue'
import ElencoIncarichi from '@/components/ElencoIncarichi.vue'
import FineAnno from '@/components/FineAnno.vue'
import { useErrore } from '@/composables/useErrore'
import { leggiConCache } from '@/offline/cache'
import { useSessioneStore } from '@/stores/sessione'

// Additional group roles: capigruppo (diarchy, DEC-18), group treasurers, technical
// administrators; they add up with the service (DEC-165, DEC-166). Appointed by the
// capigruppo in office; by the technical administrator only when there is none (first
// start). Then the capi at disposal (no unit for now) and, for the capigruppo, the capi
// with no service at all.
const { errore, esegui } = useErrore()
const dati = ref<IncarichiGruppo | null>(null)
const copiaDel = ref<string | null>(null)

async function carica() {
  const letto = await esegui(() => leggiConCache('gruppo:incarichi', api.incarichiDiGruppo))
  dati.value = letto?.dati ?? null
  copiaDel.value = letto?.copiaDel ?? null
}
onMounted(carica)

const capi = () => api.capi()
const sessione = useSessioneStore()
</script>

<template>
  <section>
    <h1 class="h4 mb-5">Incarichi di gruppo</h1>
    <div v-if="errore" class="alert theme-danger" role="alert">{{ errore }}</div>
    <CopiaLocale :del="copiaDel" />
    <template v-if="dati">
      <div v-if="dati.senza_servizio.length" class="alert theme-warning small" role="status">
        <div>
          Capi senza servizio: né in un'unità né a disposizione. Assegnali a un'unità (dalla pagina
          dell'unità) o mettili a disposizione qui sotto:
          <template v-for="(p, n) in dati.senza_servizio" :key="p.id">
            <RouterLink :to="`/persone/${p.id}`">{{ p.nome }} {{ p.cognome }}</RouterLink
            >{{ n < dati.senza_servizio.length - 1 ? ', ' : '.' }}
          </template>
        </div>
      </div>
      <h2 class="h5">Capigruppo, tesorieri e amministratori</h2>
      <p class="small fg-2">
        Ruoli che si aggiungono al servizio: lo stesso capo può essere, per esempio, capo unità,
        capogruppo, tesoriere e amministratore.
      </p>
      <div class="card card-body mb-5">
        <ElencoIncarichi
          :incarichi="dati.incarichi"
          :nomina="dati.nomina"
          :dove="{}"
          :candidati="capi"
          vuoto="Nessun capogruppo registrato."
          @cambiato="carica"
        />
      </div>
      <h2 class="h5">A disposizione</h2>
      <p class="small fg-2">
        Capi della Co.Ca. che al momento non fanno servizio in un'unità. Quando un capo viene
        assegnato a un'unità, «a disposizione» finisce da sé.
      </p>
      <div class="card card-body">
        <ElencoIncarichi
          :incarichi="dati.a_disposizione"
          :nomina="dati.nomina_a_disposizione"
          :dove="{}"
          :candidati="capi"
          vuoto="Nessun capo a disposizione."
          @cambiato="carica"
        />
      </div>
      <FineAnno v-if="sessione.profilo?.capogruppo" />
    </template>
  </section>
</template>
