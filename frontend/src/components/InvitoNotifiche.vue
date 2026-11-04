<script setup lang="ts">
import { onMounted, ref } from 'vue'

import { api } from '@/api/qdc'
import { useErrore } from '@/composables/useErrore'
import { appInstallata } from '@/pwa/installazione'
import { attiva, chiudiInvito, invitoChiuso, notificheSupportate, permesso } from '@/pwa/notifiche'

// A discreet invitation in the installed app (DEC-345): the system's permission is asked only
// after a tap here or in the preferences, and it can be closed.
const { errore, inCorso, esegui } = useErrore()
const mostra = ref(false)
const chiave = ref('')

onMounted(async () => {
  if (!appInstallata() || !notificheSupportate()) return
  if (permesso() !== 'default' || invitoChiuso()) return
  const stato = await api.statoPush().catch(() => null)
  if (!stato?.disponibili) return
  chiave.value = stato.chiave_pubblica
  mostra.value = true
})

function chiudi() {
  chiudiInvito()
  mostra.value = false
}

async function si() {
  const fatto = await esegui(async () => {
    await attiva(chiave.value)
    return true
  })
  if (fatto) mostra.value = false
}
</script>

<template>
  <div v-if="mostra" class="alert theme-primary small mb-5" role="region" aria-label="Notifiche">
    <div class="d-flex flex-wrap align-items-center gap-3">
      <span class="flex-grow-1">
        Vuoi ricevere le notifiche su riunioni, scadenze e avvisi? Puoi cambiare idea nelle
        preferenze.
      </span>
      <button
        type="button"
        class="btn btn-sm btn-solid theme-primary"
        :disabled="inCorso"
        @click="si"
      >
        Attiva
      </button>
      <button type="button" class="btn btn-sm btn-link" @click="chiudi">Non ora</button>
    </div>
    <div v-if="errore" class="mt-1">{{ errore }}</div>
  </div>
</template>
