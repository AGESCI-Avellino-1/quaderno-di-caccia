<script setup lang="ts">
import { ref, watch } from 'vue'

import { api, type Unita } from '@/api/qdc'
import { useErrore } from '@/composables/useErrore'

// The ages of a unit for the waiting list (DEC-260): hints for the capi, at the 30 April
// of the scout year (DEC-37); its staff and the capigruppo change them.
const props = defineProps<{ unita: Unita; modificabile: boolean }>()
const { errore, inCorso, esegui } = useErrore()
const minima = ref<number | null>(props.unita.eta_minima ?? null)
const massima = ref<number | null>(props.unita.eta_massima ?? null)
const aperto = ref(false)

watch(
  () => props.unita,
  (u) => {
    minima.value = u.eta_minima ?? null
    massima.value = u.eta_massima ?? null
  },
)

async function salva() {
  const nuove = await esegui(() =>
    api.etaUnita(props.unita.id, { eta_minima: minima.value, eta_massima: massima.value }),
  )
  if (!nuove) return
  minima.value = nuove.eta_minima
  massima.value = nuove.eta_massima
  aperto.value = false
}
</script>

<template>
  <div v-if="unita.eta_minima != null" class="small mb-3">
    <span class="fg-2"
      >Età per la lista d'attesa: da {{ minima }} a {{ massima }} anni (al 30 aprile).</span
    >
    <button
      v-if="modificabile && !aperto"
      type="button"
      class="btn btn-sm btn-link"
      @click="aperto = true"
    >
      Cambia
    </button>
    <form v-if="aperto" class="d-flex flex-wrap align-items-end gap-3 mt-1" @submit.prevent="salva">
      <div>
        <label class="form-label small mb-0" for="eta-minima">Da</label>
        <input
          id="eta-minima"
          v-model.number="minima"
          type="number"
          min="5"
          max="25"
          class="form-control form-control-sm"
          required
        />
      </div>
      <div>
        <label class="form-label small mb-0" for="eta-massima">A</label>
        <input
          id="eta-massima"
          v-model.number="massima"
          type="number"
          min="5"
          max="25"
          class="form-control form-control-sm"
          required
        />
      </div>
      <button type="submit" class="btn btn-sm btn-solid theme-primary" :disabled="inCorso">
        Salva
      </button>
      <button type="button" class="btn btn-sm btn-link" @click="aperto = false">Annulla</button>
    </form>
    <div v-if="errore" class="alert theme-danger small mt-1" role="alert">{{ errore }}</div>
  </div>
</template>
