<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'

import { api, type IncarichiGruppo } from '@/api/qdc'
import CopiaLocale from '@/components/CopiaLocale.vue'
import ElencoIncarichi from '@/components/ElencoIncarichi.vue'
import FineAnno from '@/components/FineAnno.vue'
import StampaIncarichi from '@/components/StampaIncarichi.vue'
import { useErrore } from '@/composables/useErrore'
import { leggiConCache } from '@/offline/cache'
import { useSessioneStore } from '@/stores/sessione'

// Additional group roles: capigruppo (diarchy, DEC-18), group treasurers, technical
// administrators; they add up with the service (DEC-165, DEC-166). Appointed by the
// capigruppo in office; by the technical administrator only when there is none (first
// start). Then the capi serving outside the units (two support services, which replaced
// "a disposizione", DEC-293) and, for the capigruppo, the capi with no service at all.
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
const ancoraADisposizione = computed(
  () => dati.value?.supporto.filter((i) => i.ruolo === 'A_DISPOSIZIONE') ?? [],
)
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
          Capi senza servizio: né in un'unità né in un servizio di supporto. Assegnali a un'unità
          (dalla pagina dell'unità) o a un servizio di supporto qui sotto:
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
      <h2 class="h5">Servizi di supporto</h2>
      <p class="small fg-2">
        Capi della Co.Ca. che fanno servizio fuori dalle unità: servizio di supporto al gruppo o
        all'azione educativa, uno solo per capo. Quando un capo viene assegnato a un'unità, il
        servizio di supporto finisce da sé.
      </p>
      <div v-if="ancoraADisposizione.length" class="alert theme-warning small" role="status">
        <div>
          «A disposizione» non c'è più: per
          <template v-for="(i, n) in ancoraADisposizione" :key="i.id">
            {{ i.persona.nome }} {{ i.persona.cognome
            }}{{ n < ancoraADisposizione.length - 1 ? ', ' : '' }}
          </template>
          scegli uno dei due servizi di supporto qui sotto; «a disposizione» si chiude da sé.
        </div>
      </div>
      <div class="card card-body">
        <ElencoIncarichi
          :incarichi="dati.supporto"
          :nomina="dati.nomina_supporto"
          :dove="{}"
          :candidati="capi"
          vuoto="Nessun capo in un servizio di supporto."
          @cambiato="carica"
        />
      </div>
      <StampaIncarichi v-if="sessione.profilo?.capogruppo" />
      <FineAnno v-if="sessione.profilo?.capogruppo" />
    </template>
  </section>
</template>
