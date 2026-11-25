<script setup lang="ts">
import { computed, ref } from 'vue'

import { coincide, type Opzione } from '@/components/sceltaDaElenco'

// People chosen one by one (DEC-430): the list, filtered by what is written, with a check
// each; who is chosen comes first, in sight also while filtering.
const props = defineProps<{ id: string; opzioni: Opzione[] }>()
const scelti = defineModel<number[]>({ required: true })
const testo = ref('')
const presi = computed(() => new Set(scelti.value))
const nomiScelti = computed(() => props.opzioni.filter((o) => presi.value.has(o.id)))
const trovate = computed(() => props.opzioni.filter((o) => coincide(o, testo.value)))
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
    <input
      :id="`${id}-cerca`"
      v-model="testo"
      type="search"
      class="form-control form-control-sm mb-3"
      placeholder="Cerca per nome…"
      aria-label="Cerca una persona"
      @keydown.enter.prevent
    />
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
