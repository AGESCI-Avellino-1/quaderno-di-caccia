<script setup lang="ts">
import { ref, watch } from 'vue'
import { RouterLink } from 'vue-router'

import { api, fascicoloAnnoPdf, fotoProfilo, type FascicoloAnno } from '@/api/qdc'
import { useErrore } from '@/composables/useErrore'
import { useNomePersona } from '@/composables/useNomePagina'

// The file of a ragazzo for an associative year (DEC-38, DEC-203): every section the
// user may read, chosen by the API; printed as PDF. Online only: it gathers health
// data and notes, whose reads are logged.
const props = defineProps<{ id: number }>()
const { errore, inCorso, esegui } = useErrore()
const dati = ref<FascicoloAnno | null>(null)
useNomePersona(
  () => props.id,
  () => dati.value?.persona,
)
const anno = ref<number | undefined>(undefined)

async function carica() {
  dati.value = (await esegui(() => api.fascicoloAnno(props.id, anno.value))) ?? null
  if (dati.value) anno.value = dati.value.anno
}
watch(() => props.id, carica, { immediate: true })
</script>

<template>
  <section style="max-width: 50rem">
    <div v-if="errore" class="alert theme-danger small" role="alert">{{ errore }}</div>
    <p v-if="inCorso && !dati" class="fg-2">Caricamento…</p>
    <template v-if="dati">
      <div class="d-flex flex-wrap align-items-start gap-3 mb-3">
        <img
          v-if="dati.foto"
          :src="fotoProfilo(dati.persona_id)"
          :alt="`Foto di ${dati.persona}`"
          width="72"
          height="72"
          class="rounded"
        />
        <div class="flex-grow-1">
          <h1 class="h4 mb-1">Fascicolo di {{ dati.persona }}</h1>
          <RouterLink :to="{ name: 'persona', params: { id: dati.persona_id } }" class="small">
            Scheda della persona
          </RouterLink>
        </div>
      </div>
      <div class="d-flex flex-wrap align-items-end gap-3 mb-5">
        <div>
          <label class="form-label small" for="anno-fascicolo">Anno associativo</label>
          <select
            id="anno-fascicolo"
            v-model="anno"
            class="form-control form-control-sm"
            @change="carica"
          >
            <option v-for="a in dati.anni" :key="a.anno" :value="a.anno">{{ a.etichetta }}</option>
          </select>
        </div>
        <a
          :href="fascicoloAnnoPdf(dati.persona_id, dati.anno)"
          class="btn btn-sm btn-outline theme-primary"
        >
          Stampa (PDF)
        </a>
      </div>
      <section v-for="s in dati.sezioni" :key="s.titolo" class="mb-5">
        <h2 class="h5">{{ s.titolo }}</h2>
        <p v-if="!s.voci.length" class="small fg-2">{{ s.vuota || '—' }}</p>
        <dl v-else class="row small mb-0">
          <template v-for="(v, n) in s.voci" :key="n">
            <dt class="col-12 md:col-4">{{ v.etichetta }}</dt>
            <dd class="col-12 md:col-8 testo-a-capo">{{ v.valore }}</dd>
          </template>
        </dl>
      </section>
    </template>
  </section>
</template>
