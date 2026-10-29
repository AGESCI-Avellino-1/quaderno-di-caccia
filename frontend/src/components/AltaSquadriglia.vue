<script setup lang="ts">
import { ref, watch } from 'vue'

import { api, type AltaSquadriglia, type PersonaBreve } from '@/api/qdc'
import { useErrore } from '@/composables/useErrore'

// The reparto staff chooses, year by year, the ragazzi of the Alta Squadriglia: its
// events invite them. Online only.
const props = defineProps<{ reparto: number; ragazzi: PersonaBreve[] }>()
const { errore, inCorso, esegui } = useErrore()
const alta = ref<AltaSquadriglia | null>(null)
const scelti = ref<number[]>([])
const salvata = ref(false)

watch(
  () => props.reparto,
  async (id) => {
    try {
      alta.value = await api.altaSquadriglia(id)
      scelti.value = [...alta.value.persone]
    } catch {
      alta.value = null
    }
  },
  { immediate: true },
)

async function salva() {
  if (!alta.value) return
  salvata.value = false
  const dati = await esegui(() =>
    api.scegliAltaSquadriglia(props.reparto, alta.value!.anno, scelti.value),
  )
  if (!dati) return
  alta.value = dati
  salvata.value = true
}
const etichetta = (fine: number) => `${fine - 1}/${String(fine).slice(-2)}`
</script>

<template>
  <section v-if="alta" class="card card-body mb-5">
    <h2 class="h5 mb-1">Alta Squadriglia {{ etichetta(alta.anno) }}</h2>
    <p class="form-text">Gli eventi di Alta Squadriglia invitano questi ragazzi.</p>
    <div v-if="errore" class="alert theme-danger small" role="alert">{{ errore }}</div>
    <form @submit.prevent="salva">
      <div class="d-flex flex-wrap gap-5 mb-3">
        <div v-for="r in ragazzi" :key="r.id" class="form-field mb-0">
          <input
            :id="`alta-${r.id}`"
            v-model="scelti"
            type="checkbox"
            class="check"
            :value="r.id"
            :disabled="!alta.puo_scegliere"
          />
          <label :for="`alta-${r.id}`">{{ r.nome }} {{ r.cognome }}</label>
        </div>
      </div>
      <div v-if="alta.puo_scegliere" class="d-flex align-items-center gap-3">
        <button type="submit" class="btn btn-sm btn-solid theme-primary" :disabled="inCorso">
          Salva
        </button>
        <span v-if="salvata" class="small fg-success">Salvata.</span>
      </div>
    </form>
  </section>
</template>
