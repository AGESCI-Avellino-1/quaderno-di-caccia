<script setup lang="ts">
import { ref, watch } from 'vue'
import { RouterLink } from 'vue-router'

import { api, euro, fileFormazione, type FormazioneCapo } from '@/api/qdc'
import { useErrore } from '@/composables/useErrore'

// For the Zona (DEC-164): the capi training camps of an associative year, with date,
// place, type of camp and the fee each capo paid. The Zona computes its contribution by
// itself. Capigruppo only (the API decides).
const { errore, esegui } = useErrore()
const oggi = new Date()
// The associative year is named by the year it ends (1 October – 30 September).
const anno = ref(oggi.getMonth() >= 9 ? oggi.getFullYear() + 1 : oggi.getFullYear())
const righe = ref<FormazioneCapo[]>([])

watch(
  anno,
  async (valore) => {
    righe.value = (await esegui(() => api.formazioneCapi(valore))) ?? []
  },
  { immediate: true },
)

const data = (iso: string) => new Date(iso).toLocaleDateString('it-IT')
</script>

<template>
  <section>
    <h1 class="h4">Formazione capi per la Zona</h1>
    <p class="small fg-2">
      I campi di formazione capi dell'anno, con la quota che ogni capo ha versato. I capi li segnano
      dalla pagina dell'evento su BuonaCaccia.
    </p>
    <div v-if="errore" class="alert theme-danger small" role="alert">{{ errore }}</div>
    <div class="d-flex flex-wrap align-items-end gap-3 mb-3">
      <div>
        <label class="form-label small" for="anno-formazione">Anno associativo</label>
        <select id="anno-formazione" v-model="anno" class="form-control form-control-sm">
          <option v-for="a in [anno + 1, anno, anno - 1, anno - 2]" :key="a" :value="a">
            {{ a - 1 }}/{{ String(a).slice(2) }}
          </option>
        </select>
      </div>
      <a :href="fileFormazione(anno)" class="small">Scarica in Excel</a>
    </div>
    <p v-if="!righe.length" class="small">Nessun campo di formazione in questo anno.</p>
    <div v-else class="table-responsive">
      <table class="table table-sm small">
        <thead>
          <tr>
            <th scope="col">Capo</th>
            <th scope="col">Evento</th>
            <th scope="col">Date</th>
            <th scope="col">Località</th>
            <th scope="col">Tipo di campo</th>
            <th scope="col" class="text-end">Quota versata</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="r in righe" :key="`${r.evento_id}-${r.persona_id}`">
            <td>{{ r.persona }}</td>
            <td>
              <RouterLink :to="`/eventi/${r.evento_id}`">{{ r.evento }}</RouterLink>
            </td>
            <td>
              {{ data(r.dal) }}<template v-if="r.al !== r.dal"> – {{ data(r.al) }}</template>
            </td>
            <td>{{ r.luogo }}</td>
            <td>{{ r.tipo_campo }}</td>
            <td class="text-end">{{ r.quota_versata ? euro(r.quota_versata) : '—' }}</td>
          </tr>
        </tbody>
      </table>
    </div>
  </section>
</template>
