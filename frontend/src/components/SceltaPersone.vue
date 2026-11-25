<script setup lang="ts">
import { computed, ref, watch } from 'vue'

import { coincide, type Opzione } from '@/components/sceltaDaElenco'

// People chosen one by one (DEC-430): the list, filtered by what is written, with a check
// each; who is chosen comes first, in sight also while filtering. The filter by unit takes or
// leaves everyone it shows in one go (DEC-434).
const props = defineProps<{ id: string; opzioni: Opzione[] }>()
const scelti = defineModel<number[]>({ required: true })
const testo = ref('')
const presi = computed(() => new Set(scelti.value))
const nomiScelti = computed(() => props.opzioni.filter((o) => presi.value.has(o.id)))
const unita = computed(() =>
  [...new Set(props.opzioni.flatMap((o) => (o.dettaglio ? [o.dettaglio] : [])))].sort((a, b) =>
    a.localeCompare(b, 'it'),
  ),
)
const filtro = ref('')
const trovate = computed(() =>
  props.opzioni.filter(
    (o) => (!filtro.value || o.dettaglio === filtro.value) && coincide(o, testo.value),
  ),
)
// The options change with who creates the meeting: a unit no longer there does not hide everyone.
watch(unita, (u) => {
  if (!u.includes(filtro.value)) filtro.value = ''
})

function scegliTutti() {
  scelti.value = [...new Set([...scelti.value, ...trovate.value.map((o) => o.id)])]
}

function togliTutti() {
  const via = new Set(trovate.value.map((o) => o.id))
  scelti.value = scelti.value.filter((i) => !via.has(i))
}
</script>

<template>
  <fieldset>
    <legend class="form-label small">Partecipanti ({{ nomiScelti.length }})</legend>
    <div v-if="nomiScelti.length" class="d-flex flex-wrap gap-1 mb-3">
      <button
        v-for="o in nomiScelti"
        :key="o.id"
        type="button"
        class="btn btn-sm btn-outline theme-primary"
        :aria-label="`Togli ${o.nome}`"
        @click="scelti = scelti.filter((i) => i !== o.id)"
      >
        {{ o.nome }} ×
      </button>
    </div>
    <select
      v-if="unita.length > 1"
      :id="`${id}-unita`"
      v-model="filtro"
      class="form-control form-control-sm mb-3"
      aria-label="Filtra per unità"
    >
      <option value="">Tutte le unità</option>
      <option v-for="u in unita" :key="u" :value="u">{{ u }}</option>
    </select>
    <input
      :id="`${id}-cerca`"
      v-model="testo"
      type="search"
      class="form-control form-control-sm mb-3"
      placeholder="Cerca per nome…"
      aria-label="Cerca una persona"
      @keydown.enter.prevent
    />
    <div v-if="filtro" class="d-flex gap-3 mb-1 small">
      <button
        type="button"
        class="btn btn-link btn-sm p-0"
        :disabled="trovate.every((o) => presi.has(o.id))"
        @click="scegliTutti"
      >
        Scegli tutti
      </button>
      <button
        type="button"
        class="btn btn-link btn-sm p-0"
        :disabled="!trovate.some((o) => presi.has(o.id))"
        @click="togliTutti"
      >
        Togli tutti
      </button>
    </div>
    <div class="qdc-scelta-persone border rounded p-3">
      <div v-for="o in trovate" :key="o.id" class="form-field mb-1">
        <input :id="`${id}-${o.id}`" v-model="scelti" type="checkbox" class="check" :value="o.id" />
        <label :for="`${id}-${o.id}`">
          {{ o.nome }} <span v-if="o.dettaglio" class="small fg-2">{{ o.dettaglio }}</span>
        </label>
      </div>
      <p v-if="!trovate.length" class="small fg-2 mb-0">Nessuno con questo nome.</p>
    </div>
  </fieldset>
</template>
