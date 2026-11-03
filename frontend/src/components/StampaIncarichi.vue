<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'

import { api, elencoIncarichiPdf, type OpzioniElencoIncarichi } from '@/api/qdc'
import { useErrore } from '@/composables/useErrore'

// The PDF list of the group's roles, for the capigruppo (DEC-284): the kinds of role,
// grouped by unit or by role, in force today or at the end of a past year. Online only.
const { errore, esegui } = useErrore()
const opzioni = ref<OpzioniElencoIncarichi | null>(null)
const scelti = ref<string[]>([])
const raggruppa = ref<'unita' | 'incarico'>('unita')
const anno = ref('')

onMounted(async () => {
  opzioni.value = (await esegui(() => api.opzioniElencoIncarichi())) ?? null
  scelti.value = opzioni.value?.ruoli.map((r) => r.valore) ?? []
  anno.value = opzioni.value?.anni[0]?.valore ?? ''
})

// The year in course is "today": no year in the address.
const indirizzo = computed(() =>
  elencoIncarichiPdf(
    scelti.value,
    raggruppa.value,
    anno.value && anno.value !== opzioni.value?.anni[0]?.valore ? anno.value : null,
  ),
)
</script>

<template>
  <h2 class="h5 mt-7">Elenco degli incarichi</h2>
  <p class="small fg-2">
    Un PDF su carta intestata del gruppo con codice socio, nome, cognome e livello di formazione
    capi. Il livello è sempre quello di oggi.
  </p>
  <div v-if="errore" class="alert theme-danger small" role="alert">{{ errore }}</div>
  <div v-if="opzioni" class="card card-body">
    <fieldset class="mb-5">
      <legend class="small fw-bold">Incarichi da includere</legend>
      <div class="row">
        <div v-for="r in opzioni.ruoli" :key="r.valore" class="col-12 md:col-6 form-field">
          <input
            :id="`elenco-${r.valore}`"
            v-model="scelti"
            type="checkbox"
            class="check"
            :value="r.valore"
          />
          <label :for="`elenco-${r.valore}`">{{ r.nome }}</label>
        </div>
      </div>
    </fieldset>
    <fieldset class="mb-5">
      <legend class="small fw-bold">Raggruppa i capi</legend>
      <div class="form-field">
        <input id="elenco-unita" v-model="raggruppa" type="radio" class="radio" value="unita" />
        <label for="elenco-unita">
          Per unità (ogni capo in ogni unità in cui ha un incarico; gli incarichi di gruppo in
          Co.Ca.)
        </label>
      </div>
      <div class="form-field">
        <input
          id="elenco-incarico"
          v-model="raggruppa"
          type="radio"
          class="radio"
          value="incarico"
        />
        <label for="elenco-incarico">Per incarico</label>
      </div>
    </fieldset>
    <div class="mb-5">
      <label for="elenco-anno" class="form-label small fw-bold">Anno associativo</label>
      <select id="elenco-anno" v-model="anno" class="form-control">
        <option v-for="(a, n) in opzioni.anni" :key="a.valore" :value="a.valore">
          {{ a.nome }}{{ n === 0 ? ' (incarichi di oggi)' : ' (incarichi alla fine dell’anno)' }}
        </option>
      </select>
    </div>
    <div>
      <a v-if="scelti.length" :href="indirizzo" class="btn btn-solid theme-primary" download>
        Scarica il PDF
      </a>
      <span v-else class="small fg-2">Scegli almeno un incarico.</span>
    </div>
  </div>
</template>
