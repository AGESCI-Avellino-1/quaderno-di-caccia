<script setup lang="ts">
import { ref } from 'vue'

// One step of a registration on BuonaCaccia, with its real date (DEC-392): today by default,
// never in the future; once marked it may be corrected or taken away (DEC-394).
const props = defineProps<{
  id: string
  valore: string | null
  /** What to do, on the button: «Segna arrivata». */
  segna: string
  /** What happened, before the date: «Arrivata il». */
  fatto: string
  inCorso?: boolean
}>()
const emit = defineEmits<{ scegli: [data: string | null] }>()

const oggi = () => new Date().toLocaleDateString('sv')
const leggibile = (iso: string) => new Date(iso).toLocaleDateString('it-IT')

const scelta = ref(oggi())
const inCorrezione = ref(false)

function correggi() {
  scelta.value = props.valore ?? oggi()
  inCorrezione.value = true
}
function conferma() {
  if (!scelta.value) return
  emit('scegli', scelta.value)
  inCorrezione.value = false
}
</script>

<template>
  <div v-if="valore && !inCorrezione" class="small d-flex flex-wrap align-items-center gap-3">
    <span>{{ fatto }} {{ leggibile(valore) }}</span>
    <button type="button" class="btn btn-sm btn-link p-0" :disabled="inCorso" @click="correggi">
      Cambia
    </button>
    <button
      type="button"
      class="btn btn-sm btn-link p-0"
      :disabled="inCorso"
      @click="emit('scegli', null)"
    >
      Togli
    </button>
  </div>
  <form v-else class="d-flex flex-wrap align-items-end gap-3" @submit.prevent="conferma">
    <div>
      <label class="form-label small mb-0" :for="id">Data</label>
      <input
        :id="id"
        v-model="scelta"
        type="date"
        :max="oggi()"
        class="form-control form-control-sm"
        required
      />
    </div>
    <button type="submit" class="btn btn-sm btn-outline theme-primary" :disabled="inCorso">
      {{ segna }}
    </button>
    <button
      v-if="inCorrezione"
      type="button"
      class="btn btn-sm btn-link"
      @click="inCorrezione = false"
    >
      Annulla
    </button>
  </form>
</template>
