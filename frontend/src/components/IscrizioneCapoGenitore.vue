<script setup lang="ts">
import { ref } from 'vue'

import { api } from '@/api/qdc'
import { useErrore } from '@/composables/useErrore'

// A parent who becomes a capo (DEC-282): a capogruppo sends them the link to join the
// Co.Ca., with what the app already knows of them filled in.
const props = defineProps<{ persona: number; nome: string }>()
const { errore, inCorso, esegui } = useErrore()
const conferma = ref(false)
const inviata = ref<{ email: string; scadenza: string } | null>(null)

async function invia() {
  inviata.value = (await esegui(() => api.iscriviGenitoreInCoca(props.persona))) ?? null
  conferma.value = false
}
</script>

<template>
  <section class="card card-body mb-5">
    <h2 class="h5">Iscrizione in Comunità capi</h2>
    <div v-if="errore" class="alert theme-danger small" role="alert">{{ errore }}</div>
    <p v-if="inviata" class="small mb-0">
      Link mandato a {{ inviata.email }}, valido fino al
      {{ new Date(inviata.scadenza).toLocaleDateString('it-IT') }}: {{ nome }} troverà già i suoi
      dati e completerà il resto. Poi la richiesta arriva tra le richieste di iscrizione.
    </p>
    <template v-else>
      <p class="small fg-2">
        Se {{ nome }} diventa capo, mandagli il link per iscriversi in Comunità capi, con i dati che
        l'app ha già.
      </p>
      <div class="d-flex flex-wrap gap-3 align-items-center">
        <button
          v-if="!conferma"
          type="button"
          class="btn btn-sm btn-outline theme-primary"
          @click="conferma = true"
        >
          Iscrivi in Comunità capi…
        </button>
        <template v-else>
          <span class="small">Mandare il link?</span>
          <button
            type="button"
            class="btn btn-sm btn-solid theme-primary"
            :disabled="inCorso"
            @click="invia"
          >
            Manda il link
          </button>
          <button type="button" class="btn btn-sm btn-link" @click="conferma = false">
            Annulla
          </button>
        </template>
      </div>
    </template>
  </section>
</template>
