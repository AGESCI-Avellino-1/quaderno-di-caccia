<script setup lang="ts">
import { ref, watch } from 'vue'

import { api, type Delega, type PersonaBreve } from '@/api/qdc'
import { useErrore } from '@/composables/useErrore'

// The member the CSQ delegates to create the patrol's meetings (not to mark their
// attendance). The API answers 404 to whoever may not see it. Online only.
const props = defineProps<{ squadriglia: number; membri: PersonaBreve[] }>()
const { errore, inCorso, esegui } = useErrore()
const delega = ref<Delega | null>(null)
const scelto = ref<number | null>(null)

watch(
  () => props.squadriglia,
  async (id) => {
    try {
      delega.value = await api.delega(id)
    } catch {
      delega.value = null
    }
  },
  { immediate: true },
)

async function delegaA() {
  if (scelto.value === null) return
  const dati = await esegui(() => api.delegaA(props.squadriglia, scelto.value!))
  if (dati) delega.value = dati
}

async function revoca() {
  const dati = await esegui(() => api.revocaDelega(props.squadriglia))
  if (dati) delega.value = dati
}
</script>

<template>
  <div v-if="delega && (delega.puo_delegare || delega.persona)" class="border-top pt-3 mt-3">
    <strong>Riunioni di squadriglia</strong>
    <p class="small mb-1">
      <template v-if="delega.persona">
        Le può inserire anche {{ delega.persona }}, su delega del capo squadriglia.
      </template>
      <template v-else>Le inseriscono il capo squadriglia e lo staff.</template>
    </p>
    <div v-if="errore" class="alert theme-danger small" role="alert">{{ errore }}</div>
    <form
      v-if="delega.puo_delegare"
      class="d-flex flex-wrap align-items-end gap-3"
      @submit.prevent="delegaA"
    >
      <div>
        <label class="form-label small" :for="`delega-${squadriglia}`">Delega a</label>
        <select
          :id="`delega-${squadriglia}`"
          v-model="scelto"
          class="form-control form-control-sm"
          required
        >
          <option v-for="m in membri" :key="m.id" :value="m.id">
            {{ m.nome }} {{ m.cognome }}
          </option>
        </select>
      </div>
      <button type="submit" class="btn btn-sm btn-outline theme-primary" :disabled="inCorso">
        Delega
      </button>
      <button
        v-if="delega.persona"
        type="button"
        class="btn btn-sm btn-link"
        :disabled="inCorso"
        @click="revoca"
      >
        Togli la delega
      </button>
    </form>
  </div>
</template>
