<script setup lang="ts">
import { ref, watch } from 'vue'

import { api, type NoteSchede } from '@/api/qdc'
import { useErrore } from '@/composables/useErrore'
import { leggiConCache } from '@/offline/cache'

// The rules on the relationship with the minor given by the parents (DEC-43): for the
// Co.Ca. only, in evidence at the top of the person page, also offline (the copy of the
// notes). Transcribed online by the unit staff and the capigruppo (DEC-199).
const props = defineProps<{ persona: number }>()
const { errore, inCorso, esegui } = useErrore()
const dati = ref<NoteSchede | null>(null)
const aperta = ref(false)
const testo = ref('')

watch(
  () => props.persona,
  async (id) => {
    const letto = await esegui(() => leggiConCache(`note:${id}`, () => api.note(id)))
    dati.value = letto?.dati ?? null
  },
  { immediate: true },
)

function apri() {
  testo.value = dati.value?.regole ?? ''
  aperta.value = true
}

async function salva() {
  const nuovi = await esegui(() => api.regoleRapporto(props.persona, testo.value))
  if (!nuovi) return
  dati.value = nuovi
  aperta.value = false
}
</script>

<template>
  <template v-if="dati && (dati.regole || dati.puo_scrivere_regole)">
    <div v-if="errore" class="alert theme-danger small" role="alert">{{ errore }}</div>
    <div v-if="dati.regole && !aperta" class="alert theme-warning mb-5" role="note">
      <div>
        <strong>Regole sul rapporto con il minore</strong> (solo per la Co.Ca.)
        <p class="testo-a-capo mb-1">{{ dati.regole }}</p>
        <button
          v-if="dati.puo_scrivere_regole"
          type="button"
          class="btn btn-sm btn-link px-0"
          @click="apri"
        >
          Modifica
        </button>
      </div>
    </div>
    <p v-else-if="!aperta" class="small mb-5">
      <button type="button" class="btn btn-sm btn-link px-0" @click="apri">
        Regole sul rapporto con il minore indicate dai genitori…
      </button>
    </p>
    <form v-if="aperta" class="card card-body mb-5" @submit.prevent="salva">
      <label class="form-label small" :for="`regole-${persona}`">
        Regole sul rapporto con il minore, come scritte dai genitori sul modulo firmato (le leggono
        solo i capi; lascia vuoto se non ce ne sono più)
      </label>
      <textarea
        :id="`regole-${persona}`"
        v-model="testo"
        class="form-control form-control-sm mb-3"
        rows="3"
      />
      <div class="d-flex gap-3">
        <button type="submit" class="btn btn-sm btn-solid theme-primary" :disabled="inCorso">
          Salva
        </button>
        <button type="button" class="btn btn-sm btn-link" @click="aperta = false">Annulla</button>
      </div>
    </form>
  </template>
</template>
