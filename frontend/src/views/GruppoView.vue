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
// Last, the staff of every unit (DEC-316): the capigruppo appoint them here too, the others
// only look; only the capigruppo are told who serves more than one unit (DEC-384).
const { errore, esegui } = useErrore()
const dati = ref<IncarichiGruppo | null>(null)
const copiaDel = ref<string | null>(null)

async function carica() {
  const letto = await esegui(() => leggiConCache('gruppo:incarichi', api.incarichiDiGruppo))
  dati.value = letto?.dati ?? null
  copiaDel.value = letto?.copiaDel ?? null
}
onMounted(carica)

// Only a presbitero may be assistente ecclesiastico (DEC-296): the list shows only them.
const capi = (ruolo: string) => api.capi(ruolo === 'AE_GRUPPO' || ruolo === 'AE_UNITA')
const ancoraADisposizione = computed(
  () => dati.value?.supporto.filter((i) => i.ruolo === 'A_DISPOSIZIONE') ?? [],
)
const sessione = useSessioneStore()
</script>

<template>
  <section>
    <h1 class="h4 mb-1">Organigramma</h1>
    <p v-if="sessione.profilo?.capo" class="small mb-5">
      <RouterLink :to="{ name: 'scheda-incarichi' }">Scheda incarichi</RouterLink>
    </p>
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
      <div v-if="dati.capi_in_piu_unita?.length" class="alert theme-warning small" role="status">
        <div>
          Capi inseriti in più unità, che non sono collegate tra loro:
          <ul class="mb-0">
            <li v-for="c in dati.capi_in_piu_unita" :key="c.persona.id">
              <RouterLink :to="`/persone/${c.persona.id}`"
                >{{ c.persona.nome }} {{ c.persona.cognome }}</RouterLink
              >: {{ c.unita.join(', ') }}
            </li>
          </ul>
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
      <template v-if="dati.staff_unita?.length">
        <h2 class="h5 mt-7">Staff delle unità</h2>
        <p class="small fg-2">
          Capi unità, staff e assistenti ecclesiastici.
          {{
            sessione.profilo?.capogruppo
              ? "Puoi nominarli qui o dalla pagina dell'unità."
              : "Si nominano dalla pagina dell'unità."
          }}
        </p>
        <div class="card card-body">
          <section v-for="(s, n) in dati.staff_unita" :key="s.unita_id" :class="{ 'mt-5': n }">
            <h3 class="h6 mb-3">
              <RouterLink :to="`/unita/${s.unita_id}`">{{ s.unita }}</RouterLink>
            </h3>
            <ElencoIncarichi
              :incarichi="s.incarichi"
              :nomina="s.nomina ?? []"
              :dove="{ unita_id: s.unita_id }"
              :candidati="capi"
              vuoto="Nessuno nello staff."
              @cambiato="carica"
            />
          </section>
        </div>
      </template>
      <StampaIncarichi v-if="sessione.profilo?.capogruppo" />
      <FineAnno v-if="sessione.profilo?.capogruppo" />
    </template>
  </section>
</template>
