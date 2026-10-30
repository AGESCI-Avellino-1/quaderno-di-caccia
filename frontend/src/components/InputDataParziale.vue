<script setup lang="ts">
import { ref, watch } from 'vue'

import type { DataParziale, Precisione } from '@/api/qdc'

// A date that may be known only by month or year (DEC-70): for the history of ragazzi
// already in the reparto, never a fake 1 January. What is typed stays as typed; the date
// changes only once it is complete (a year has four digits).
const modello = defineModel<DataParziale>({ required: true })
const props = defineProps<{ id: string; etichetta: string }>()
const oggi = new Date().toLocaleDateString('sv')

function daModello(): string {
  const data = modello.value.data ?? ''
  if (modello.value.precisione === 'ANNO') return data.slice(0, 4)
  if (modello.value.precisione === 'MESE') return data.slice(0, 7)
  return data
}
const valore = ref(daModello())
watch(modello, () => {
  if (modello.value.data !== null || !valore.value) valore.value = daModello()
})

function imposta(testo: string) {
  valore.value = testo
  const completo =
    modello.value.precisione === 'ANNO'
      ? /^\d{4}$/.test(testo)
      : modello.value.precisione === 'MESE'
        ? /^\d{4}-\d{2}$/.test(testo)
        : /^\d{4}-\d{2}-\d{2}$/.test(testo)
  const data = !completo
    ? null
    : modello.value.precisione === 'ANNO'
      ? `${testo}-01-01`
      : modello.value.precisione === 'MESE'
        ? `${testo}-01`
        : testo
  modello.value = { ...modello.value, data }
}

function precisione(nuova: Precisione) {
  const data = modello.value.data
  modello.value = {
    precisione: nuova,
    data: !data
      ? null
      : nuova === 'ANNO'
        ? `${data.slice(0, 4)}-01-01`
        : nuova === 'MESE'
          ? `${data.slice(0, 7)}-01`
          : data,
  }
  valore.value = daModello()
}
</script>

<template>
  <div>
    <label class="form-label small" :for="props.id">{{ etichetta }}</label>
    <div class="d-flex gap-1">
      <input
        v-if="modello.precisione === 'ANNO'"
        :id="props.id"
        type="number"
        min="1950"
        :max="oggi.slice(0, 4)"
        class="form-control form-control-sm"
        :value="valore"
        required
        @input="imposta(($event.target as HTMLInputElement).value)"
      />
      <input
        v-else
        :id="props.id"
        :type="modello.precisione === 'MESE' ? 'month' : 'date'"
        :max="modello.precisione === 'MESE' ? oggi.slice(0, 7) : oggi"
        class="form-control form-control-sm"
        :value="valore"
        required
        @input="imposta(($event.target as HTMLInputElement).value)"
      />
      <select
        class="form-control form-control-sm w-auto"
        :aria-label="`Precisione: ${etichetta}`"
        :value="modello.precisione"
        @change="precisione(($event.target as HTMLSelectElement).value as Precisione)"
      >
        <option value="GIORNO">giorno</option>
        <option value="MESE">solo mese</option>
        <option value="ANNO">solo anno</option>
      </select>
    </div>
  </div>
</template>
