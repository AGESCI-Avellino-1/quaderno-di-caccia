<script setup lang="ts">
import { ref } from 'vue'

import { useErrore } from '@/composables/useErrore'
import { useSessioneStore } from '@/stores/sessione'

// Start using the app as one person: the reason is required, the person reads it.
const props = defineProps<{ utente?: number; persona?: number; nome: string }>()
const sessione = useSessioneStore()
const { errore, inCorso, esegui } = useErrore()
const aperto = ref(false)
const motivo = ref('')

async function inizia() {
  await esegui(() =>
    sessione.impersona({
      ...(props.persona !== undefined ? { persona_id: props.persona } : {}),
      ...(props.utente !== undefined ? { utente_id: props.utente } : {}),
      motivo: motivo.value,
    }),
  )
}
</script>

<template>
  <div>
    <button
      v-if="!aperto"
      type="button"
      class="btn btn-sm btn-outline theme-primary"
      @click="aperto = true"
    >
      Usa l'app al posto di {{ nome }}
    </button>
    <form v-else class="d-flex flex-wrap align-items-end gap-3" @submit.prevent="inizia">
      <div class="flex-grow-1">
        <label class="form-label small" :for="`motivo-imp-${persona ?? utente}`">
          Perché? (lo leggerà {{ nome }}; dura al massimo 30 minuti)
        </label>
        <input
          :id="`motivo-imp-${persona ?? utente}`"
          v-model="motivo"
          class="form-control form-control-sm"
          maxlength="300"
          required
        />
      </div>
      <button type="submit" class="btn btn-sm btn-solid theme-primary" :disabled="inCorso">
        Inizia
      </button>
      <button type="button" class="btn btn-sm btn-link" @click="aperto = false">Annulla</button>
    </form>
    <div v-if="errore" class="alert theme-danger small mt-1" role="alert">{{ errore }}</div>
  </div>
</template>
